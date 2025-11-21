from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Especialidade
from config import get_settings
from services.rag_service import load_and_index_documents, ask_question

settings = get_settings()

router = APIRouter(
    prefix="/clinica",
    tags=["Clínica"]
)


@router.get("/info")
def get_clinica_info():
    return {
        "nome": settings.clinica_nome,
        "endereco": settings.clinica_endereco,
        "telefone": settings.clinica_telefone,
        "email": settings.clinica_email
    }


@router.get("/especialidades")
def get_especialidades(db: Session = Depends(get_db)):
    especialidades = db.query(Especialidade).all()
    
    return {
        "total": len(especialidades),
        "especialidades": [
            {
                "id": esp.id,
                "nome": esp.nome,
                "descricao": esp.descricao,
                "icone": esp.icone
            }
            for esp in especialidades
        ]
    }


@router.get("/apresentacao")
def get_apresentacao(db: Session = Depends(get_db)):
    especialidades = db.query(Especialidade).all()
    
    lista_especialidades = "\n".join([
        f"   {esp.icone} {esp.nome}" for esp in especialidades
    ])
    
    mensagem = f"""Olá! Bem-vindo(a) à {settings.clinica_nome}!

Oferecemos consultas nas seguintes especialidades:
{lista_especialidades}

Como posso ajudar você hoje?

Você pode:
- Verificar horários disponíveis
- Agendar uma consulta
- Ver seus agendamentos"""

    return {
        "mensagem": mensagem,
        "clinica": {
            "nome": settings.clinica_nome,
            "endereco": settings.clinica_endereco,
            "telefone": settings.clinica_telefone
        },
        "especialidades": [esp.nome for esp in especialidades]
    }
    
@router.post("/reindex")
def reindex_documents():
    return load_and_index_documents()


@router.post("/ask")
def ask_clinic_question(question: str):
    return ask_question(question)