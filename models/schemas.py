from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal


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


class ChatbotRequest(BaseModel):
    """Requisição do chatbot com intenção e parâmetros"""
    intent: Literal["check_availability", "create_appointment", "list_appointments"]
    parameters: dict = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "intent": "check_availability",
                    "parameters": {"days": 7}
                },
                {
                    "intent": "create_appointment",
                    "parameters": {
                        "title": "Consulta com Dr. Silva",
                        "description": "Consulta de rotina",
                        "start_datetime": "2025-12-01T14:00:00",
                        "end_datetime": "2025-12-01T15:00:00",
                        "attendee_email": "paciente@email.com"
                    }
                },
                {
                    "intent": "list_appointments",
                    "parameters": {}
                }
            ]
        }


class ChatbotResponse(BaseModel):
    """Resposta estruturada para o chatbot"""
    success: bool
    intent: str
    message: str
    data: Optional[dict] = None
    suggestions: Optional[List[str]] = None


class ChatMessage(BaseModel):
    """Mensagem de texto do usuário"""
    message: str = Field(..., description="Mensagem em texto natural do usuário")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {"message": "Quero marcar uma consulta para o dia 25"},
                {"message": "Quais horários estão disponíveis na próxima semana?"},
                {"message": "Lista meus agendamentos"}
            ]
        }


class ChatMessageResponse(BaseModel):
    """Resposta do chatbot para o usuário"""
    message: str = Field(..., description="Resposta do chatbot")
    intent_detected: Optional[str] = None
    parameters_extracted: Optional[dict] = None
    action_taken: Optional[str] = None
    data: Optional[dict] = None