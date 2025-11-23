# Sistema de Agendamento Inteligente para WhatsApp

Sistema completo de agendamento via WhatsApp com IA que processa linguagem natural, reconhece sintomas, gerencia consultas e integra automaticamente com Google Calendar e Trello.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-orange.svg)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Bot-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ⚡ Principais Funcionalidades

### 🧠 Inteligência Artificial
- **Processamento de Linguagem Natural** - Entende contexto e intenções do usuário
- **Reconhecimento Automático de Sintomas** - Detecta especialidade necessária baseado em sintomas descritos
- **Detecção Inteligente de Datas** - Compreende "amanhã", "segunda às 14h", "próximos 5 dias", "dezembro"
- **Reconhecimento de Pacientes** - Identifica automaticamente pacientes já cadastrados
- **RAG (Retrieval Augmented Generation)** - Responde perguntas sobre a clínica usando documentos PDF com vetorização

### 💬 WhatsApp
- **Agendamento Completo** - Fluxo conversacional natural para criar consultas
- **Gestão de Consultas** - Remarcar, cancelar e consultar agendamentos futuros
- **Múltiplas Consultas** - Gerencia pacientes com várias consultas agendadas
- **Sistema de Taxas Automático** - Calcula taxas de remarcação/cancelamento conforme regras
- **Confirmações e Notificações** - Envia detalhes da consulta via email

### 🔄 Integrações
- **Google Calendar** - Cria, atualiza e remove eventos automaticamente
- **Trello** - Gerencia cards de agendamentos com links para o Calendar
- **Banco de Dados SQLite** - Armazena histórico completo de pacientes e consultas

## 🚀 Stack Tecnológica

- **FastAPI** - Framework web moderno para APIs
- **Python 3.10+** - Linguagem principal
- **OpenAI GPT-4o-mini** - Processamento de linguagem natural
- **LangChain + ChromaDB** - Sistema RAG para base de conhecimento
- **Google Calendar API** - Gerenciamento de eventos
- **Trello API** - Gestão de cards
- **SQLAlchemy + SQLite** - Persistência de dados
- **Neonize** - Cliente WhatsApp para Python

## 📦 Pré-requisitos

- Python 3.10 ou superior
- Conta Google com Calendar API habilitada
- Conta Trello com API ativada
- API Key da OpenAI
- Número de WhatsApp Business (ou pessoal para testes)

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/chatbot-agendamento.git
cd chatbot-agendamento
```

### 2. Crie o ambiente virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

## 🔑 Configuração

### 1. OpenAI API

1. Acesse [platform.openai.com/signup](https://platform.openai.com/signup)
2. Crie uma conta e adicione créditos
3. Gere uma API Key em [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### 2. Google Calendar API

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto
3. Ative a **Google Calendar API**
4. Configure a **OAuth Consent Screen**:
   - Tipo: External
   - Adicione o scope: `https://www.googleapis.com/auth/calendar`
   - Adicione seu email em "Test users"
5. Crie credenciais **OAuth 2.0** (tipo Desktop app)
6. Baixe o JSON e salve como `credentials.json` na raiz do projeto

### 3. Trello API

1. Acesse [trello.com/power-ups/admin](https://trello.com/power-ups/admin)
2. Crie um novo Power-Up
3. Copie a **API Key**
4. Gere um **Token** usando:
```
https://trello.com/1/authorize?key=SUA_API_KEY&name=AgendamentoBot&expiration=never&response_type=token&scope=read,write
```
5. Obtenha o **Board ID** da URL do seu quadro: `trello.com/b/BOARD_ID/nome`
6. Para o **List ID**, acesse `trello.com/b/BOARD_ID/nome.json` e procure por `"lists"`

### 4. Arquivo .env

Crie um arquivo `.env` na raiz:
```env
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary

TRELLO_API_KEY=sua_api_key
TRELLO_TOKEN=seu_token
TRELLO_BOARD_ID=seu_board_id
TRELLO_LIST_ID=seu_list_id

OPENAI_API_KEY=sk-...

CLINICA_NOME=Clínica SaúdeMed
CLINICA_ENDERECO=Rua Exemplo, 123
CLINICA_TELEFONE=(11) 3333-4444
CLINICA_EMAIL=contato@clinica.com

API_HOST=0.0.0.0
API_PORT=8000
```

## 📚 Base de Conhecimento (RAG)

O sistema pode responder perguntas sobre a clínica usando documentos PDF.

### 1. Adicione documentos
```bash
mkdir documents
```

Coloque arquivos PDF na pasta `documents/` com informações como:
- Preços e procedimentos
- Convênios aceitos
- Políticas de cancelamento
- Informações sobre especialidades

### 2. Indexação automática
O ChromaDB será criado automaticamente na primeira indexação.

Acesse `http://127.0.0.1:8000/docs` e execute:
- **POST /clinica/reindex**

> O banco de vetores será criado em `chroma_db/` automaticamente.

## ▶️ Executando o Sistema

### 1. Inicialize o banco de dados
```bash
python -m database.init_db
```

Isso criará:
- `agendamentos.db` (SQLite)
- Tabelas: `pacientes`, `especialidades`, `agendamentos`
- Especialidades pré-cadastradas

### 2. Inicie a API REST (opcional)
```bash
uvicorn main:app --reload
```

Acesse a documentação em: `http://127.0.0.1:8000/docs`

### 3. Conecte o Google Calendar (primeira vez)

Acesse: `http://127.0.0.1:8000/test-google-calendar`

Uma janela do navegador abrirá solicitando permissões. Após autorizar, o arquivo `token.json` será criado.

### 4. Inicie o Bot WhatsApp
```bash
python run_whatsapp.py
```

**Primeira execução:**
1. Um QR Code aparecerá no terminal
2. Abra o WhatsApp no celular
3. Vá em **Configurações** → **Aparelhos conectados**
4. Escaneie o QR Code

**Sessão salva:**
- A sessão é salva em `whatsapp_session/`
- Nas próximas execuções, conectará automaticamente

## 🎨 Funcionalidades Avançadas

### Reconhecimento de Sintomas
O bot detecta automaticamente a especialidade baseado em palavras-chave:

- **Oftalmologia:** olho, vista, visão, enxergar, óculos
- **Cardiologia:** peito, coração, pressão, batimento
- **Odontologia:** dente, boca, gengiva, canal, cárie
- **Clínica Geral:** febre, gripe, tosse, dor de cabeça

### Sistema de Taxas Inteligente

- **1ª Remarcação:** Gratuita
- **2ª+ Remarcação:** R$ 30,00
- **Remarcação <24h:** R$ 50,00
- **Cancelamento <24h:** R$ 50,00
- **Cancelamento ≥24h:** Gratuito

### Horários de Funcionamento

- **Segunda a Sexta:** 7h às 19h
- **Sábado:** 8h às 13h
- **Domingo:** Fechado

O sistema valida automaticamente horários fora do expediente.

## 🔒 Segurança

**Nunca commite:**
- `.env`
- `credentials.json`
- `token.json`
- `whatsapp_session/`
- `chroma_db/`
- `agendamentos.db`

Todos já estão no `.gitignore`.

## 🐛 Troubleshooting

### WhatsApp desconectando
- Mantenha `run_whatsapp.py` sempre ativo
- Evite usar a mesma conta em múltiplos dispositivos

### Erro: "credentials.json não encontrado"
- Baixe as credenciais OAuth do Google Cloud Console
- Salve como `credentials.json` na raiz

### ChromaDB não encontrado
- Execute **POST /clinica/reindex** após adicionar PDFs
- O banco de vetores será criado automaticamente

### RAG não responde corretamente
- Verifique se há PDFs em `documents/`
- Reindexe os documentos via API
- Confira se a OpenAI API Key está válida

### Banco de dados não inicializa
```bash
# Recrie o banco
rm agendamentos.db
python -m database.init_db
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'Adiciona nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

---

**⭐ Se este projeto foi útil, considere dar uma estrela!**