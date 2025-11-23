from neonize.client import NewClient
from neonize.events import MessageEv, ConnectedEv, PairStatusEv
from datetime import datetime, timedelta
import re
from services.conversation_service import (
    get_or_create_conversation,
    reset_conversation,
    get_all_especialidades,
    get_especialidade_by_name,
    get_paciente_by_telefone
)
from services.openai_service import detect_intent_and_extract
from services.rag_service import ask_question
from services.google_calendar_service import get_available_slots, create_calendar_event
from services.trello_service import create_trello_card
from database.database import SessionLocal
from database.models import Paciente, Agendamento, Especialidade
from config import get_settings

settings = get_settings()
client = None


def format_disponibilidade(dias: int = 7) -> str:
    try:
        slots = get_available_slots(days=dias)
        if not slots:
            return "No momento não temos horários disponíveis."
        
        resultado = "*Horários disponíveis:*\n"
        for dia in slots[:5]:
            data_obj = datetime.strptime(dia['date'], '%Y-%m-%d')
            data_fmt = data_obj.strftime('%d/%m/%Y (%A)')
            
            dias_semana = {
                'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
                'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            for en, pt in dias_semana.items():
                data_fmt = data_fmt.replace(en, pt)
            
            horarios = ', '.join(dia['slots'][:6])
            resultado += f"\n*{data_fmt}*\n   {horarios}\n"
        
        return resultado
    except Exception:
        return "Desculpe, tive um problema ao buscar os horários."


def get_primeiro_nome(nome_completo: str) -> str:
    if not nome_completo:
        return ""
    return nome_completo.strip().split()[0]


def normalizar_telefone(phone: str) -> str:
    numeros = ''.join(filter(str.isdigit, phone))
    
    if numeros.startswith('55') and len(numeros) > 11:
        numeros = numeros[2:]
    
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    else:
        return numeros


def validar_horario_disponivel(data_hora_str: str) -> dict:
    try:
        data_sugerida = datetime.fromisoformat(data_hora_str)
        weekday = data_sugerida.weekday()
        hora = data_sugerida.hour
        
        if weekday == 6:
            return {
                "disponivel": False,
                "mensagem": (
                    "Domingos não abrimos, desculpa!\n\n"
                    "Funcionamos de segunda a sexta das 7h às 19h, e sábado das 8h às 13h.\n\n"
                    "Escolhe outro dia?"
                ),
                "alternativas": []
            }
        
        if weekday == 5 and (hora < 8 or hora >= 13):
            return {
                "disponivel": False,
                "mensagem": (
                    f"Sábado só até 13h!\n\n"
                    f"Você sugeriu {data_sugerida.strftime('%H:%M')}, mas não dá pra esse horário.\n\n"
                    f"Tenta entre 8h e 12h, ou escolhe outro dia?"
                ),
                "alternativas": []
            }
        
        if weekday < 5 and (hora < 7 or hora >= 19):
            return {
                "disponivel": False,
                "mensagem": (
                    f"Durante a semana é das 7h às 19h.\n\n"
                    f"O horário que você pediu ({data_sugerida.strftime('%H:%M')}) não tá no nosso expediente.\n\n"
                    f"Consegue em outro horário entre 7h e 18h?"
                ),
                "alternativas": []
            }
        
        slots = get_available_slots(days=30)
        data_str = data_sugerida.strftime('%Y-%m-%d')
        hora_str = data_sugerida.strftime('%H:%M')
        
        for dia in slots:
            if dia['date'] == data_str:
                if hora_str in dia['slots']:
                    return {"disponivel": True, "data": data_sugerida}
                else:
                    break
        
        alternativas = []
        for dia in slots[:5]:
            if dia['slots']:
                data_obj = datetime.strptime(dia['date'], '%Y-%m-%d')
                data_fmt = data_obj.strftime('%d/%m (%A)')
                dias_pt = {
                    'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua',
                    'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sáb'
                }
                for en, pt in dias_pt.items():
                    data_fmt = data_fmt.replace(en, pt)
                
                alternativas.append({
                    'data': data_fmt,
                    'horarios': ', '.join(dia['slots'][:4])
                })
        
        return {
            "disponivel": False,
            "mensagem": None,
            "alternativas": alternativas
        }
        
    except Exception:
        return {
            "disponivel": False,
            "mensagem": "Desculpe, erro ao validar.",
            "alternativas": []
        }


def responder_pergunta_inteligente(user_message: str, context_step: str = None) -> str:
    msg_lower = user_message.lower()
    
    if any(word in msg_lower for word in ['especialidade', 'especialidades']):
        especialidades = get_all_especialidades()
        
        if not especialidades:
            return "Atendemos: Clínica Geral, Odontologia, Oftalmologia e Cardiologia."
        
        lista = "\n".join([f"• {e['icone']} *{e['nome']}*" for e in especialidades])
        
        return (
            f"Atendemos:\n\n{lista}\n\n"
            f"Sobre qual gostaria de saber mais ou deseja agendar?"
        )
    
    try:
        rag_result = ask_question(user_message, context_step=context_step)
        if rag_result.get('success') and rag_result.get('answer'):
            return rag_result['answer']
    except Exception:
        pass
    
    return (
        "Não achei essa informação aqui...\n\n"
        "Mas posso te ajudar com valores, convênios ou agendar consulta.\n\n"
        "O que você precisa?"
    )

def detectar_mes_especifico(user_message: str) -> dict:
    msg_lower = user_message.lower()
    
    meses = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3,
        'abril': 4, 'maio': 5, 'junho': 6,
        'julho': 7, 'agosto': 8, 'setembro': 9,
        'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
    
    for nome_mes, numero in meses.items():
        if nome_mes in msg_lower:
            hoje = datetime.now()
            ano = hoje.year
            
            if numero < hoje.month:
                ano += 1
            
            return {
                'mes_nome': nome_mes.capitalize(),
                'mes_numero': numero,
                'ano': ano
            }
    
    return None


def responder_sobre_disponibilidade(user_message: str, conversation=None) -> str:
    msg_lower = user_message.lower()
    
    hoje_flag = any(w in msg_lower for w in ['hoje', 'hj'])
    amanha = any(w in msg_lower for w in ['amanhã', 'amanha'])
    proximos_dias = None
    dia_semana = None
    
    match_dias = re.search(r'pr[oó]xim[oa]s?\s+(\d+)\s+dias?', msg_lower)
    if match_dias:
        proximos_dias = int(match_dias.group(1))
    
    if not amanha and not proximos_dias and not dia_semana:
        if any(w in msg_lower for w in ['pode ser', 'pode', 'sim', 'ok', 'quero']) and len(msg_lower.split()) <= 3:
            proximos_dias = 5
    
    dias_semana_map = {
        'segunda': (0, 'Segunda-feira'),
        'terca': (1, 'Terça-feira'),
        'terça': (1, 'Terça-feira'),
        'quarta': (2, 'Quarta-feira'),
        'quinta': (3, 'Quinta-feira'),
        'sexta': (4, 'Sexta-feira'),
        'sabado': (5, 'Sábado'),
        'sábado': (5, 'Sábado'),
        'domingo': (6, 'Domingo')
    }
    
    for nome, (num, nome_completo) in dias_semana_map.items():
        if nome in msg_lower:
            dia_semana = (nome_completo, num)
            break
    
    if hoje_flag:
        hoje_date = datetime.now()
        weekday = hoje_date.weekday()
        
        if weekday == 6:
            if conversation:
                conversation.update(last_question='quer_ver_segunda')
            
            return (
                "Hoje é domingo e não abrimos, desculpa!\n\n"
                "Funcionamos de segunda a sexta das 7h às 19h, e sábado das 8h às 13h.\n\n"
                "Quer dar uma olhada nos horários de segunda?"
            )
        
        hora_atual = hoje_date.hour
        
        if weekday == 5 and hora_atual >= 13:
            return (
                "Puxa, já fechamos hoje! Aos sábados só até 13h.\n\n"
                "Quer ver o que tem disponível segunda?"
            )
        
        if weekday < 5 and hora_atual >= 19:
            return (
                "Já fechamos por hoje, mas posso te ajudar a agendar para amanhã!\n\n"
                "Te mostro os horários disponíveis?"
            )
        
        slots = get_available_slots(days=1)
        hoje_str = hoje_date.strftime('%Y-%m-%d')
        
        for dia in slots:
            if dia['date'] == hoje_str:
                if dia['slots']:
                    horarios_futuros = [h for h in dia['slots'] if int(h.split(':')[0]) > hora_atual]
                    
                    if horarios_futuros:
                        horarios = ', '.join(horarios_futuros[:10])
                        return (
                            f"Pra hoje tenho:\n\n"
                            f"{horarios}\n\n"
                            f"Algum desses te atende?"
                        )
                    else:
                        return (
                            "Hoje já não tenho mais horários vagos...\n\n"
                            "Mas posso te mostrar o que tem pra amanhã, que tal?"
                        )
                else:
                    return "Hoje está lotado!\n\nVer amanhã?"
        
        return "Hoje sem horários.\n\nVer amanhã?"
    
    if amanha:
        amanha_date = datetime.now() + timedelta(days=1)
        weekday = amanha_date.weekday()
        
        if weekday == 6:
            if conversation:
                conversation.update(last_question='quer_ver_segunda')
            
            return (
                "Amanhã é domingo e não abrimos...\n\n"
                "Mas segunda já tenho horários! Quer ver?"
            )
        
        slots = get_available_slots(days=2)
        amanha_str = amanha_date.strftime('%Y-%m-%d')
        
        for dia in slots:
            if dia['date'] == amanha_str:
                if dia['slots']:
                    dia_fmt = amanha_date.strftime('%d/%m (%A)')
                    dias_pt = {
                        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
                        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado'
                    }
                    for en, pt in dias_pt.items():
                        dia_fmt = dia_fmt.replace(en, pt)
                    
                    horarios = ', '.join(dia['slots'][:10])
                    return (
                        f"Amanhã ({dia_fmt}) tenho:\n\n"
                        f"{horarios}\n\n"
                        f"Qual funciona melhor pra você?"
                    )
                else:
                    return "Amanhã já tá bem cheio... Quer dar uma olhada nos próximos dias?"
        
        return "Amanhã sem horários.\n\nVer próximos dias?"
    
    elif proximos_dias:
        slots = get_available_slots(days=proximos_dias + 5)
        
        if not slots:
            return f"Próximos {proximos_dias} dias sem horários."
        
        resultado = f"*Próximos {proximos_dias} dias*:\n"
        
        hoje = datetime.now()
        dias_mostrados = 0
        dia_offset = 1
        
        while dias_mostrados < proximos_dias and dia_offset <= proximos_dias + 10:
            dia_atual = hoje + timedelta(days=dia_offset)
            dia_str = dia_atual.strftime('%Y-%m-%d')
            dia_fmt = dia_atual.strftime('%d/%m (%A)')
            
            dias_pt = {
                'Monday': 'Seg', 'Tuesday': 'Ter', 'Wednesday': 'Qua',
                'Thursday': 'Qui', 'Friday': 'Sex', 'Saturday': 'Sáb', 'Sunday': 'Dom'
            }
            for en, pt in dias_pt.items():
                dia_fmt = dia_fmt.replace(en, pt)
            
            if dia_atual.weekday() == 6:
                resultado += f"\n\n*{dia_fmt}*: Fechado"
                dias_mostrados += 1
                dia_offset += 1
                continue
            
            slots_dia = None
            for slot in slots:
                if slot['date'] == dia_str:
                    slots_dia = slot['slots']
                    break
            
            if slots_dia:
                horarios = ', '.join(slots_dia[:8])
                resultado += f"\n\n*{dia_fmt}*:\n{horarios}"
            else:
                resultado += f"\n\n*{dia_fmt}*: Lotado"
            
            dias_mostrados += 1
            dia_offset += 1
        
        resultado += "\n\nQual funciona melhor pra você?"
        return resultado

    elif dia_semana:
        nome_dia, num_dia = dia_semana
        
        if num_dia == 6:
            return (
                f"Domingos não abrimos, mas de segunda a sexta funciona das 7h às 19h, "
                f"e sábado das 8h às 13h."
            )
        
        hoje = datetime.now()
        dias_ate = (num_dia - hoje.weekday()) % 7
        if dias_ate == 0:
            dias_ate = 7
        
        proximo_dia = hoje + timedelta(days=dias_ate)
        slots = get_available_slots(days=dias_ate + 1)
        dia_str = proximo_dia.strftime('%Y-%m-%d')
        
        for dia in slots:
            if dia['date'] == dia_str:
                if dia['slots']:
                    horarios = ', '.join(dia['slots'][:10])
                    return (
                        f"{nome_dia} ({proximo_dia.strftime('%d/%m')}) tem:\n\n"
                        f"{horarios}\n\n"
                        f"Consegue em algum desses?"
                    )
                else:
                    return f"{nome_dia} já tá lotado... Posso ver outra data pra você?"
        
        return f"{nome_dia} sem horários."
    
    return format_disponibilidade(7)


def detectar_escolha_de_dia(user_message: str) -> str:
    msg_lower = user_message.lower().strip()
    
    if any(w in msg_lower for w in ['hoje', 'hj']):
        return 'hoje'
    
    if any(w in msg_lower for w in ['amanhã', 'amanha']):
        return 'amanhã'
    
    dias = {
        'segunda': 'segunda', 'seg': 'segunda',
        'terça': 'terça', 'terca': 'terça', 'ter': 'terça',
        'quarta': 'quarta', 'qua': 'quarta',
        'quinta': 'quinta', 'qui': 'quinta',
        'sexta': 'sexta', 'sex': 'sexta',
        'sábado': 'sábado', 'sabado': 'sábado', 'sab': 'sábado'
    }
    
    for palavra, dia in dias.items():
        if palavra in msg_lower:
            return dia
    
    return None


def buscar_consultas_paciente(telefone: str) -> list:
    db = SessionLocal()
    try:
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        
        pacientes = db.query(Paciente).filter(
            Paciente.telefone.like(f"%{telefone_limpo[-9:]}")
        ).all()
        
        if not pacientes:
            pacientes = db.query(Paciente).all()
            pacientes = [p for p in pacientes if telefone_limpo[-8:] in ''.join(filter(str.isdigit, p.telefone))]
        
        if not pacientes:
            return []
        
        paciente = pacientes[0]
        
        agora = datetime.now()
        consultas = db.query(Agendamento).filter(
            Agendamento.paciente_id == paciente.id,
            Agendamento.status == "agendado",
            Agendamento.data_hora > agora
        ).order_by(Agendamento.data_hora).all()
        
        resultado = []
        for consulta in consultas:
            especialidade = db.query(Especialidade).filter(
                Especialidade.id == consulta.especialidade_id
            ).first()
            
            resultado.append({
                'id': consulta.id,
                'data_hora': consulta.data_hora,
                'especialidade': especialidade.nome if especialidade else "Não identificada",
                'num_remarcacoes': consulta.num_remarcacoes,
                'calendar_event_id': consulta.calendar_event_id,
                'trello_card_id': consulta.trello_card_id
            })
        
        return resultado
        
    finally:
        db.close()


def calcular_taxa_cancelamento(data_hora_consulta: datetime) -> dict:
    agora = datetime.now()
    diferenca = data_hora_consulta - agora
    horas_antecedencia = diferenca.total_seconds() / 3600
    
    if horas_antecedencia >= 24:
        return {
            "tem_taxa": False,
            "valor": 0,
            "motivo": "Cancelamento com mais de 24h de antecedência"
        }
    else:
        return {
            "tem_taxa": True,
            "valor": 50.00,
            "motivo": f"Cancelamento com menos de 24h de antecedência ({int(horas_antecedencia)}h)"
        }


def cancelar_consulta(consulta_id: int, motivo: str = "Solicitado pelo paciente") -> dict:
    db = SessionLocal()
    try:
        consulta = db.query(Agendamento).filter(Agendamento.id == consulta_id).first()
        
        if not consulta:
            return {"success": False, "message": "Consulta não encontrada"}
        
        if consulta.status != "agendado":
            return {"success": False, "message": f"Consulta já está com status: {consulta.status}"}
        
        consulta.status = "cancelado"
        consulta.data_cancelamento = datetime.now()
        consulta.motivo_cancelamento = motivo
        
        if consulta.calendar_event_id:
            try:
                from services.google_calendar_service import delete_calendar_event
                delete_calendar_event(consulta.calendar_event_id)
            except Exception:
                pass
        
        if consulta.trello_card_id:
            try:
                from services.trello_service import archive_trello_card
                archive_trello_card(consulta.trello_card_id)
            except Exception:
                pass
        
        db.commit()
        
        return {
            "success": True,
            "message": "Consulta cancelada com sucesso",
            "taxa": calcular_taxa_cancelamento(consulta.data_hora)
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Erro: {str(e)}"}
    finally:
        db.close()


def remarcar_consulta(consulta_id: int, nova_data_hora: datetime) -> dict:
    db = SessionLocal()
    try:
        consulta = db.query(Agendamento).filter(Agendamento.id == consulta_id).first()

        if not consulta:
            return {"success": False, "message": "Consulta não encontrada"}
        
        if consulta.status != "agendado":
            return {"success": False, "message": f"Não é possível remarcar. Status: {consulta.status}"}
        
        agora = datetime.now()
        diferenca = consulta.data_hora - agora
        horas_antecedencia = diferenca.total_seconds() / 3600
        
        taxa = {"tem_taxa": False, "valor": 0, "motivo": ""}
        
        if consulta.num_remarcacoes == 0:
            taxa["motivo"] = "Primeira remarcação gratuita"
        elif consulta.num_remarcacoes == 1:
            taxa["tem_taxa"] = True
            taxa["valor"] = 30.00
            taxa["motivo"] = "Segunda remarcação"
        else:
            taxa["tem_taxa"] = True
            taxa["valor"] = 30.00
            taxa["motivo"] = f"Remarcação {consulta.num_remarcacoes + 1}"
        
        if horas_antecedencia < 24:
            taxa["tem_taxa"] = True
            taxa["valor"] = 50.00
            taxa["motivo"] = "Remarcação com menos de 24h de antecedência"
        
        paciente = db.query(Paciente).filter(Paciente.id == consulta.paciente_id).first()
        especialidade = db.query(Especialidade).filter(Especialidade.id == consulta.especialidade_id).first()
        
        if consulta.calendar_event_id:
            try:
                from services.google_calendar_service import update_calendar_event
                update_calendar_event(
                    event_id=consulta.calendar_event_id,
                    start_datetime=nova_data_hora,
                    end_datetime=nova_data_hora + timedelta(hours=1)
                )
            except Exception:
                pass
        
        if consulta.trello_card_id:
            try:
                from services.trello_service import update_trello_card
                update_trello_card(
                    card_id=consulta.trello_card_id,
                    due_datetime=nova_data_hora
                )
            except Exception:
                pass
        
        consulta.data_hora = nova_data_hora
        consulta.num_remarcacoes += 1
        db.commit()
        
        return {
            "success": True,
            "message": "Consulta remarcada com sucesso",
            "taxa": taxa
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Erro: {str(e)}"}
    finally:
        db.close()


def process_whatsapp_message(phone: str, user_message: str) -> str:
    session_id = f"whatsapp_{phone}"
    conversation = get_or_create_conversation(session_id)
    user_message = user_message.strip()
    
    conversation.add_message("user", user_message)
    
    if conversation.step == "apresentacao":
        conversation.step = "aguardando_intent"
        
        hora = datetime.now().hour
        if hora < 12:
            saudacao = "Bom dia"
        elif hora < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"
        
        resposta = (
            f"{saudacao}! Aqui é a *{settings.clinica_nome}*.\n\n"
            f"No que posso te ajudar hoje?"
        )
        conversation.add_message("assistant", resposta)
        return resposta
    
    sintomas_especialidades = {
        'oftalmologia': ['olho', 'olhos', 'vista', 'visão', 'cego', 'enxergar', 'grau', 'óculos', 'lente'],
        'cardiologia': ['peito', 'coração', 'cardíaco', 'pressão', 'batimento', 'infarto', 'angina'],
        'odontologia': ['dente', 'dentes', 'boca', 'gengiva', 'canal', 'cárie', 'mastigar', 'morder'],
        'clínica geral': ['febre', 'gripe', 'tosse', 'dor de cabeça', 'corpo', 'mal estar', 'enjoo']
    }
    
    msg_lower = user_message.lower()
    if conversation.step == "aguardando_intent" and any(palavra in msg_lower for palavra in ['dor', 'doendo', 'problema', 'incomodo']):
        for especialidade, sintomas in sintomas_especialidades.items():
            if any(sintoma in msg_lower for sintoma in sintomas):
                esp = get_especialidade_by_name(especialidade)
                if esp:
                    conversation.update(
                        especialidade_id=esp['id'],
                        especialidade_nome=esp['nome'],
                        intent='create_appointment'
                    )
                    conversation.step = "coletando_dados"
                    
                    primeiro_nome = get_primeiro_nome(conversation.data.get('nome', ''))
                    nome_txt = f", {primeiro_nome}" if primeiro_nome else ""
                    
                    resposta = (
                        f"Entendi{nome_txt}. Pelo que você descreveu, recomendo uma consulta com {esp['nome']}.\n\n"
                        f"Quer agendar? Me diz qual dia funciona melhor pra você."
                    )
                    conversation.add_message("assistant", resposta)
                    return resposta
    
    context = {"step": conversation.step, **conversation.data}
    ai_result = detect_intent_and_extract(user_message, context, conversation.history)
    
    intent = ai_result.get('intent', 'greeting')
    extracted = ai_result.get('extracted_data', {})
    
    palavras_sim = ['sim', 'pode ser', 'pode', 'ok', 'quero', 's']
    mensagem_curta = len(user_message.split()) <= 3
    
    context = {"step": conversation.step, **conversation.data}
    ai_result = detect_intent_and_extract(user_message, context, conversation.history)
    
    intent = ai_result.get('intent', 'greeting')
    extracted = ai_result.get('extracted_data', {})
    
    palavras_sim = ['sim', 'pode ser', 'pode', 'ok', 'quero', 's']
    mensagem_curta = len(user_message.split()) <= 3
    
    if (intent == 'confirm' or any(w == user_message.lower().strip() for w in palavras_sim)) and mensagem_curta:
        last_q = conversation.last_question
        
        if last_q == 'quer_ver_segunda':
            resposta = responder_sobre_disponibilidade("segunda", conversation)
            conversation.update(last_question=None)
            conversation.add_message("assistant", resposta)
            return resposta

        elif last_q == 'quer_agendar_nova':
            conversation.update(last_question=None, intent='create_appointment')
            conversation.step = "coletando_dados"
        
        if conversation.step == "coletando_dados" and intent == 'create_appointment':
            pass
    
    if intent == 'question':
        resposta = responder_pergunta_inteligente(user_message, conversation.step)
        if any(word in user_message.lower() for word in ['quanto', 'valor', 'preço']):
            if "agendar" not in resposta.lower():
                resposta += "\n\nGostaria de agendar?"
        conversation.add_message("assistant", resposta)
        return resposta
    
    last_question_backup = conversation.last_question
    
    if extracted.get('nome') and not conversation.data.get('paciente_id'):
        conversation.update(nome=extracted['nome'])
    
    if extracted.get('telefone'):
        tel_norm = normalizar_telefone(extracted['telefone'])
        conversation.update(telefone=tel_norm)
    
    if extracted.get('email') and not conversation.data.get('paciente_id'):
        conversation.update(email=extracted['email'])
    
    if extracted.get('especialidade'):
        esp = get_especialidade_by_name(extracted['especialidade'])
        if esp:
            conversation.update(especialidade_id=esp['id'], especialidade_nome=esp['nome'])
        else:
            todas = get_all_especialidades()
            for e in todas:
                if extracted['especialidade'].lower() in e['nome'].lower():
                    conversation.update(especialidade_id=e['id'], especialidade_nome=e['nome'])
                    break
    
    if extracted.get('start_datetime'):
        conversation.update(data_hora=extracted['start_datetime'])
    
    if last_question_backup and not conversation.last_question:
        conversation.last_question = last_question_backup
    
    if intent == 'check_availability':
        if conversation.step in ["aguardando_nome", "aguardando_email", "aguardando_data"]:
            pass
        else:
            if conversation.data.get('especialidade_id'):
                resposta = responder_sobre_disponibilidade(user_message, conversation)
                conversation.add_message("assistant", resposta)
                return resposta
            
            if extracted.get('especialidade'):
                esp = get_especialidade_by_name(extracted['especialidade'])
                if esp:
                    conversation.update(especialidade_id=esp['id'], especialidade_nome=esp['nome'])
                    conversation.step = "coletando_dados"
                    resposta = responder_sobre_disponibilidade(user_message, conversation)
                    resposta += "\n\n_Gostaria de agendar?_"
                    conversation.add_message("assistant", resposta)
                    return resposta
                
            especialidades = get_all_especialidades()
            lista = "\n".join([f"{e['icone']} {e['nome']}" for e in especialidades])
            resposta = f"Qual especialidade?\n\n{lista}"
            conversation.add_message("assistant", resposta)
            return resposta
    
    if not conversation.data.get('paciente_id'):
        telefone = conversation.data.get('telefone') or normalizar_telefone(phone)
        conversation.update(telefone=telefone)
        
        paciente_existente = get_paciente_by_telefone(telefone)
        if paciente_existente:
            conversation.update(
                paciente_id=paciente_existente['id'],
                nome=paciente_existente['nome'],
                email=paciente_existente['email']
            )
    
    if conversation.step == "aguardando_intent" and intent == 'create_appointment':
        conversation.update(intent='create_appointment')
        conversation.step = "coletando_dados"
    
    if conversation.step in ["coletando_dados", "aguardando_especialidade", "aguardando_nome", "aguardando_email", "aguardando_data"] or intent == 'create_appointment':
        
        if not conversation.data.get('especialidade_id'):
            if extracted.get('especialidade'):
                esp = get_especialidade_by_name(extracted['especialidade'])
                if esp:
                    conversation.update(especialidade_id=esp['id'], especialidade_nome=esp['nome'])
            
            if not conversation.data.get('especialidade_id'):
                especialidades = get_all_especialidades()
                lista = "\n".join([f"{e['icone']} {e['nome']}" for e in especialidades])
                conversation.step = "aguardando_especialidade"
                
                if conversation.data.get('paciente_id'):
                    primeiro_nome = get_primeiro_nome(conversation.data['nome'])
                    resposta = f"Oi, {primeiro_nome}! Já te conheço\n\nQual especialidade você precisa?\n\n{lista}"
                else:
                    resposta = f"Certo! Qual especialidade você precisa?\n\n{lista}"
                
                conversation.add_message("assistant", resposta)
                return resposta
        
        if not conversation.data.get('paciente_id'):
            if not conversation.data.get('nome'):
                conversation.step = "aguardando_nome"
                resposta = f"Beleza, {conversation.data['especialidade_nome']}.\n\nMe passa seu nome completo?"
                conversation.add_message("assistant", resposta)
                return resposta
            
            if not conversation.data.get('email'):
                conversation.step = "aguardando_email"
                primeiro_nome = get_primeiro_nome(conversation.data['nome'])
                resposta = f"Prazer, {primeiro_nome}! Qual seu e-mail? (Vou mandar a confirmação por lá)"
                conversation.add_message("assistant", resposta)
                return resposta
        
        if not conversation.data.get('data_hora'):
            conversation.step = "aguardando_data"
            primeiro_nome = get_primeiro_nome(conversation.data['nome'])
            
            if not conversation.last_question or conversation.last_question != 'perguntou_data':
                conversation.update(last_question='perguntou_data')
                resposta = (
                    f"Legal, {primeiro_nome}.\n\n"
                    f"Que dia funciona melhor pra você?\n\n"
                )
                conversation.add_message("assistant", resposta)
                return resposta
            
            mes_info = detectar_mes_especifico(user_message)
            if mes_info:
                hoje = datetime.now()
                dias_ate_mes = (datetime(mes_info['ano'], mes_info['mes_numero'], 1) - hoje).days
                
                if dias_ate_mes > 31:
                    resposta = (
                        f"A agenda só está aberta pros próximos 31 dias.\n\n"
                        f"{mes_info['mes_nome']} ainda tá longe demais...\n\n"
                        f"Quer ver os horários disponíveis nas próximas semanas?"
                    )
                    conversation.add_message("assistant", resposta)
                    return resposta
                
                resposta = responder_sobre_disponibilidade(f"próximos {dias_ate_mes} dias", conversation)
                conversation.add_message("assistant", resposta)
                return resposta
            
            escolha_dia = detectar_escolha_de_dia(user_message)
            if escolha_dia and not extracted.get('start_datetime'):
                resposta = responder_sobre_disponibilidade(user_message, conversation)
                conversation.add_message("assistant", resposta)
                return resposta
            
            match_dias = re.search(r'pr[oó]xim[oa]s?\s+(\d+)\s+dias?', user_message.lower())
            if match_dias:
                num_dias = int(match_dias.group(1))
                if num_dias > 31:
                    resposta = "A agenda só vai até 31 dias.\n\nTe mostro o máximo que dá?"
                    conversation.add_message("assistant", resposta)
                    return resposta
                
                resposta = responder_sobre_disponibilidade(user_message, conversation)
                conversation.add_message("assistant", resposta)
                return resposta
            
            if extracted.get('start_datetime'):
                data_extraida = datetime.fromisoformat(extracted['start_datetime'])
                
                if data_extraida.hour == 0 and data_extraida.minute == 0:
                    resposta = responder_sobre_disponibilidade(user_message, conversation)
                    conversation.add_message("assistant", resposta)
                    return resposta
                
                validacao = validar_horario_disponivel(extracted['start_datetime'])
                
                if validacao['disponivel']:
                    conversation.update(data_hora=extracted['start_datetime'], last_question=None)
                else:
                    if validacao.get('mensagem'):
                        conversation.add_message("assistant", validacao['mensagem'])
                        return validacao['mensagem']
                    
                    if validacao.get('alternativas'):
                        resposta = f"Esse horário já foi, {primeiro_nome}...\n\nQue tal:\n\n"
                        for alt in validacao['alternativas'][:3]:
                            resposta += f"• *{alt['data']}*: {alt['horarios']}\n"
                        resposta += "\nAlgum desses dá?"
                        conversation.add_message("assistant", resposta)
                        return resposta
                    else:
                        resposta = f"Esse horário não tá disponível, {primeiro_nome}.\n\nTenta outro?"
                        conversation.add_message("assistant", resposta)
                        return resposta
            else:
                resposta = f"Não entendi direito, {primeiro_nome}.\n\nPode falar de novo? Tipo: _amanhã_, _segunda_, _próximos 5 dias_..."
                conversation.add_message("assistant", resposta)
                return resposta
        
        if conversation.is_complete():
            conversation.step = "confirmando"
            data_hora = datetime.fromisoformat(conversation.data['data_hora'])
            data_fmt = data_hora.strftime('%d/%m/%Y às %H:%M')
            primeiro_nome = get_primeiro_nome(conversation.data['nome'])
            
            resposta = (
                f"Fechado então, {primeiro_nome}!\n\n"
                f"Só confirma comigo:\n\n"
                f"*{conversation.data['nome']}*\n"
                f"{conversation.data['telefone']}\n"
                f"{conversation.data['email']}\n"
                f"{conversation.data['especialidade_nome']} - {data_fmt}\n\n"
                f"Tá tudo certo? (responde *sim* pra confirmar)"
            )
            conversation.add_message("assistant", resposta)
            return resposta
    
    if intent == 'cancel_appointment' or conversation.step == "cancelando_consulta":
        telefone = conversation.data.get('telefone')
        
        if not telefone:
            telefone = normalizar_telefone(phone)
            conversation.update(telefone=telefone)
        
        consultas = buscar_consultas_paciente(telefone)
        
        if not consultas:
            conversation.update(last_question='quer_agendar_nova')
            conversation.step = "aguardando_intent"
            
            resposta = (
                "Não encontrei nenhuma consulta agendada no seu nome.\n\n"
                "Quer agendar uma nova?"
            )
            conversation.add_message("assistant", resposta)
            return resposta
        
        if len(consultas) == 1:
            consulta = consultas[0]
            data_fmt = consulta['data_hora'].strftime('%d/%m/%Y às %H:%M')
            taxa_info = calcular_taxa_cancelamento(consulta['data_hora'])

            conversation.step = "confirmando_cancelamento"
            conversation.update(consulta_cancelar_id=consulta['id'])
            
            if taxa_info['tem_taxa']:
                resposta = (
                    f"Você tem uma consulta de *{consulta['especialidade']}* "
                    f"marcada para {data_fmt}.\n\n"
                    f"Como falta menos de 24h, tem uma taxa de R$ {taxa_info['valor']:.2f}.\n\n"
                    f"Confirma o cancelamento mesmo assim?"
                )
            else:
                resposta = (
                    f"Você tem uma consulta de *{consulta['especialidade']}* "
                    f"marcada para {data_fmt}.\n\n"
                    f"Confirma o cancelamento?"
                )
            
            conversation.add_message("assistant", resposta)
            return resposta
        
        conversation.step = "escolhendo_consulta_cancelar"
        
        lista = "\n".join([
            f"{i+1}. {c['especialidade']} - {c['data_hora'].strftime('%d/%m/%Y às %H:%M')}"
            for i, c in enumerate(consultas)
        ])
        
        resposta = (
            f"Você tem {len(consultas)} consultas agendadas:\n\n"
            f"{lista}\n\n"
            f"Qual você quer cancelar? (responde o número)"
        )
        
        conversation.update(consultas_disponiveis=consultas)
        conversation.add_message("assistant", resposta)
        return resposta
    
    if conversation.step == "escolhendo_consulta_cancelar":
        try:
            escolha = int(user_message.strip())
            consultas = conversation.data.get('consultas_disponiveis', [])
            
            if escolha < 1 or escolha > len(consultas):
                resposta = f"Escolhe um número entre 1 e {len(consultas)}."
                conversation.add_message("assistant", resposta)
                return resposta
            
            consulta = consultas[escolha - 1]
            data_fmt = consulta['data_hora'].strftime('%d/%m/%Y às %H:%M')
            taxa_info = calcular_taxa_cancelamento(consulta['data_hora'])
            
            conversation.step = "confirmando_cancelamento"
            conversation.update(consulta_cancelar_id=consulta['id'])
            
            if taxa_info['tem_taxa']:
                resposta = (
                    f"Consulta de *{consulta['especialidade']}* em {data_fmt}.\n\n"
                    f"Taxa de R$ {taxa_info['valor']:.2f} (menos de 24h).\n\n"
                    f"Confirma o cancelamento?"
                )
            else:
                resposta = (
                    f"Consulta de *{consulta['especialidade']}* em {data_fmt}.\n\n"
                    f"Confirma o cancelamento?"
                )
            
            conversation.add_message("assistant", resposta)
            return resposta
            
        except ValueError:
            resposta = "Manda o número da consulta que você quer cancelar."
            conversation.add_message("assistant", resposta)
            return resposta
    
    if conversation.step == "confirmando_cancelamento":
        if intent == 'confirm' or any(w in user_message.lower() for w in ['sim', 'confirmo', 'ok', 's']):
            consulta_id = conversation.data.get('consulta_cancelar_id')
            
            resultado = cancelar_consulta(consulta_id, "Solicitado pelo paciente via WhatsApp")
            
            if resultado['success']:
                taxa_info = resultado['taxa']
                
                if taxa_info['tem_taxa']:
                    resposta = (
                        f"Consulta cancelada!\n\n"
                        f"Taxa de cancelamento: R$ {taxa_info['valor']:.2f}\n"
                        f"Motivo: {taxa_info['motivo']}\n\n"
                        f"A taxa pode ser paga na próxima visita.\n\n"
                        f"Qualquer coisa é só chamar!"
                    )
                else:
                    resposta = (
                        "Consulta cancelada com sucesso!\n\n"
                        "Sem taxa, pois você cancelou com mais de 24h de antecedência.\n\n"
                        "Precisa de algo mais?"
                    )
                
                reset_conversation(session_id)
            else:
                resposta = f"Deu erro ao cancelar: {resultado['message']}\n\nTenta de novo ou liga pra gente?"
            
            conversation.add_message("assistant", resposta)
            return resposta
        
        if intent == 'cancel' or any(w in user_message.lower() for w in ['não', 'nao', 'desistir']):
            reset_conversation(session_id)
            resposta = "Cancelamento cancelado.\n\nSua consulta continua agendada!"
            conversation.add_message("assistant", resposta)
            return resposta
    
    if intent == 'reschedule_appointment' or conversation.step in ["remarcando_consulta", "escolhendo_consulta_remarcar", "escolhendo_nova_data"]:
        telefone = conversation.data.get('telefone')
        
        if not telefone:
            telefone = normalizar_telefone(phone)
            conversation.update(telefone=telefone)
        
        if conversation.step == "escolhendo_consulta_remarcar":
            pass
        
        elif conversation.step == "escolhendo_nova_data":
            pass
        
        else:
            consultas = buscar_consultas_paciente(telefone)
            
            if not consultas:
                resposta = "Não encontrei consultas agendadas.\n\nQuer agendar uma nova?"
                conversation.add_message("assistant", resposta)
                return resposta
            
            if len(consultas) == 1:
                consulta = consultas[0]
                data_fmt = consulta['data_hora'].strftime('%d/%m/%Y às %H:%M')
                
                agora = datetime.now()
                diferenca = consulta['data_hora'] - agora
                horas_antecedencia = diferenca.total_seconds() / 3600
                
                taxa_msg = ""
                if consulta['num_remarcacoes'] == 0:
                    taxa_msg = "Primeira remarcação é gratuita!"
                elif consulta['num_remarcacoes'] >= 1:
                    taxa_msg = "Taxa de R$ 30,00 (segunda remarcação)"
                
                if horas_antecedencia < 24:
                    taxa_msg = "Taxa de R$ 50,00 (menos de 24h)"
                
                primeiro_nome = get_primeiro_nome(conversation.data.get('nome', ''))
                
                conversation.step = "escolhendo_nova_data"
                conversation.update(
                    consulta_remarcar_id=consulta['id'],
                    especialidade_id=None,
                    especialidade_nome=consulta['especialidade'],
                    last_question='perguntou_data_remarcacao'
                )
                
                resposta = (
                    f"Sua consulta de *{consulta['especialidade']}* "
                    f"tá marcada pra {data_fmt}.\n\n"
                    f"{taxa_msg}\n\n"
                    f"Pra qual dia você quer remarcar, {primeiro_nome}?"
                )
                
                conversation.add_message("assistant", resposta)
                return resposta
            
            conversation.step = "escolhendo_consulta_remarcar"
            
            lista = "\n".join([
                f"{i+1}. {c['especialidade']} - {c['data_hora'].strftime('%d/%m/%Y às %H:%M')}"
                for i, c in enumerate(consultas)
            ])
            
            resposta = (
                f"Você tem {len(consultas)} consultas:\n\n"
                f"{lista}\n\n"
                f"Qual você quer remarcar? (número)"
            )
            
            conversation.update(consultas_disponiveis=consultas)
            conversation.add_message("assistant", resposta)
            return resposta
        
        if conversation.step == "escolhendo_nova_data":
            mes_info = detectar_mes_especifico(user_message)
            if mes_info:
                hoje = datetime.now()
                dias_ate_mes = (datetime(mes_info['ano'], mes_info['mes_numero'], 1) - hoje).days
                
                if dias_ate_mes > 31:
                    resposta = (
                        f"A agenda só está aberta pros próximos 31 dias.\n\n"
                        f"{mes_info['mes_nome']} ainda tá longe demais...\n\n"
                        f"Quer ver os horários disponíveis nas próximas semanas?"
                    )
                    conversation.add_message("assistant", resposta)
                    return resposta
                
                resposta = responder_sobre_disponibilidade(f"próximos {dias_ate_mes} dias", conversation)
                conversation.add_message("assistant", resposta)
                return resposta
            
            escolha_dia = detectar_escolha_de_dia(user_message)
            if escolha_dia and not extracted.get('start_datetime'):
                resposta = responder_sobre_disponibilidade(user_message, conversation)
                conversation.add_message("assistant", resposta)
                return resposta
            
            match_dias = re.search(r'pr[oó]xim[oa]s?\s+(\d+)\s+dias?', user_message.lower())
            if match_dias:
                num_dias = int(match_dias.group(1))
                if num_dias > 31:
                    resposta = "A agenda só vai até 31 dias.\n\nTe mostro o máximo que dá?"
                    conversation.add_message("assistant", resposta)
                    return resposta
                
                resposta = responder_sobre_disponibilidade(user_message, conversation)
                conversation.add_message("assistant", resposta)
                return resposta
            
            if extracted.get('start_datetime'):
                data_extraida = datetime.fromisoformat(extracted['start_datetime'])
                
                if data_extraida.hour == 0 and data_extraida.minute == 0:
                    resposta = responder_sobre_disponibilidade(user_message, conversation)
                    conversation.add_message("assistant", resposta)
                    return resposta
                
                validacao = validar_horario_disponivel(extracted['start_datetime'])
                
                if validacao['disponivel']:
                    consulta_id = conversation.data.get('consulta_remarcar_id')
                    nova_data = datetime.fromisoformat(extracted['start_datetime'])
                    
                    resultado = remarcar_consulta(consulta_id, nova_data)
                    
                    if resultado['success']:
                        taxa_info = resultado['taxa']
                        data_fmt = nova_data.strftime('%d/%m/%Y às %H:%M')
                        
                        if taxa_info['tem_taxa']:
                            resposta = (
                                f"Remarcado!\n\n"
                                f"Nova data: {data_fmt}\n\n"
                                f"Taxa: R$ {taxa_info['valor']:.2f}\n"
                                f"Motivo: {taxa_info['motivo']}\n\n"
                                f"Mandei a confirmação no seu e-mail!"
                            )
                        else:
                            resposta = (
                                f"Remarcado!\n\n"
                                f"Nova data: {data_fmt}\n\n"
                                f"{taxa_info['motivo']}\n\n"
                                f"Mandei a confirmação no e-mail!"
                            )
                        
                        reset_conversation(session_id)
                    else:
                        resposta = f"Erro ao remarcar: {resultado['message']}"
                    
                    conversation.add_message("assistant", resposta)
                    return resposta
                else:
                    primeiro_nome = get_primeiro_nome(conversation.data.get('nome', ''))
                    
                    if validacao.get('mensagem'):
                        conversation.add_message("assistant", validacao['mensagem'])
                        return validacao['mensagem']
                    
                    if validacao.get('alternativas'):
                        resposta = f"Esse horário já foi, {primeiro_nome}...\n\nQue tal:\n\n"
                        for alt in validacao['alternativas'][:3]:
                            resposta += f"• *{alt['data']}*: {alt['horarios']}\n"
                        resposta += "\nAlgum desses dá?"
                        conversation.add_message("assistant", resposta)
                        return resposta
                    else:
                        resposta = f"Esse horário não tá disponível, {primeiro_nome}.\n\nTenta outro?"
                        conversation.add_message("assistant", resposta)
                        return resposta
            else:
                primeiro_nome = get_primeiro_nome(conversation.data.get('nome', ''))
                resposta = f"Não entendi direito, {primeiro_nome}.\n\nPode falar de novo? Tipo: _amanhã_, _segunda_, _próximos 5 dias_..."
                conversation.add_message("assistant", resposta)
                return resposta
    
    if conversation.step == "escolhendo_consulta_remarcar":
        try:
            escolha = int(user_message.strip())
            consultas = conversation.data.get('consultas_disponiveis', [])
            
            if escolha < 1 or escolha > len(consultas):
                resposta = f"Escolhe entre 1 e {len(consultas)}."
                conversation.add_message("assistant", resposta)
                return resposta
            
            consulta = consultas[escolha - 1]
            data_fmt = consulta['data_hora'].strftime('%d/%m/%Y às %H:%M')
            
            primeiro_nome = get_primeiro_nome(conversation.data.get('nome', ''))
            
            conversation.step = "escolhendo_nova_data"
            conversation.update(
                consulta_remarcar_id=consulta['id'],
                especialidade_id=None,
                especialidade_nome=consulta['especialidade'],
                last_question='perguntou_data_remarcacao'
            )
            
            resposta = (
                f"Beleza! Sua consulta de *{consulta['especialidade']}* está marcada para {data_fmt}.\n\n"
                f"Pra qual dia você quer remarcar, {primeiro_nome}?"
            )
            
            conversation.add_message("assistant", resposta)
            return resposta
            
        except ValueError:
            resposta = "Manda o número da consulta."
            conversation.add_message("assistant", resposta)
            return resposta
    
    if conversation.step == "confirmando":
        
        if intent == 'confirm' or any(w in user_message.lower() for w in ['sim', 'confirmo', 'ok', 's']):
            
            if not conversation.is_complete():
                resposta = "Opa, acho que faltou alguma informação... Vamos tentar de novo?"
                conversation.add_message("assistant", resposta)
                return resposta
            
            try:
                db = SessionLocal()
                primeiro_nome = get_primeiro_nome(conversation.data['nome'])
                paciente_id = conversation.data.get('paciente_id')
                
                if not paciente_id:
                    paciente = Paciente(
                        nome=conversation.data['nome'],
                        telefone=conversation.data['telefone'],
                        email=conversation.data['email']
                    )
                    db.add(paciente)
                    db.flush()
                    paciente_id = paciente.id
                
                data_hora = datetime.fromisoformat(conversation.data['data_hora'])
                titulo = f"{conversation.data['especialidade_nome']} - {conversation.data['nome']}"
                
                calendar_event = create_calendar_event(
                    title=titulo,
                    start_datetime=data_hora,
                    end_datetime=data_hora.replace(hour=data_hora.hour + 1),
                    description=f"Paciente: {conversation.data['nome']}\nTelefone: {conversation.data['telefone']}",
                    attendee_email=conversation.data['email']
                )         
            
                trello_card = None
                try:
                    trello_card = create_trello_card(
                        title=titulo,
                        description=f"{conversation.data['telefone']}\n{conversation.data['email']}",
                        start_datetime=data_hora,
                        due_datetime=data_hora.replace(hour=data_hora.hour + 1),
                        calendar_event_link=calendar_event.get('event_link')
                    )
                except Exception:
                    pass
                
                agendamento = Agendamento(
                    paciente_id=paciente_id,
                    especialidade_id=conversation.data['especialidade_id'],
                    data_hora=data_hora,
                    calendar_event_id=calendar_event.get('event_id'),
                    trello_card_id=trello_card.get('card_id') if trello_card else None
                )
                db.add(agendamento)
                db.commit()
                db.close()
                
                data_fmt = data_hora.strftime('%d/%m/%Y às %H:%M')
                conversation.step = "finalizado"
                
                resposta = (
                    f"Pronto, {primeiro_nome}! Agendamento confirmado.\n\n"
                    f"*{conversation.data['especialidade_nome']}*\n"
                    f"{data_fmt}\n\n"
                    f"Local: {settings.clinica_nome}\n"
                    f"{settings.clinica_endereco}\n\n"
                    f"Mandei um e-mail com todos os detalhes. "
                    f"Chega uns 15 minutinhos antes, tá bom?\n\n"
                    f"Qualquer coisa é só chamar!"
                )
                conversation.add_message("assistant", resposta)
                return resposta
                
            except Exception as e:
                resposta = f"Deu um erro aqui no sistema, {primeiro_nome}...\n\nLiga pra gente? {settings.clinica_telefone}"
                conversation.add_message("assistant", resposta)
                return resposta
        
        if intent == 'cancel' or any(w in user_message.lower() for w in ['não', 'nao', 'cancelar']):
            reset_conversation(session_id)
            resposta = "Sem problemas! Se precisar de algo depois, é só chamar."
            conversation.add_message("assistant", resposta)
            return resposta
    
    if any(w in user_message.lower() for w in ['reiniciar', 'recomeçar']):
        reset_conversation(session_id)
        resposta = "Reiniciado!"
        conversation.add_message("assistant", resposta)
        return resposta
    
    if intent == 'greeting':
        hora = datetime.now().hour
        if hora < 12:
            saudacao = "Bom dia"
        elif hora < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"
        
        resposta = f"{saudacao}! Como posso ajudar?"
        conversation.add_message("assistant", resposta)
        return resposta
    
    resposta = (
        "Desculpa, não entendi direito.\n\n"
        "Posso te ajudar a agendar consulta, tirar dúvidas ou ver horários disponíveis.\n\n"
        "O que você precisa?"
    )
    conversation.add_message("assistant", resposta)
    return resposta


def start_whatsapp():
    global client
    
    client = NewClient("whatsapp_session")
    
    @client.event(PairStatusEv)
    def on_pair(c, event: PairStatusEv):
        pass
    
    @client.event(ConnectedEv)
    def on_connected(c, event: ConnectedEv):
        print("Bot WhatsApp conectado")
    
    @client.event(MessageEv)
    def on_message(c, message: MessageEv):
        try:
            if message.Info.MessageSource.IsFromMe:
                return
            
            phone = message.Info.MessageSource.Sender.User
            msg = message.Message
            user_message = None
            
            if msg.conversation:
                user_message = msg.conversation
            elif msg.extendedTextMessage and msg.extendedTextMessage.text:
                user_message = msg.extendedTextMessage.text
            
            if not user_message:
                return
            
            response = process_whatsapp_message(phone, user_message)
            client.send_message(message.Info.MessageSource.Chat, response)
            
        except Exception:
            try:
                client.send_message(
                    message.Info.MessageSource.Chat,
                    f"Erro técnico. Ligue: {settings.clinica_telefone}"
                )
            except:
                pass
    
    client.connect()         