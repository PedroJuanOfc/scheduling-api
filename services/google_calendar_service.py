from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from datetime import datetime, timedelta, time
from config import get_settings

settings = get_settings()

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    creds = None
    token_file = settings.google_calendar_token_file
    credentials_file = settings.google_calendar_credentials_file
    
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(
                    f"Arquivo {credentials_file} não encontrado. "
                    "Baixe as credenciais do Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    service = build('calendar', 'v3', credentials=creds)
    return service


def is_working_day(date: datetime) -> bool:
    weekday = date.weekday()
    
    if weekday == 6:
        return False
    
    if weekday == 5:
        return 8 <= date.hour < 13
    
    return 7 <= date.hour < 19


def get_working_hours(date: datetime) -> tuple:
    weekday = date.weekday()
    
    if weekday == 5:
        return (8, 13)
    
    if weekday < 5:
        return (7, 19)
    
    return (None, None)


def get_busy_times(start_date: datetime, end_date: datetime):
    service = get_calendar_service()
    calendar_id = settings.google_calendar_id
    
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
        
        if 'T' in start:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            
            busy_times.append({
                'start': start_dt,
                'end': end_dt,
                'title': event.get('summary', 'Sem título')
            })
    
    return busy_times


def get_available_slots(days: int = 30, slot_duration_minutes: int = 60):
    now = datetime.now()
    start_date = datetime.combine(now.date(), time(0, 0))
    end_date = start_date + timedelta(days=days)
    
    busy_times = get_busy_times(start_date, end_date)
    
    available_slots = []
    
    current_date = start_date
    while current_date < end_date:
        weekday = current_date.weekday()
        
        if weekday == 6:
            current_date += timedelta(days=1)
            continue
        
        work_start_hour, work_end_hour = get_working_hours(current_date)
        
        if work_start_hour is None:
            current_date += timedelta(days=1)
            continue
        
        day_slots = []
        
        current_slot = datetime.combine(current_date.date(), time(work_start_hour, 0))
        work_end = datetime.combine(current_date.date(), time(work_end_hour, 0))
        
        while current_slot < work_end:
            slot_end = current_slot + timedelta(minutes=slot_duration_minutes)
            
            is_free = True
            for busy in busy_times:
                busy_start = busy['start'].replace(tzinfo=None)
                busy_end = busy['end'].replace(tzinfo=None)
                
                if not (slot_end <= busy_start or current_slot >= busy_end):
                    is_free = False
                    break
            
            if current_slot > now and is_free:
                day_slots.append(current_slot.strftime('%H:%M'))
            
            current_slot = slot_end
        
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
    service = get_calendar_service()
    calendar_id = settings.google_calendar_id
    
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
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }
    
    if description:
        event_body['description'] = description
    
    if attendee_email:
        event_body['attendees'] = [
            {'email': attendee_email, 'responseStatus': 'needsAction'}
        ]
    
    event = service.events().insert(
        calendarId=calendar_id,
        body=event_body,
        sendUpdates='all'
    ).execute()
    
    return {
        'event_id': event.get('id'),
        'event_link': event.get('htmlLink'),
        'created': event.get('created'),
        'summary': event.get('summary'),
        'start': event['start'].get('dateTime'),
        'end': event['end'].get('dateTime')
    }


def test_calendar_connection():
    try:
        service = get_calendar_service()
        calendar_id = settings.google_calendar_id
        
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


def delete_calendar_event(event_id: str) -> bool:
    try:
        service = get_calendar_service()
        service.events().delete(
            calendarId=settings.google_calendar_id,
            eventId=event_id
        ).execute()
        return True
    except Exception:
        return False


def update_calendar_event(event_id: str, start_datetime: datetime, end_datetime: datetime) -> bool:
    try:
        service = get_calendar_service()
        
        event = service.events().get(
            calendarId=settings.google_calendar_id,
            eventId=event_id
        ).execute()
        
        event['start'] = {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'America/Sao_Paulo'
        }
        event['end'] = {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'America/Sao_Paulo'
        }
        
        service.events().update(
            calendarId=settings.google_calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        return True
    except Exception:
        return False