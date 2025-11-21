from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.schemas import ChatMessage, ChatMessageResponse
from services.google_calendar_service import get_available_slots, create_calendar_event
from services.trello_service import create_trello_card
from services.gemini_service import process_user_message
from services.conversation_service import (
    get_or_create_conversation,
    reset_conversation,
    get_apresentacao,
    get_especialidade_by_name,
    get_all_especialidades
)
from database.database import get_db
from database.models import Paciente, Agendamento
from config import get_settings
from datetime import datetime

settings = get_settings()

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot"]
)


def format_disponibilidade(dias: int = 7) -> str:
    """Formata a disponibilidade de forma legível"""
    try:
        slots = get_available_slots(days=dias)
        if not slots:
            return "Não há horários disponíveis nos próximos dias."
        
        resultado = "📅 **Horários disponíveis:**\n"
        for dia in slots[:5]:
            data_obj = datetime.strptime(dia['date'], '%Y-%m-%d')
            data_fmt = data_obj.strftime('%d/%m/%Y (%A)')
            data_fmt = data_fmt.replace('Monday', 'Segunda').replace('Tuesday', 'Terça')
            data_fmt = data_fmt.replace('Wednesday', 'Quarta').replace('Thursday', 'Quinta')
            data_fmt = data_fmt.replace('Friday', 'Sexta').replace('Saturday', 'Sábado')
            data_fmt = data_fmt.replace('Sunday', 'Domingo')
            
            horarios = ', '.join(dia['slots'][:6])
            resultado += f"\n• **{data_fmt}**\n  {horarios}"
        
        return resultado
    except Exception as e:
        return f"Erro ao buscar disponibilidade: {str(e)}"


@router.post("/message", response_model=ChatMessageResponse)
def process_chat_message(request: ChatMessage, db: Session = Depends(get_db)):
    """
    Processa mensagens do chatbot com fluxo de conversa.
    """
    session_id = request.session_id or "default"
    conversation = get_or_create_conversation(session_id)
    user_message = request.message.strip()
    
    # Se é uma nova conversa, mostrar apresentação
    if conversation.step == "apresentacao":
        conversation.step = "aguardando_intent"
        return ChatMessageResponse(
            message=get_apresentacao(),
            intent_detected="greeting",
            current_step=conversation.step,
            data_collected=conversation.data,
            action_taken="apresentacao"
        )
    
    # Processar mensagem com IA
    context = {
        "step": conversation.step,
        **conversation.data
    }
    ai_result = process_user_message(user_message, context)
    
    intent = ai_result.get('intent', 'greeting')
    extracted = ai_result.get('extracted_data', {})
    
    # Atualizar dados extraídos
    if extracted.get('nome'):
        conversation.update(nome=extracted['nome'])
    if extracted.get('telefone'):
        conversation.update(telefone=extracted['telefone'])
    if extracted.get('email'):
        conversation.update(email=extracted['email'])
    if extracted.get('especialidade'):
        esp = get_especialidade_by_name(extracted['especialidade'])
        if esp:
            conversation.update(
                especialidade_id=esp['id'],
                especialidade_nome=esp['nome']
            )
    if extracted.get('start_datetime'):
        conversation.update(data_hora=extracted['start_datetime'])
    
    # Se conversa está finalizada e usuário quer fazer algo novo
    if conversation.step == "finalizado":
        if any(word in user_message.lower() for word in ['agendar', 'marcar', 'consulta', 'outra', 'nova']):
            conversation.step = "coletando_dados"
            conversation.data = {
                "nome": None,
                "telefone": None,
                "email": None,
                "especialidade_id": None,
                "especialidade_nome": None,
                "data_hora": None,
                "intent": "create_appointment"
            }
            
            especialidades = get_all_especialidades()
            lista = "\n".join([f"   {e['icone']} {e['nome']}" for e in especialidades])
            
            return ChatMessageResponse(
                message=f"Claro! Vamos agendar outra consulta.\n\nPara qual especialidade?\n\n{lista}",
                intent_detected="create_appointment",
                current_step="aguardando_especialidade",
                data_collected=conversation.data,
                action_taken="novo_agendamento"
            )
        
        if any(word in user_message.lower() for word in ['disponível', 'disponivel', 'horários', 'horarios']):
            disponibilidade = format_disponibilidade(7)
            return ChatMessageResponse(
                message=f"Claro! Aqui estão os horários disponíveis:\n\n{disponibilidade}\n\nGostaria de agendar uma consulta?",
                intent_detected="check_availability",
                current_step="finalizado",
                data_collected=conversation.data,
                action_taken="mostrando_disponibilidade"
            )
        
        # Resposta padrão para conversa finalizada
        return ChatMessageResponse(
            message=ai_result.get('natural_response', 'Posso te ajudar com mais alguma coisa? Você pode agendar outra consulta ou verificar horários disponíveis.'),
            intent_detected=intent,
            current_step=conversation.step,
            data_collected=conversation.data,
            action_taken="resposta_ia"
        )
    
    # VERIFICAR DISPONIBILIDADE
    if intent == 'check_availability' or any(word in user_message.lower() for word in ['disponível', 'disponivel', 'horários', 'horarios', 'dias', 'quando']):
        disponibilidade = format_disponibilidade(7)
        
        mensagem = disponibilidade + "\n\nQual data e horário você prefere?"
        
        if not conversation.data.get('especialidade_id'):
            especialidades = get_all_especialidades()
            lista = "\n".join([f"   {e['icone']} {e['nome']}" for e in especialidades])
            mensagem = f"Para qual especialidade?\n\n{lista}\n\n{disponibilidade}"
        
        return ChatMessageResponse(
            message=mensagem,
            intent_detected="check_availability",
            current_step=conversation.step,
            data_collected=conversation.data,
            action_taken="mostrando_disponibilidade"
        )
    
    # Lógica de fluxo baseada na intenção
    if intent == 'create_appointment' and conversation.step == "aguardando_intent":
        conversation.update(intent=intent)
        conversation.step = "coletando_dados"
    
    # Se está coletando dados, verificar o que falta
    if conversation.step == "coletando_dados" or intent in ['provide_name', 'provide_phone', 'provide_email', 'provide_specialty', 'create_appointment']:
        
        # Verificar especialidade
        if not conversation.data.get('especialidade_id'):
            especialidades = get_all_especialidades()
            lista = "\n".join([f"   {e['icone']} {e['nome']}" for e in especialidades])
            conversation.step = "aguardando_especialidade"
            return ChatMessageResponse(
                message=f"Para qual especialidade você gostaria de agendar?\n\n{lista}",
                intent_detected=intent,
                current_step=conversation.step,
                data_collected=conversation.data,
                action_taken="solicitando_especialidade"
            )
        
        # Verificar nome
        if not conversation.data.get('nome'):
            conversation.step = "aguardando_nome"
            return ChatMessageResponse(
                message="Para realizar o agendamento, preciso de alguns dados.\n\nQual é o seu **nome completo**?",
                intent_detected=intent,
                current_step=conversation.step,
                data_collected=conversation.data,
                action_taken="solicitando_nome"
            )
        
        # Verificar telefone
        if not conversation.data.get('telefone'):
            conversation.step = "aguardando_telefone"
            primeiro_nome = conversation.data['nome'].split()[0]
            return ChatMessageResponse(
                message=f"Obrigado, {primeiro_nome}! 😊\n\nQual é o seu **telefone** para contato?",
                intent_detected=intent,
                current_step=conversation.step,
                data_collected=conversation.data,
                action_taken="solicitando_telefone"
            )
        
        # Verificar email
        if not conversation.data.get('email'):
            conversation.step = "aguardando_email"
            return ChatMessageResponse(
                message="Ótimo! Qual é o seu **email**?\n\n(Enviaremos a confirmação do agendamento)",
                intent_detected=intent,
                current_step=conversation.step,
                data_collected=conversation.data,
                action_taken="solicitando_email"
            )
        
        # Verificar data/hora
        if not conversation.data.get('data_hora'):
            conversation.step = "aguardando_data"
            disponibilidade = format_disponibilidade(7)
            
            return ChatMessageResponse(
                message=f"Perfeito! Agora escolha a **data e horário** da consulta.\n\n{disponibilidade}\n\nQual data e horário você prefere? (Ex: dia 25 às 14h)",
                intent_detected=intent,
                current_step=conversation.step,
                data_collected=conversation.data,
                action_taken="mostrando_disponibilidade"
            )
        
        # Todos os dados coletados - confirmar
        if conversation.is_complete():
            conversation.step = "confirmando"
            data_hora = datetime.fromisoformat(conversation.data['data_hora'])
            data_fmt = data_hora.strftime('%d/%m/%Y às %H:%M')
            
            return ChatMessageResponse(
                message=f"""Perfeito! Confirme os dados do agendamento:

👤 **Nome:** {conversation.data['nome']}
📞 **Telefone:** {conversation.data['telefone']}
📧 **Email:** {conversation.data['email']}
🏥 **Especialidade:** {conversation.data['especialidade_nome']}
📅 **Data/Hora:** {data_fmt}

Está tudo certo? Responda **SIM** para confirmar ou **NÃO** para cancelar.""",
                intent_detected=intent,
                current_step=conversation.step,
                data_collected=conversation.data,
                action_taken="solicitando_confirmacao"
            )
    
    # Confirmação do agendamento
    if conversation.step == "confirmando":
        if any(word in user_message.lower() for word in ['sim', 'confirmo', 'confirmar', 'ok', 'isso', 'correto', 's']):
            if conversation.is_complete():
                try:
                    # Criar paciente no banco
                    paciente = Paciente(
                        nome=conversation.data['nome'],
                        telefone=conversation.data['telefone'],
                        email=conversation.data['email']
                    )
                    db.add(paciente)
                    db.flush()
                    
                    # Criar evento no Calendar
                    data_hora = datetime.fromisoformat(conversation.data['data_hora'])
                    titulo = f"{conversation.data['especialidade_nome']} - {conversation.data['nome']}"
                    
                    calendar_event = create_calendar_event(
                        title=titulo,
                        start_datetime=data_hora,
                        end_datetime=data_hora.replace(hour=data_hora.hour + 1),
                        description=f"Paciente: {conversation.data['nome']}\nTelefone: {conversation.data['telefone']}\nEmail: {conversation.data['email']}",
                        attendee_email=conversation.data['email']
                    )
                    
                    # Criar card no Trello
                    trello_card = None
                    try:
                        trello_card = create_trello_card(
                            title=titulo,
                            description=f"Paciente: {conversation.data['nome']}\nTelefone: {conversation.data['telefone']}\nEmail: {conversation.data['email']}",
                            start_datetime=data_hora,
                            due_datetime=data_hora.replace(hour=data_hora.hour + 1),
                            calendar_event_link=calendar_event.get('event_link')
                        )
                    except:
                        pass
                    
                    # Salvar agendamento no banco
                    agendamento = Agendamento(
                        paciente_id=paciente.id,
                        especialidade_id=conversation.data['especialidade_id'],
                        data_hora=data_hora,
                        calendar_event_id=calendar_event.get('event_id'),
                        trello_card_id=trello_card.get('card_id') if trello_card else None
                    )
                    db.add(agendamento)
                    db.commit()
                    
                    data_fmt = data_hora.strftime('%d/%m/%Y às %H:%M')
                    dados_salvos = conversation.data.copy()
                    
                    # Mudar step para finalizado mas NÃO resetar
                    conversation.step = "finalizado"
                    
                    return ChatMessageResponse(
                        message=f"""✅ **Agendamento confirmado com sucesso!**

📅 **{dados_salvos['especialidade_nome']}**
🗓️ **Data:** {data_fmt}
👤 **Paciente:** {dados_salvos['nome']}

📍 **Local:** {settings.clinica_nome}
📫 **Endereço:** {settings.clinica_endereco}
📞 **Telefone:** {settings.clinica_telefone}

Enviamos um email de confirmação para {dados_salvos['email']}.

---

😊 **Obrigado por agendar conosco!**

Precisa de mais alguma coisa? Posso te ajudar a:
- Agendar outra consulta
- Ver horários disponíveis
- Tirar dúvidas sobre a clínica

É só me chamar!""",
                        intent_detected="confirm",
                        current_step="finalizado",
                        data_collected=dados_salvos,
                        action_taken="agendamento_criado",
                        data={
                            "calendar_event_id": calendar_event.get('event_id'),
                            "trello_card_id": trello_card.get('card_id') if trello_card else None,
                            "event_link": calendar_event.get('event_link')
                        }
                    )
                    
                except Exception as e:
                    db.rollback()
                    return ChatMessageResponse(
                        message=f"Desculpe, ocorreu um erro ao criar o agendamento: {str(e)}",
                        intent_detected="error",
                        current_step=conversation.step,
                        data_collected=conversation.data,
                        action_taken="erro"
                    )
        
        elif any(word in user_message.lower() for word in ['não', 'nao', 'cancelar', 'n']):
            reset_conversation(session_id)
            return ChatMessageResponse(
                message="Agendamento cancelado. Se precisar de algo, é só me chamar! 😊",
                intent_detected="cancel",
                current_step="finalizado",
                data_collected={},
                action_taken="cancelado"
            )
    
    # Cancelar em qualquer momento
    if any(word in user_message.lower() for word in ['cancelar', 'voltar', 'recomeçar', 'desistir', 'sair']):
        reset_conversation(session_id)
        return ChatMessageResponse(
            message="Tudo bem! Conversa reiniciada. Se precisar de algo, é só me chamar! 😊",
            intent_detected="cancel",
            current_step="finalizado",
            data_collected={},
            action_taken="cancelado"
        )
    
    # Resposta padrão da IA
    return ChatMessageResponse(
        message=ai_result.get('natural_response', 'Como posso ajudar? Você pode agendar uma consulta ou verificar horários disponíveis.'),
        intent_detected=intent,
        current_step=conversation.step,
        data_collected=conversation.data,
        action_taken="resposta_ia"
    )


@router.post("/reset")
def reset_chat(session_id: str = "default"):
    """Reseta a conversa para o início."""
    reset_conversation(session_id)
    return {"message": "Conversa resetada", "session_id": session_id}


@router.get("/health")
def chatbot_health():
    """Verifica se o endpoint do chatbot está funcionando."""
    return {
        "status": "ok",
        "message": "Chatbot endpoint is ready"
    }