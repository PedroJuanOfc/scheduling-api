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
    
    # Carregar todos os PDFs
    documents = []
    for filename in os.listdir(DOCUMENTS_DIR):
        if filename.endswith(".pdf"):
            filepath = os.path.join(DOCUMENTS_DIR, filename)
            loader = PyPDFLoader(filepath)
            documents.extend(loader.load())
    
    if not documents:
        return {"success": False, "message": "Nenhum PDF encontrado na pasta documents/"}
    
    # Dividir em chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    
    # Criar embeddings e indexar
    embeddings = get_embeddings()
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    
    return {"success": True, "message": f"Indexados {len(chunks)} chunks"}


def ask_question(question: str) -> dict:
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
            return {"success": False, "answer": "Índice não encontrado. Execute /clinica/reindex primeiro."}
    
    # Buscar documentos relevantes
    docs = vectorstore.similarity_search(question, k=3)
    
    if not docs:
        return {"success": False, "answer": "Não encontrei informações sobre isso."}
    
    # Montar contexto
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Perguntar ao GPT-4o-mini
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=settings.openai_api_key
    )
    
    prompt = f"""Baseado no contexto abaixo, responda a pergunta de forma clara e amigável.
Se a informação não estiver no contexto, diga que não tem essa informação.

CONTEXTO:
{context}

PERGUNTA: {question}

RESPOSTA:"""
    
    response = llm.invoke(prompt)
    
    return {"success": True, "answer": response.content}