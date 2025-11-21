from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Google Calendar
    google_calendar_credentials_file: str = "credentials.json"
    google_calendar_token_file: str = "token.json"
    google_calendar_id: str = "primary"
    
    # Trello
    trello_api_key: str = ""
    trello_token: str = ""
    trello_board_id: str = ""
    trello_list_id: str = ""
    
    # Google Gemini
    gemini_api_key: str = ""
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Informações da Clínica
    clinica_nome: str = "Clínica Saúde Total"
    clinica_endereco: str = "Rua Exemplo, 123 - Centro, Brasília - DF"
    clinica_telefone: str = "(61) 3333-4444"
    clinica_email: str = "contato@clinicasaudetotal.com.br"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()