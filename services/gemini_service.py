import google.generativeai as genai
import json
from datetime import datetime, timedelta
from config import get_settings

settings = get_settings()


def get_gemini_model():
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY não configurada. "
            "Configure a key no arquivo .env"
        )
    
    genai.configure(api_key=settings.gemini_api_key)
    
    # Usar o modelo Gemini 2.5 Flash (gratuito, rápido e estável)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    return model


def test_gemini_connection():
    try:
        model = get_gemini_model()
        
        # Fazer uma pergunta teste
        response = model.generate_content("Responda apenas: OK")
        
        return {
            "success": True,
            "message": "Conexão com Gemini estabelecida com sucesso!",
            "model": "gemini-2.5-flash",
            "test_response": response.text
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Configure a GEMINI_API_KEY no arquivo .env"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Erro ao conectar com Gemini. Verifique sua API Key."
        }


def list_available_models():
    try:
        genai.configure(api_key=settings.gemini_api_key)
        models = genai.list_models()
        
        available = []
        for model in models:
            available.append({
                "name": model.name,
                "supported_methods": model.supported_generation_methods
            })
        
        return {
            "success": True,
            "models": available
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def process_user_message(user_message: str) -> dict:
    model = get_gemini_model()
    
    # Data atual para contexto
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M')
    
    # Prompt otimizado para extração de intenção e parâmetros
    prompt = f"""Você é um assistente especializado em agendamentos de consultas.

DATA E HORA ATUAL: {today_str} às {current_time}

INTENÇÕES POSSÍVEIS:
1. check_availability - Usuário quer verificar horários disponíveis
2. create_appointment - Usuário quer marcar/agendar uma consulta
3. list_appointments - Usuário quer ver seus agendamentos
4. greeting - Usuário está cumprimentando ou fazendo pergunta genérica

MENSAGEM DO USUÁRIO: "{user_message}"

Analise a mensagem e retorne APENAS um JSON válido (sem markdown, sem explicações) no seguinte formato:

{{
  "intent": "uma das 4 intenções acima",
  "confidence": 0.0 a 1.0,
  "parameters": {{
    // Para check_availability:
    "days": número de dias (padrão: 7),
    
    // Para create_appointment:
    "title": "título da consulta (ex: Consulta médica)",
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "duration_minutes": número (padrão: 60),
    "description": "descrição opcional",
    
    // Para list_appointments:
    // nenhum parâmetro necessário
  }},
  "natural_response": "uma resposta amigável para o usuário baseada na intenção detectada"
}}

REGRAS IMPORTANTES:
- Se o usuário mencionar "amanhã", calcule a data correta baseada em {today_str}
- Se mencionar "próxima semana", "semana que vem", use +7 dias
- Se mencionar dia do mês (ex: "dia 25"), use o mês atual ou próximo
- Se não especificar horário, pergunte na natural_response
- Se a intenção não for clara, use "greeting" e peça mais informações
- Horários devem estar no formato 24h (ex: 14:00, não 2:00 PM)
- NUNCA inclua markdown (```json) na resposta, apenas o JSON puro

Retorne APENAS o JSON:"""

    try:
        # Gerar resposta com Gemini
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Remover possíveis markdown se aparecer
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        # Parse do JSON
        result = json.loads(response_text.strip())
        
        # Validar estrutura básica
        if 'intent' not in result:
            raise ValueError("Intent não encontrado na resposta do Gemini")
        
        # Garantir que parameters existe
        if 'parameters' not in result:
            result['parameters'] = {}
        
        # Processar parâmetros de data/hora para create_appointment
        if result['intent'] == 'create_appointment':
            params = result['parameters']
            
            # Se tem date e time, criar datetimes
            if 'date' in params and 'time' in params:
                date_str = params['date']
                time_str = params['time']
                duration = params.get('duration_minutes', 60)
                
                # Criar datetime de início
                start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                end_dt = start_dt + timedelta(minutes=duration)
                
                params['start_datetime'] = start_dt.isoformat()
                params['end_datetime'] = end_dt.isoformat()
                
                # Garantir que tem título
                if 'title' not in params or not params['title']:
                    params['title'] = "Consulta"
        
        return {
            "success": True,
            "intent": result['intent'],
            "confidence": result.get('confidence', 0.8),
            "parameters": result['parameters'],
            "natural_response": result.get('natural_response', ''),
            "raw_response": response_text
        }
        
    except json.JSONDecodeError as e:
        # Se o JSON for inválido, retornar erro mas continuar funcionando
        return {
            "success": False,
            "intent": "greeting",
            "confidence": 0.0,
            "parameters": {},
            "natural_response": "Desculpe, não entendi muito bem. Pode reformular sua pergunta?",
            "error": f"Erro ao parsear JSON: {str(e)}",
            "raw_response": response.text if 'response' in locals() else ""
        }
    
    except Exception as e:
        return {
            "success": False,
            "intent": "greeting",
            "confidence": 0.0,
            "parameters": {},
            "natural_response": "Desculpe, tive um problema ao processar sua mensagem. Tente novamente.",
            "error": str(e)
        }