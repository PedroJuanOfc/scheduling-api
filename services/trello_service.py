from trello import TrelloClient
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