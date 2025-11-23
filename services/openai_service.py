from openai import OpenAI
from config import get_settings
from datetime import datetime, timedelta
import json

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


def detect_intent_and_extract(user_message: str, context: dict = None, history: list = None) -> dict:
    if context is None:
        context = {}
    
    current_date = datetime.now()
    step = context.get('step', 'início')
    
    historico_formatado = ""
    if history and len(history) > 0:
        historico_formatado = "\n\nHISTÓRICO DA CONVERSA (últimas mensagens):\n"
        for msg in history[-10:]:
            role = "Cliente" if msg['role'] == 'user' else "Assistente"
            historico_formatado += f"{role}: {msg['content']}\n"
    
    especialidade_atual = context.get('especialidade_nome', None)
    nome_atual = context.get('nome', None)
    email_atual = context.get('email', None)
    telefone_atual = context.get('telefone', None)
    
    system_prompt = f"""Você é um assistente de atendimento de clínica médica MUITO INTELIGENTE que entende CONTEXTO e HISTÓRICO.

DATA/HORA ATUAL: {current_date.strftime('%d/%m/%Y %H:%M (%A)')}
DIA DA SEMANA: {current_date.strftime('%A')} (0=Segunda, 6=Domingo)
ETAPA DA CONVERSA: {step}

DADOS JÁ COLETADOS:
- Especialidade: {especialidade_atual or 'Nenhuma'}
- Nome: {nome_atual or 'Não informado'}
- Telefone: {telefone_atual or 'Não informado'}
- Email: {email_atual or 'Não informado'}
{historico_formatado}

INSTRUÇÕES CRÍTICAS:

1. ANALISE O HISTÓRICO COMPLETO antes de decidir o intent
2. Se o assistente acabou de mostrar horários (ex: "8h, 14h, 16h") e cliente responde:
   - "às 8" → extrair start_datetime com 08:00
   - "14h" → extrair start_datetime com 14:00  
   - "segunda" → calcular próxima segunda-feira
   - "hoje" → calcular hoje
   - "amanhã" → calcular amanhã
3. Se cliente responde "sim", "pode ser", "ok" após pergunta → intent: "confirm"
4. Use o histórico para inferir dados implícitos

INTENTS DISPONÍVEIS:

- "question": pergunta genérica
- "create_appointment": quer agendar
- "check_availability": quer ver horários
- "cancel_appointment": quer CANCELAR consulta
- "reschedule_appointment": quer REMARCAR consulta
- "provide_datetime": escolhendo data/hora
- "confirm": confirmando ("sim", "ok", "pode ser")
- "cancel": cancelando
- "greeting": saudação

ESPECIALIDADES:
- "oftalmologia", "oftalmo" → "Oftalmologia"
- "odontologia", "dentista" → "Odontologia"  
- "cardiologia", "cardio" → "Cardiologia"
- "clínica geral", "geral" → "Clínica Geral"

EXTRAÇÃO DE DATA/HORA:

HOJE: {current_date.strftime('%d/%m/%Y')}
AMANHÃ: {(current_date + timedelta(days=1)).strftime('%d/%m/%Y')}

REGRAS:
- "às 8" (após ver horários) → usar contexto para data + 08:00
- "amanhã 14h" → {(current_date + timedelta(days=1)).strftime('%Y-%m-%d')}T14:00:00
- "segunda 9h" → calcular próxima segunda T09:00:00
- Formato: YYYY-MM-DDTHH:MM:SS

RESPONDA APENAS JSON:
{{
  "intent": "...",
  "confidence": 0.0-1.0,
  "extracted_data": {{
    "nome": null,
    "telefone": null,
    "email": null,
    "especialidade": null,
    "start_datetime": null
  }},
  "reasoning": "explicação"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"MENSAGEM ATUAL DO CLIENTE:\n{user_message}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        if 'extracted_data' not in result:
            result['extracted_data'] = {}
        if 'intent' not in result:
            result['intent'] = 'other'
        if 'confidence' not in result:
            result['confidence'] = 0.5
        
        return result
        
    except Exception as e:
        return {
            "intent": "other",
            "confidence": 0,
            "extracted_data": {},
            "reasoning": f"Erro: {str(e)}"
        }


def process_user_message(user_message: str, context: dict = None) -> dict:
    return detect_intent_and_extract(user_message, context)