from trello import TrelloClient
from datetime import datetime
from config import get_settings

settings = get_settings()


def get_trello_client():
    """
    Obtém o cliente autenticado do Trello.
    """
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
    """
    Testa a conexão com o Trello.
    Retorna informações básicas do board configurado.
    """
    try:
        client = get_trello_client()
        
        # Verificar se o board_id está configurado
        if not settings.trello_board_id:
            return {
                "success": False,
                "error": "TRELLO_BOARD_ID não configurado no .env",
                "message": "Configure o ID do board do Trello"
            }
        
        # Buscar informações do board
        board = client.get_board(settings.trello_board_id)
        
        # Buscar listas do board
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
    """
    Cria um novo card no Trello.
    
    Args:
        title: Título do card
        description: Descrição do card
        start_datetime: Data e hora de início (opcional)
        due_datetime: Data e hora de vencimento
        calendar_event_link: Link do evento no Google Calendar
    
    Returns:
        Dict com informações do card criado
    """
    client = get_trello_client()
    
    # Verificar se list_id está configurado
    if not settings.trello_list_id:
        raise ValueError(
            "TRELLO_LIST_ID não configurado no .env. "
            "Configure o ID da lista onde os cards serão criados."
        )
    
    # Buscar a lista
    board = client.get_board(settings.trello_board_id)
    trello_list = None
    
    for lst in board.list_lists():
        if lst.id == settings.trello_list_id:
            trello_list = lst
            break
    
    if not trello_list:
        raise ValueError(f"Lista com ID {settings.trello_list_id} não encontrada no board")
    
    # Montar a descrição completa
    full_description = ""
    
    if description:
        full_description += f"{description}\n\n"
    
    if start_datetime:
        full_description += f"**Início:** {start_datetime.strftime('%d/%m/%Y às %H:%M')}\n"
    
    if due_datetime:
        full_description += f"**Fim:** {due_datetime.strftime('%d/%m/%Y às %H:%M')}\n"
    
    if calendar_event_link:
        full_description += f"\n**Link do evento:** {calendar_event_link}"
    
    # Criar o card
    card = trello_list.add_card(
        name=title,
        desc=full_description.strip()
    )
    
    # Adicionar data de vencimento se fornecida
    if due_datetime:
        card.set_due(due_datetime)
    
    return {
        'card_id': card.id,
        'card_url': card.url,
        'card_name': card.name,
        'list_name': trello_list.name
    }


def get_trello_cards(limit: int = 20):
    """
    Busca os cards da lista configurada.
    
    Args:
        limit: Número máximo de cards a retornar
    
    Returns:
        Lista de cards
    """
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