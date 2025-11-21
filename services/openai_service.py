from openai import OpenAI
from config import get_settings
from datetime import datetime, timedelta
import json

settings = get_settings()

client = OpenAI(api_key=settings.openai_api_key)


def process_user_message(user_message: str, context: dict = None) -> dict:
    if context is None:
        context = {}
    
    current_date = datetime.now()
    step = context.get('step', 'início')
    amanha = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    system_prompt = f"""Você é um assistente que extrai dados de mensagens para um sistema de agendamento médico.

HOJE: {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A')})
MÊS ATUAL: {current_date.strftime('%m')} ({current_date.strftime('%B')})
ANO: {current_date.year}
AMANHÃ: {amanha}

ETAPA ATUAL DA CONVERSA: {step}

SUA TAREFA: Analisar a mensagem e extrair informações relevantes.

=== INTENTS ===
- "create_appointment": quer agendar (palavras: agendar, marcar, consulta, consultar)
- "check_availability": quer ver horários disponíveis
- "provide_specialty": mencionou especialidade médica
- "provide_name": informou nome de pessoa
- "provide_phone": informou telefone (números)
- "provide_email": informou email (contém @)
- "provide_datetime": informou data/horário
- "confirm": confirmou (sim, ok, confirmo, correto)
- "cancel": cancelou (não, cancelar)
- "greeting": saudação
- "other": outros

=== ESPECIALIDADES ===
Mapeie variações para o nome correto:
- "oftalmologia", "oftalmologista", "olhos", "vista", "visão" → "Oftalmologia"
- "odontologia", "dentista", "dente", "dentes" → "Odontologia"
- "cardiologia", "cardiologista", "coração", "cardio" → "Cardiologia"
- "clínica geral", "geral", "clínico", "clinico geral" → "Clínica Geral"

=== EXTRAÇÃO DE DATA/HORA (MUITO IMPORTANTE) ===
Quando o usuário mencionar data e hora, SEMPRE extraia no formato ISO 8601.

EXEMPLOS de como interpretar:
- "24 as 11" → "2025-{current_date.strftime('%m')}-24T11:00:00"
- "24 as 11 da manha" → "2025-{current_date.strftime('%m')}-24T11:00:00"
- "dia 25 às 14h" → "2025-{current_date.strftime('%m')}-25T14:00:00"
- "25 as 2 da tarde" → "2025-{current_date.strftime('%m')}-25T14:00:00"
- "amanhã às 10h" → "{amanha}T10:00:00"
- "segunda às 9" → próxima segunda, 09:00:00

REGRAS DE HORA:
- "da manhã" ou "manha" = usar hora como está (ex: 11 = 11:00)
- "da tarde" = adicionar 12 se hora < 12 (ex: 2 da tarde = 14:00)
- Se hora entre 1-7 sem especificar, assumir tarde (ex: "as 3" = 15:00)
- Se hora entre 8-12 sem especificar, assumir manhã

=== RESPOSTA ===
Retorne APENAS JSON válido:
{{
    "intent": "string",
    "extracted_data": {{
        "nome": "string ou null",
        "telefone": "string ou null",
        "email": "string ou null",
        "especialidade": "nome correto da especialidade ou null",
        "start_datetime": "ISO 8601 (YYYY-MM-DDTHH:MM:SS) ou null"
    }}
}}

IMPORTANTE: Se a etapa atual é "aguardando_data", priorize extrair a data/hora da mensagem."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        if 'extracted_data' not in result:
            result['extracted_data'] = {}
        
        return result
        
    except Exception as e:
        print(f"Erro OpenAI: {e}")
        return {
            "intent": "other",
            "extracted_data": {}
        }