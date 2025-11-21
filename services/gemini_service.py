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
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    return model


def test_gemini_connection():
    try:
        model = get_gemini_model()
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
        
        return {"success": True, "models": available}
    except Exception as e:
        return {"success": False, "error": str(e)}


def process_user_message(user_message: str, conversation_context: dict = None) -> dict:
    model = get_gemini_model()
    
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M')
    
    context_info = ""
    if conversation_context:
        context_info = f"""
CONTEXTO DA CONVERSA ATUAL:
- Etapa: {conversation_context.get('step', 'desconhecida')}
- Nome do paciente: {conversation_context.get('nome', 'não informado')}
- Telefone: {conversation_context.get('telefone', 'não informado')}
- Email: {conversation_context.get('email', 'não informado')}
- Especialidade: {conversation_context.get('especialidade_nome', 'não informada')}
"""

    from services.conversation_service import get_all_especialidades
    especialidades = get_all_especialidades()
    esp_list = ", ".join([e['nome'] for e in especialidades])

    prompt = f"""Você é um assistente de agendamento da clínica {settings.clinica_nome}.

DATA E HORA ATUAL: {today_str} às {current_time}

ESPECIALIDADES DISPONÍVEIS: {esp_list}
{context_info}

INTENÇÕES POSSÍVEIS:
1. greeting - Usuário está cumprimentando ou fazendo pergunta genérica
2. check_availability - Usuário quer verificar horários disponíveis
3. create_appointment - Usuário quer marcar/agendar uma consulta
4. list_appointments - Usuário quer ver agendamentos
5. provide_name - Usuário está fornecendo seu nome
6. provide_phone - Usuário está fornecendo seu telefone
7. provide_email - Usuário está fornecendo seu email
8. provide_specialty - Usuário está informando a especialidade desejada
9. confirm - Usuário está confirmando algo
10. cancel - Usuário quer cancelar ou voltar

MENSAGEM DO USUÁRIO: "{user_message}"

Analise a mensagem e retorne APENAS um JSON válido (sem markdown) no formato:

{{
  "intent": "uma das intenções acima",
  "confidence": 0.0 a 1.0,
  "extracted_data": {{
    "nome": "nome se mencionado ou null",
    "telefone": "telefone se mencionado ou null",
    "email": "email se mencionado ou null",
    "especialidade": "especialidade se mencionada ou null",
    "date": "YYYY-MM-DD se mencionada ou null",
    "time": "HH:MM se mencionado ou null"
  }},
  "natural_response": "resposta amigável baseada na intenção"
}}

REGRAS:
- Se mencionar "amanhã", calcule a data correta baseada em {today_str}
- Se mencionar dia do mês (ex: "dia 25"), use o mês atual ou próximo
- Extraia nome, telefone, email se o usuário fornecer
- Identifique especialidade se mencionada
- Se a mensagem for só um nome, intent = "provide_name"
- Se for telefone (números), intent = "provide_phone"
- Se tiver @, provavelmente é email, intent = "provide_email"
- NUNCA inclua markdown (```json) na resposta

Retorne APENAS o JSON:"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        result = json.loads(response_text.strip())
        
        if 'intent' not in result:
            raise ValueError("Intent não encontrado")
        
        if 'extracted_data' not in result:
            result['extracted_data'] = {}
        
        extracted = result.get('extracted_data', {})
        if extracted.get('date') and extracted.get('time'):
            date_str = extracted['date']
            time_str = extracted['time']
            duration = 60
            
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=duration)
            
            extracted['start_datetime'] = start_dt.isoformat()
            extracted['end_datetime'] = end_dt.isoformat()
        
        return {
            "success": True,
            "intent": result['intent'],
            "confidence": result.get('confidence', 0.8),
            "extracted_data": extracted,
            "natural_response": result.get('natural_response', '')
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "intent": "greeting",
            "confidence": 0.0,
            "extracted_data": {},
            "natural_response": "Desculpe, não entendi. Pode reformular?",
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "intent": "greeting",
            "confidence": 0.0,
            "extracted_data": {},
            "natural_response": "Desculpe, tive um problema. Tente novamente.",
            "error": str(e)
        }