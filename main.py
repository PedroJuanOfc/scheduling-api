from fastapi import FastAPI
from config import get_settings
from services.google_calendar_service import test_calendar_connection
from services.trello_service import test_trello_connection

settings = get_settings()

app = FastAPI(
    title="Chatbot Agendamento API",
    description="Backend para chatbot de agendamento com Google Calendar e Trello",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "API do Chatbot de Agendamento está funcionando!",
        "status": "online"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/config-check")
def config_check():
    return {
        "google_calendar_id": settings.google_calendar_id,
        "trello_configured": bool(settings.trello_api_key and settings.trello_token),
        "api_host": settings.api_host,
        "api_port": settings.api_port
    }


@app.get("/test-google-calendar")
def test_google_calendar():
    """
    Testa a conexão com o Google Calendar.
    """
    return test_calendar_connection()


@app.get("/test-trello")
def test_trello():
    """
    Testa a conexão com o Trello.
    """
    return test_trello_connection()