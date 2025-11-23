from trello import TrelloClient
from datetime import datetime
import requests
from config import get_settings

settings = get_settings()


def get_trello_client():
    if not settings.trello_api_key or not settings.trello_token:
        raise ValueError(
            "Credenciais do Trello não configuradas. "
            "Configure TRELLO_API_KEY e TRELLO_TOKEN no arquivo .env"
        )
    
    client = TrelloClient(
        api_key=settings.trello_api_key,
        token=settings.trello_token
    )
    
    return client


def test_trello_connection():
    try:
        client = get_trello_client()
        
        if not settings.trello_board_id:
            return {
                "success": False,
                "error": "TRELLO_BOARD_ID não configurado no .env",
                "message": "Configure o ID do board do Trello"
            }
        
        board = client.get_board(settings.trello_board_id)
        lists = board.list_lists()
        list_names = [lst.name for lst in lists]
        
        return {
            "success": True,
            "board_name": board.name,
            "board_id": settings.trello_board_id,
            "lists": list_names,
            "configured_list_id": settings.trello_list_id
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Configure as credenciais do Trello primeiro"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Erro ao conectar com Trello. Verifique suas credenciais."
        }


def create_trello_card(
    title: str,
    description: str = None,
    start_datetime: datetime = None,
    due_datetime: datetime = None,
    calendar_event_link: str = None
):
    client = get_trello_client()
    
    if not settings.trello_list_id:
        raise ValueError(
            "TRELLO_LIST_ID não configurado no .env. "
            "Configure o ID da lista onde os cards serão criados."
        )
    
    board = client.get_board(settings.trello_board_id)
    trello_list = None
    
    for lst in board.list_lists():
        if lst.id == settings.trello_list_id:
            trello_list = lst
            break
    
    if not trello_list:
        raise ValueError(f"Lista com ID {settings.trello_list_id} não encontrada no board")
    
    full_description = ""
    
    if description:
        full_description += f"{description}\n\n"
    
    if start_datetime:
        full_description += f"**Início:** {start_datetime.strftime('%d/%m/%Y às %H:%M')}\n"
    
    if due_datetime:
        full_description += f"**Fim:** {due_datetime.strftime('%d/%m/%Y às %H:%M')}\n"
    
    if calendar_event_link:
        full_description += f"\n**Link do evento:** {calendar_event_link}"
    
    card = trello_list.add_card(
        name=title,
        desc=full_description.strip()
    )
    
    if due_datetime:
        card.set_due(due_datetime)
    
    return {
        'card_id': card.id,
        'card_url': card.url,
        'card_name': card.name,
        'list_name': trello_list.name
    }


def get_trello_cards(limit: int = 20):
    client = get_trello_client()
    
    if not settings.trello_list_id:
        raise ValueError("TRELLO_LIST_ID não configurado no .env")
    
    board = client.get_board(settings.trello_board_id)
    trello_list = None
    
    for lst in board.list_lists():
        if lst.id == settings.trello_list_id:
            trello_list = lst
            break
    
    if not trello_list:
        raise ValueError(f"Lista com ID {settings.trello_list_id} não encontrada")
    
    cards = trello_list.list_cards()[:limit]
    
    formatted_cards = []
    for card in cards:
        formatted_cards.append({
            'id': card.id,
            'name': card.name,
            'description': card.description,
            'url': card.url,
            'due_date': card.due_date.isoformat() if card.due_date else None
        })
    
    return formatted_cards


def archive_trello_card(card_id: str) -> bool:
    try:
        url = f"https://api.trello.com/1/cards/{card_id}"
        params = {
            'key': settings.trello_api_key,
            'token': settings.trello_token,
            'closed': 'true'
        }
        response = requests.put(url, params=params)
        return response.status_code == 200
    except Exception:
        return False


def update_trello_card(card_id: str, due_datetime: datetime) -> bool:
    try:
        url = f"https://api.trello.com/1/cards/{card_id}"
        params = {
            'key': settings.trello_api_key,
            'token': settings.trello_token,
            'due': due_datetime.isoformat()
        }
        response = requests.put(url, params=params)
        return response.status_code == 200
    except Exception:
        return False