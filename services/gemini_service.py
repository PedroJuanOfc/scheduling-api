import google.generativeai as genai
from config import get_settings

settings = get_settings()


def get_gemini_model():
    """
    Configura e retorna o modelo Gemini.
    """
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY não configurada. "
            "Configure a key no arquivo .env"
        )
    
    genai.configure(api_key=settings.gemini_api_key)
    
    # Usar o modelo Gemini 2.5 Flash (gratuito, rápido e estável)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    return model


def test_gemini_connection():
    """
    Testa a conexão com o Gemini.
    Faz uma pergunta simples para verificar se está funcionando.
    """
    try:
        model = get_gemini_model()
        
        # Fazer uma pergunta teste
        response = model.generate_content("Responda apenas: OK")
        
        return {
            "success": True,
            "message": "Conexão com Gemini estabelecida com sucesso!",
            "model": "gemini-2.5-flash",
            "test_response": response.text
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Configure a GEMINI_API_KEY no arquivo .env"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Erro ao conectar com Gemini. Verifique sua API Key."
        }


def list_available_models():
    """
    Lista todos os modelos disponíveis para sua API Key.
    """
    try:
        genai.configure(api_key=settings.gemini_api_key)
        models = genai.list_models()
        
        available = []
        for model in models:
            available.append({
                "name": model.name,
                "supported_methods": model.supported_generation_methods
            })
        
        return {
            "success": True,
            "models": available
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }