from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal


class AvailabilityRequest(BaseModel):
    days: int = Field(default=30, description="Número de dias para buscar disponibilidade")


class AppointmentRequest(BaseModel):
    title: str = Field(..., description="Título do agendamento")
    description: Optional[str] = Field(None, description="Descrição do agendamento")
    start_datetime: datetime = Field(..., description="Data e hora de início")
    end_datetime: datetime = Field(..., description="Data e hora de fim")
    attendee_email: Optional[str] = Field(None, description="Email do participante")


class AppointmentResponse(BaseModel):
    success: bool
    message: str
    calendar_event_id: Optional[str] = None
    trello_card_id: Optional[str] = None
    event_link: Optional[str] = None


class ChatbotRequest(BaseModel):
    intent: Literal["check_availability", "create_appointment", "list_appointments"]
    parameters: dict = Field(default_factory=dict)


class ChatbotResponse(BaseModel):
    success: bool
    intent: str
    message: str
    data: Optional[dict] = None
    suggestions: Optional[List[str]] = None


class ChatMessage(BaseModel):
    message: str = Field(..., description="Mensagem em texto natural do usuário")
    session_id: Optional[str] = Field(default="default", description="ID da sessão do usuário")


class ChatMessageResponse(BaseModel):
    message: str = Field(..., description="Resposta do chatbot")
    intent_detected: Optional[str] = None
    current_step: Optional[str] = None
    data_collected: Optional[dict] = None
    action_taken: Optional[str] = None
    data: Optional[dict] = None