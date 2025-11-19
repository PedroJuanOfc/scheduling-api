from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from datetime import datetime, timedelta
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