from fastapi import APIRouter, HTTPException
from models.schemas import AvailabilityRequest, AppointmentRequest, AppointmentResponse
from services.google_calendar_service import (
    get_available_slots,
    create_calendar_event,
    get_upcoming_events
)
from services.trello_service import create_trello_card

router = APIRouter(
    prefix="/scheduling",
    tags=["Agendamento"]
)


@router.post("/check-availability")
def check_availability(request: AvailabilityRequest):
    try:
        available_slots = get_available_slots(days=request.days)
        
        return {
            "success": True,
            "total_days_with_availability": len(available_slots),
            "available_slots": available_slots
        }
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": str(e),
                "message": "Google Calendar não configurado. Configure as credenciais primeiro."
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "message": "Erro ao buscar disponibilidade"
            }
        )


@router.post("/create-appointment", response_model=AppointmentResponse)
def create_appointment(request: AppointmentRequest):
    calendar_event = None
    trello_card = None
    
    try:
        # 1. Criar evento no Google Calendar
        calendar_event = create_calendar_event(
            title=request.title,
            start_datetime=request.start_datetime,
            end_datetime=request.end_datetime,
            description=request.description,
            attendee_email=request.attendee_email
        )
        
        # 2. Criar card no Trello
        try:
            trello_card = create_trello_card(
                title=request.title,
                description=request.description,
                start_datetime=request.start_datetime,
                due_datetime=request.end_datetime,
                calendar_event_link=calendar_event['event_link']
            )
        except Exception as trello_error:
            # Se falhar no Trello, registrar mas não falhar a requisição
            # O evento já foi criado no Calendar
            print(f"Aviso: Erro ao criar card no Trello: {trello_error}")
        
        return AppointmentResponse(
            success=True,
            message="Agendamento criado com sucesso" + (
                " no Google Calendar e Trello" if trello_card else " no Google Calendar (Trello não configurado)"
            ),
            calendar_event_id=calendar_event['event_id'],
            trello_card_id=trello_card['card_id'] if trello_card else None,
            event_link=calendar_event['event_link']
        )
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": str(e),
                "message": "Google Calendar não configurado"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "message": "Erro ao criar agendamento"
            }
        )


@router.get("/appointments")
def list_appointments():
    try:
        events = get_upcoming_events(max_results=20)
        
        return {
            "success": True,
            "total": len(events),
            "appointments": events
        }
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": str(e),
                "message": "Google Calendar não configurado"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "message": "Erro ao listar agendamentos"
            }
        )