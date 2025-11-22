from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.database import Base


class Especialidade(Base):
    __tablename__ = "especialidades"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)
    descricao = Column(Text, nullable=True)
    icone = Column(String(10), nullable=True)
    
    agendamentos = relationship("Agendamento", back_populates="especialidade")


class Paciente(Base):
    __tablename__ = "pacientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    telefone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(200), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    agendamentos = relationship("Agendamento", back_populates="paciente")


class Agendamento(Base):
    __tablename__ = "agendamentos"
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    especialidade_id = Column(Integer, ForeignKey("especialidades.id"), nullable=False)
    data_hora = Column(DateTime, nullable=False)
    duracao_minutos = Column(Integer, default=60)
    status = Column(String(50), default="confirmado")
    observacoes = Column(Text, nullable=True)
    
    calendar_event_id = Column(String(200), nullable=True)
    trello_card_id = Column(String(200), nullable=True)
    
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    paciente = relationship("Paciente", back_populates="agendamentos")
    especialidade = relationship("Especialidade", back_populates="agendamentos")