from fastapi import APIRouter, HTTPException
from models.schemas import AvailabilityRequest, AppointmentRequest, AppointmentResponse
from services.google_calendar_service import (
    get_available_slots,
    create_calendar_event,
    get_upcoming_events
)

router = APIRouter(
    prefix="/scheduling",
    tags=["Agendamento"]
)


@router.post("/check-availability")
def check_availability(request: AvailabilityRequest):
    """
    Verifica a disponibilidade nos próximos N dias.
    Retorna os horários livres no Google Calendar.
    """
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
    """
    Cria um novo agendamento no Google Calendar e Trello.
    """
    try:
        # Criar evento no Google Calendar
        calendar_event = create_calendar_event(
            title=request.title,
            start_datetime=request.start_datetime,
            end_datetime=request.end_datetime,
            description=request.description,
            attendee_email=request.attendee_email
        )
        
        # TODO: Criar card no Trello na próxima etapa
        
        return AppointmentResponse(
            success=True,
            message="Agendamento criado com sucesso no Google Calendar",
            calendar_event_id=calendar_event['event_id'],
            trello_card_id=None,  # Será implementado na próxima etapa
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
    """
    Lista todos os agendamentos futuros.
    """
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