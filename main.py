from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from services.google_calendar_service import test_calendar_connection
from services.trello_service import test_trello_connection
from services.gemini_service import test_gemini_connection
from routers import scheduling, chatbot, clinica
from database.database import engine
from database.models import Base

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Chatbot Agendamento API",
    description="Backend para chatbot de agendamento com Google Calendar e Trello",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scheduling.router)
app.include_router(chatbot.router)
app.include_router(clinica.router)


@app.get("/")
def root():
    return {
        "message": "API do Chatbot de Agendamento está funcionando!",
        "status": "online",
        "clinica": settings.clinica_nome,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chatbot": "/chatbot/message",
            "clinica": "/clinica/info",
            "especialidades": "/clinica/especialidades"
        }
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/config-check")
def config_check():
    return {
        "google_calendar_id": settings.google_calendar_id,
        "trello_configured": bool(settings.trello_api_key and settings.trello_token),
        "gemini_configured": bool(settings.gemini_api_key),
        "clinica_nome": settings.clinica_nome,
        "api_host": settings.api_host,
        "api_port": settings.api_port
    }


@app.get("/test-google-calendar")
def test_google_calendar():
    return test_calendar_connection()


@app.get("/test-trello")
def test_trello():
    return test_trello_connection()


@app.get("/test-gemini")
def test_gemini():
    return test_gemini_connection()