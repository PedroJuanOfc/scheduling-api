from fastapi import APIRouter, HTTPException
from models.schemas import ChatbotRequest, ChatbotResponse
from services.google_calendar_service import (
    get_available_slots,
    create_calendar_event,
    get_upcoming_events
)
from services.trello_service import create_trello_card
from datetime import datetime

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot"]
)


@router.post("/process", response_model=ChatbotResponse)
def process_chatbot_request(request: ChatbotRequest):
    """
    Endpoint principal para o chatbot processar requisições.
    
    O chatbot envia a intenção detectada e os parâmetros extraídos.
    Este endpoint executa a ação apropriada e retorna resposta estruturada.
    """
    try:
        if request.intent == "check_availability":
            return handle_check_availability(request.parameters)
        
        elif request.intent == "create_appointment":
            return handle_create_appointment(request.parameters)
        
        elif request.intent == "list_appointments":
            return handle_list_appointments(request.parameters)
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Intenção '{request.intent}' não reconhecida"
            )
    
    except FileNotFoundError as e:
        return ChatbotResponse(
            success=False,
            intent=request.intent,
            message="Desculpe, o sistema ainda não está configurado. Por favor, configure as credenciais do Google Calendar.",
            data={"error": str(e)}
        )
    
    except Exception as e:
        return ChatbotResponse(
            success=False,
            intent=request.intent,
            message=f"Desculpe, ocorreu um erro ao processar sua solicitação: {str(e)}",
            data={"error": str(e)}
        )


def handle_check_availability(parameters: dict) -> ChatbotResponse:
    """Processa solicitação de verificação de disponibilidade"""
    days = parameters.get("days", 30)
    
    available_slots = get_available_slots(days=days)
    
    if not available_slots:
        return ChatbotResponse(
            success=True,
            intent="check_availability",
            message=f"Não encontrei horários disponíveis nos próximos {days} dias. Todos os slots estão ocupados.",
            data={"available_slots": []},
            suggestions=[
                "Tentar buscar disponibilidade para mais dias",
                "Verificar os agendamentos existentes"
            ]
        )
    
    # Formatar mensagem amigável
    total_slots = sum(len(day['slots']) for day in available_slots)
    message = f"Encontrei {len(available_slots)} dias com disponibilidade nos próximos {days} dias, totalizando {total_slots} horários livres."
    
    # Sugerir primeiros 3 dias
    suggestions = []
    for day in available_slots[:3]:
        date_formatted = datetime.strptime(day['date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        first_slots = ', '.join(day['slots'][:3])
        suggestions.append(f"{date_formatted} ({day['day_of_week']}): {first_slots}")
    
    return ChatbotResponse(
        success=True,
        intent="check_availability",
        message=message,
        data={
            "total_days": len(available_slots),
            "total_slots": total_slots,
            "available_slots": available_slots
        },
        suggestions=suggestions
    )


def handle_create_appointment(parameters: dict) -> ChatbotResponse:
    """Processa solicitação de criação de agendamento"""
    # Validar parâmetros obrigatórios
    required_fields = ["title", "start_datetime", "end_datetime"]
    missing_fields = [field for field in required_fields if field not in parameters]
    
    if missing_fields:
        return ChatbotResponse(
            success=False,
            intent="create_appointment",
            message=f"Faltam informações para criar o agendamento: {', '.join(missing_fields)}",
            data={"missing_fields": missing_fields},
            suggestions=[
                "Informar o título do agendamento",
                "Informar a data e hora desejadas"
            ]
        )
    
    # Converter strings de data para datetime se necessário
    if isinstance(parameters['start_datetime'], str):
        parameters['start_datetime'] = datetime.fromisoformat(parameters['start_datetime'])
    
    if isinstance(parameters['end_datetime'], str):
        parameters['end_datetime'] = datetime.fromisoformat(parameters['end_datetime'])
    
    # Criar evento no Google Calendar
    calendar_event = create_calendar_event(
        title=parameters['title'],
        start_datetime=parameters['start_datetime'],
        end_datetime=parameters['end_datetime'],
        description=parameters.get('description'),
        attendee_email=parameters.get('attendee_email')
    )
    
    # Tentar criar card no Trello
    trello_card = None
    try:
        trello_card = create_trello_card(
            title=parameters['title'],
            description=parameters.get('description'),
            start_datetime=parameters['start_datetime'],
            due_datetime=parameters['end_datetime'],
            calendar_event_link=calendar_event['event_link']
        )
    except Exception as trello_error:
        print(f"Aviso: Erro ao criar card no Trello: {trello_error}")
    
    # Formatar mensagem de sucesso
    start_formatted = parameters['start_datetime'].strftime('%d/%m/%Y às %H:%M')
    message = f"✅ Agendamento '{parameters['title']}' criado com sucesso para {start_formatted}!"
    
    if parameters.get('attendee_email'):
        message += f" Um convite foi enviado para {parameters['attendee_email']}."
    
    return ChatbotResponse(
        success=True,
        intent="create_appointment",
        message=message,
        data={
            "calendar_event_id": calendar_event['event_id'],
            "event_link": calendar_event['event_link'],
            "trello_card_id": trello_card['card_id'] if trello_card else None,
            "trello_card_url": trello_card['card_url'] if trello_card else None
        },
        suggestions=[
            "Ver todos os agendamentos",
            "Verificar disponibilidade para outro horário"
        ]
    )


def handle_list_appointments(parameters: dict) -> ChatbotResponse:
    """Processa solicitação de listagem de agendamentos"""
    max_results = parameters.get("max_results", 10)
    
    events = get_upcoming_events(max_results=max_results)
    
    if not events:
        return ChatbotResponse(
            success=True,
            intent="list_appointments",
            message="Você não tem agendamentos futuros no momento.",
            data={"appointments": []},
            suggestions=[
                "Verificar disponibilidade",
                "Criar um novo agendamento"
            ]
        )
    
    message = f"Você tem {len(events)} agendamento(s) futuro(s):"
    
    # Criar lista de sugestões com primeiros 3 agendamentos
    suggestions = []
    for event in events[:3]:
        start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        formatted = start_dt.strftime('%d/%m/%Y às %H:%M')
        suggestions.append(f"{event['title']} - {formatted}")
    
    return ChatbotResponse(
        success=True,
        intent="list_appointments",
        message=message,
        data={
            "total": len(events),
            "appointments": events
        },
        suggestions=suggestions
    )


@router.get("/health")
def chatbot_health():
    """Verifica se o endpoint do chatbot está funcionando"""
    return {
        "status": "ok",
        "message": "Chatbot endpoint is ready",
        "supported_intents": [
            "check_availability",
            "create_appointment",
            "list_appointments"
        ]
    }