from datetime import datetime
from typing import Optional
from database.database import SessionLocal
from database.models import Especialidade, Paciente

conversations = {}


class ConversationState:
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.step = "apresentacao"
        self.data = {
            "nome": None,
            "telefone": None,
            "email": None,
            "especialidade_id": None,
            "especialidade_nome": None,
            "data_hora": None,
            "intent": None,
            "paciente_id": None,
            "consulta_remarcar_id": None,
            "consulta_cancelar_id": None,
            "consultas_disponiveis": None
        }
        self.last_question = None
        self.history = []
        self.created_at = datetime.now()
        self.last_interaction = datetime.now()
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.data:
                self.data[key] = value
            elif key == 'last_question':
                self.last_question = value
        self.last_interaction = datetime.now()
    
    def add_message(self, role: str, content: str):
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.history) > 20:
            self.history = self.history[-20:]
        self.last_interaction = datetime.now()
    
    def is_complete(self) -> bool:
        required = ["nome", "telefone", "email", "especialidade_id", "data_hora"]
        return all(self.data.get(field) for field in required)
    
    def get_missing_fields(self) -> list:
        required = ["nome", "telefone", "email", "especialidade_id", "data_hora"]
        return [field for field in required if not self.data.get(field)]


def get_or_create_conversation(session_id: str) -> ConversationState:
    if session_id not in conversations:
        conversations[session_id] = ConversationState(session_id)
    return conversations[session_id]


def reset_conversation(session_id: str):
    if session_id in conversations:
        del conversations[session_id]


def get_apresentacao() -> str:
    from config import get_settings
    settings = get_settings()
    
    db = SessionLocal()
    try:
        especialidades = db.query(Especialidade).all()
        
        lista_especialidades = "\n".join([
            f"   {esp.icone} {esp.nome}" for esp in especialidades
        ])
        
        mensagem = f"""Olá! 👋 Bem-vindo(a) à {settings.clinica_nome}!

Oferecemos consultas nas seguintes especialidades:
{lista_especialidades}

Como posso ajudar você hoje?"""
        
        return mensagem
    finally:
        db.close()


def get_especialidade_by_name(nome: str) -> Optional[dict]:
    db = SessionLocal()
    try:
        especialidades = db.query(Especialidade).all()
        
        nome_lower = nome.lower()
        for esp in especialidades:
            if nome_lower in esp.nome.lower():
                return {
                    "id": esp.id,
                    "nome": esp.nome,
                    "icone": esp.icone
                }
        return None
    finally:
        db.close()


def get_all_especialidades() -> list:
    db = SessionLocal()
    try:
        especialidades = db.query(Especialidade).all()
        return [
            {"id": esp.id, "nome": esp.nome, "icone": esp.icone}
            for esp in especialidades
        ]
    finally:
        db.close()
        

def get_paciente_by_telefone(telefone: str) -> Optional[dict]:
    db = SessionLocal()
    try:
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        todos_pacientes = db.query(Paciente).all()
        
        for paciente in todos_pacientes:
            tel_banco_limpo = ''.join(filter(str.isdigit, paciente.telefone))
            if telefone_limpo[-9:] == tel_banco_limpo[-9:]:
                return {
                    "id": paciente.id,
                    "nome": paciente.nome,
                    "telefone": paciente.telefone,
                    "email": paciente.email
                }
        
        return None
    finally:
        db.close()