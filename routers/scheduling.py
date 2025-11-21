from fastapi import APIRouter, HTTPException
from models.schemas import AvailabilityRequest, AppointmentRequest, AppointmentResponse
from services.google_calendar_service import get_available_slots

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
    # TODO: Implementar lógica real na próxima etapa
    return AppointmentResponse(
        success=True,
        message="Agendamento criado com sucesso (mock)",
        calendar_event_id="mock_calendar_id_123",
        trello_card_id="mock_trello_id_456",
        event_link="https://calendar.google.com/event?eid=mock123"
    )


@router.get("/appointments")
def list_appointments():
    """
    Lista todos os agendamentos futuros.
    """
    # TODO: Implementar lógica real
    return {
        "appointments": [
            {
                "id": "1",
                "title": "Consulta com Dr. Silva",
                "start": "2025-12-01T14:00:00",
                "end": "2025-12-01T15:00:00"
            }
        ]
    }