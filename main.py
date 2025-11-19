from fastapi import FastAPI

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