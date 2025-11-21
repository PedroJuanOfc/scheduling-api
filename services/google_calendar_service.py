from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from datetime import datetime, timedelta, time
from config import get_settings

settings = get_settings()

# Escopos necessários para ler e criar eventos
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    """
    Obtém o serviço autenticado do Google Calendar.
    Gerencia automaticamente a autenticação e refresh de tokens.
    """
    creds = None
    token_file = settings.google_calendar_token_file
    credentials_file = settings.google_calendar_credentials_file
    
    # Verificar se já existe um token salvo
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # Se não há credenciais válidas, fazer login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Primeira autenticação - requer o arquivo credentials.json
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(
                    f"Arquivo {credentials_file} não encontrado. "
                    "Você precisa baixar as credenciais do Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Salvar as credenciais para a próxima execução
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    service = build('calendar', 'v3', credentials=creds)
    return service


def test_calendar_connection():
    """
    Testa a conexão com o Google Calendar.
    Retorna informações básicas do calendário principal.
    """
    try:
        service = get_calendar_service()
        calendar_id = settings.google_calendar_id
        
        # Buscar informações do calendário
        calendar = service.calendarList().get(calendarId=calendar_id).execute()
        
        return {
            "success": True,
            "calendar_name": calendar.get('summary', 'N/A'),
            "calendar_id": calendar_id,
            "timezone": calendar.get('timeZone', 'N/A')
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Configure as credenciais do Google Calendar primeiro"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Erro ao conectar com Google Calendar"
        }


def get_busy_times(start_date: datetime, end_date: datetime):
    """
    Busca todos os eventos ocupados no período especificado.
    Retorna lista de intervalos ocupados.
    """
    service = get_calendar_service()
    calendar_id = settings.google_calendar_id
    
    # Buscar eventos no período
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_date.isoformat() + 'Z',
        timeMax=end_date.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    busy_times = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        # Converter para datetime se necessário
        if 'T' in start:  # É dateTime
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            
            busy_times.append({
                'start': start_dt,
                'end': end_dt,
                'title': event.get('summary', 'Sem título')
            })
    
    return busy_times


def get_available_slots(days: int = 30, slot_duration_minutes: int = 60):
    """
    Calcula os horários disponíveis nos próximos N dias.
    
    Args:
        days: Número de dias para buscar
        slot_duration_minutes: Duração de cada slot em minutos
    
    Returns:
        Lista de datas com seus respectivos horários livres
    """
    # Configurações de horário de trabalho
    work_start_hour = 9  # 9h
    work_end_hour = 18   # 18h
    
    # Data inicial e final
    now = datetime.now()
    start_date = datetime.combine(now.date(), time(0, 0))
    end_date = start_date + timedelta(days=days)
    
    # Buscar horários ocupados
    busy_times = get_busy_times(start_date, end_date)
    
    available_slots = []
    
    # Iterar por cada dia
    current_date = start_date
    while current_date < end_date:
        # Pular finais de semana (sábado=5, domingo=6)
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        
        day_slots = []
        
        # Criar slots de horário para o dia
        current_slot = datetime.combine(current_date.date(), time(work_start_hour, 0))
        work_end = datetime.combine(current_date.date(), time(work_end_hour, 0))
        
        while current_slot < work_end:
            slot_end = current_slot + timedelta(minutes=slot_duration_minutes)
            
            # Verificar se o slot está livre
            is_free = True
            for busy in busy_times:
                # Remover informação de timezone para comparação
                busy_start = busy['start'].replace(tzinfo=None)
                busy_end = busy['end'].replace(tzinfo=None)
                
                # Checar sobreposição
                if not (slot_end <= busy_start or current_slot >= busy_end):
                    is_free = False
                    break
            
            # Não incluir slots no passado
            if current_slot > now and is_free:
                day_slots.append(current_slot.strftime('%H:%M'))
            
            current_slot = slot_end
        
        # Adicionar dia se houver slots disponíveis
        if day_slots:
            available_slots.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'day_of_week': current_date.strftime('%A'),
                'slots': day_slots
            })
        
        current_date += timedelta(days=1)
    
    return available_slots

def create_calendar_event(
    title: str,
    start_datetime: datetime,
    end_datetime: datetime,
    description: str = None,
    attendee_email: str = None
):
    """
    Cria um novo evento no Google Calendar.
    
    Args:
        title: Título do evento
        start_datetime: Data e hora de início
        end_datetime: Data e hora de fim
        description: Descrição opcional do evento
        attendee_email: Email opcional do participante
    
    Returns:
        Dict com informações do evento criado
    """
    service = get_calendar_service()
    calendar_id = settings.google_calendar_id
    
    # Montar o corpo do evento
    event_body = {
        'summary': title,
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 1 dia antes
                {'method': 'popup', 'minutes': 30},        # 30 minutos antes
            ],
        },
    }
    
    # Adicionar descrição se fornecida
    if description:
        event_body['description'] = description
    
    # Adicionar participante se fornecido
    if attendee_email:
        event_body['attendees'] = [
            {'email': attendee_email}
        ]
    
    # Criar o evento
    event = service.events().insert(
        calendarId=calendar_id,
        body=event_body,
        sendUpdates='all'  # Envia notificações para participantes
    ).execute()
    
    return {
        'event_id': event.get('id'),
        'event_link': event.get('htmlLink'),
        'created': event.get('created'),
        'summary': event.get('summary'),
        'start': event['start'].get('dateTime'),
        'end': event['end'].get('dateTime')
    }


def get_upcoming_events(max_results: int = 10):
    """
    Busca os próximos eventos do calendário.
    
    Args:
        max_results: Número máximo de eventos a retornar
    
    Returns:
        Lista de eventos futuros
    """
    service = get_calendar_service()
    calendar_id = settings.google_calendar_id
    
    # Data e hora atual
    now = datetime.utcnow().isoformat() + 'Z'
    
    # Buscar eventos
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        formatted_events.append({
            'id': event.get('id'),
            'title': event.get('summary', 'Sem título'),
            'start': start,
            'end': end,
            'description': event.get('description', ''),
            'link': event.get('htmlLink')
        })
    
    return formatted_events