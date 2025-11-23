import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import get_settings

settings = get_settings()

DOCUMENTS_DIR = "./documents"
CHROMA_DIR = "./chroma_db"

vectorstore = None


def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key
    )


def load_and_index_documents():
    global vectorstore
    
    if not settings.openai_api_key:
        return {"success": False, "message": "OPENAI_API_KEY não configurada"}
    
    documents = []
    for filename in os.listdir(DOCUMENTS_DIR):
        if filename.endswith(".pdf"):
            filepath = os.path.join(DOCUMENTS_DIR, filename)
            loader = PyPDFLoader(filepath)
            documents.extend(loader.load())
    
    if not documents:
        return {"success": False, "message": "Nenhum PDF encontrado na pasta documents/"}
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    
    embeddings = get_embeddings()
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    
    return {
        "success": True, 
        "message": f"Indexados {len(chunks)} chunks"
    }


def ask_question(question: str, context_step: str = None) -> dict:
    global vectorstore
    
    if not settings.openai_api_key:
        return {"success": False, "answer": "OPENAI_API_KEY não configurada"}
    
    if vectorstore is None:
        try:
            embeddings = get_embeddings()
            vectorstore = Chroma(
                persist_directory=CHROMA_DIR,
                embedding_function=embeddings
            )
        except:
            return {
                "success": False, 
                "answer": "Base de conhecimento não encontrada. Reindexe os documentos."
            }
    
    pergunta_lower = question.lower()
    
    is_especialidades = any(word in pergunta_lower for word in [
        'especialidade', 'especialidades', 'atende', 'atendem'
    ])
    
    is_valores = any(word in pergunta_lower for word in [
        'quanto', 'valor', 'preço', 'custa', 'custo'
    ])
    
    is_horario = any(word in pergunta_lower for word in [
        'horário', 'horario', 'abre', 'fecha', 'funciona'
    ])
    
    is_convenio = any(word in pergunta_lower for word in [
        'convênio', 'convenio', 'plano', 'aceita'
    ])
    
    k = 6 if is_especialidades else 3
    docs = vectorstore.similarity_search(question, k=k)
    
    if not docs:
        return {
            "success": False, 
            "answer": "Desculpe, não encontrei informações sobre isso."
        }
    
    max_context_chars = 3000 if is_especialidades else 2000
    context_parts = []
    total_chars = 0
    
    for doc in docs:
        if total_chars + len(doc.page_content) <= max_context_chars:
            context_parts.append(doc.page_content)
            total_chars += len(doc.page_content)
        else:
            remaining = max_context_chars - total_chars
            if remaining > 200:
                context_parts.append(doc.page_content[:remaining])
            break
    
    context = "\n\n".join(context_parts)
    
    if context_step == "aguardando_especialidade":
        prompt = f"""CONTEXTO: O paciente está no meio de um agendamento e foi perguntado qual especialidade ele quer.
Ele respondeu: "{question}"

Você deve APENAS confirmar que entendeu a especialidade escolhida.

RESPOSTA CURTA (máximo 1 linha):"""
        
    elif is_valores:
        prompt = f"""Você é a assistente da Clínica SaúdeMed. Responda sobre valores.

INFORMAÇÕES:
{context}

PERGUNTA: {question}

INSTRUÇÕES:
- Informe os valores encontrados no contexto
- Seja direto e claro
- Se houver variação de preços, explique
- Mencione formas de pagamento se relevante

RESPOSTA (máximo 3 parágrafos):"""

    elif is_horario:
        prompt = f"""Você é a assistente da Clínica SaúdeMed. Responda sobre horários.

INFORMAÇÕES:
{context}

PERGUNTA: {question}

INSTRUÇÕES:
- Informe horários de funcionamento
- Segunda a Sexta: 7h às 19h
- Sábado: 8h às 13h
- Domingo/Feriado: Fechado

RESPOSTA (máximo 2 parágrafos):"""

    elif is_convenio:
        prompt = f"""Você é a assistente da Clínica SaúdeMed. Responda sobre convênios.

INFORMAÇÕES:
{context}

PERGUNTA: {question}

INSTRUÇÕES:
- Liste os convênios aceitos
- Seja direto e organizado

RESPOSTA (máximo 3 parágrafos):"""

    else:
        prompt = f"""Você é a assistente da Clínica SaúdeMed. Responda de forma amigável.

INFORMAÇÕES:
{context}

PERGUNTA: {question}

INSTRUÇÕES:
- Use APENAS as informações acima
- Seja direto, claro e amigável
- Se não tiver a informação, diga: "Não tenho essa informação específica, mas posso te ajudar com outras dúvidas ou agendar uma consulta."
- NÃO invente informações
- Máximo 4 parágrafos

RESPOSTA:"""
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=settings.openai_api_key,
        temperature=0.3,
        max_tokens=400
    )
    
    try:
        response = llm.invoke(prompt)
        
        return {
            "success": True, 
            "answer": response.content,
            "tokens_used": {
                "context_chars": total_chars,
                "estimated_input_tokens": total_chars // 4,
                "max_output_tokens": 400
            }
        }
    except Exception as e:
        return {
            "success": False,
            "answer": f"Erro ao processar: {str(e)}"
        }


def search_similar_content(query: str, k: int = 5) -> list:
    global vectorstore
    
    if vectorstore is None:
        embeddings = get_embeddings()
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings
        )
    
    docs = vectorstore.similarity_search(query, k=k)
    
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in docs
    ]