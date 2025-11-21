from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AvailabilityRequest(BaseModel):
    """Requisição para buscar disponibilidade"""
    days: int = Field(default=30, description="Número de dias para buscar disponibilidade")
    
    class Config:
        json_schema_extra = {
            "example": {
                "days": 30
            }
        }


class AppointmentRequest(BaseModel):
    """Requisição para criar um agendamento"""
    title: str = Field(..., description="Título do agendamento")
    description: Optional[str] = Field(None, description="Descrição do agendamento")
    start_datetime: datetime = Field(..., description="Data e hora de início")
    end_datetime: datetime = Field(..., description="Data e hora de fim")
    attendee_email: Optional[str] = Field(None, description="Email do participante")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Consulta com Dr. Silva",
                "description": "Consulta médica de rotina",
                "start_datetime": "2025-12-01T14:00:00",
                "end_datetime": "2025-12-01T15:00:00",
                "attendee_email": "paciente@email.com"
            }
        }


class AppointmentResponse(BaseModel):
    """Resposta após criar um agendamento"""
    success: bool
    message: str
    calendar_event_id: Optional[str] = None
    trello_card_id: Optional[str] = None
    event_link: Optional[str] = None