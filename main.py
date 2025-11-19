from fastapi import FastAPI
from config import get_settings

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