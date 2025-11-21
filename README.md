# 🤖 Chatbot de Agendamento com IA

Sistema completo de agendamento com chatbot inteligente que processa linguagem natural, cria eventos no Google Calendar e cards no Trello automaticamente.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Funcionalidades

- ✅ **Processamento de Linguagem Natural** com Google Gemini
- ✅ **Integração com Google Calendar** - Cria eventos automaticamente
- ✅ **Integração com Trello** - Cria cards vinculados aos eventos
- ✅ **Detecção Inteligente de Datas** - Entende "amanhã", "próxima semana", etc.
- ✅ **Verificação de Disponibilidade** - Mostra horários livres
- ✅ **Interface de Chat Moderna** - Frontend responsivo e bonito
- ✅ **API REST Completa** - Documentação automática com Swagger

## 🎯 Demonstração

**Exemplos de interação:**
```
Você: "Quero marcar uma consulta amanhã às 14h"
Bot: "✅ Consulta agendada com sucesso para 22/11/2025 às 14:00!
      📅 Evento criado no Google Calendar
      ✅ Card criado no Trello"

Você: "Quais horários estão disponíveis essa semana?"
Bot: "Encontrei horários disponíveis nos próximos 7 dias:
      📅 22/11/2025 (Friday): 09:00, 10:00, 14:00, 15:00
      📅 25/11/2025 (Monday): 09:00, 11:00, 16:00"
```

## 🚀 Tecnologias Utilizadas

### Backend
- **FastAPI** - Framework web moderno e rápido
- **Python 3.8+** - Linguagem principal
- **Google Gemini API** - Processamento de linguagem natural
- **Google Calendar API** - Gerenciamento de eventos
- **Trello API** - Gerenciamento de cards
- **Pydantic** - Validação de dados

### Frontend
- **HTML5/CSS3/JavaScript** - Interface de chat
- **Fetch API** - Comunicação com backend

## 📦 Pré-requisitos

- Python 3.8 ou superior
- Conta Google (para Calendar API)
- Conta Trello (para Trello API)
- Conta Google AI Studio (para Gemini API - gratuita)

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/chatbot-agendamento-backend.git
cd chatbot-agendamento-backend
```

### 2. Crie e ative o ambiente virtual

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

## 🔑 Configuração das APIs

### 1. Google Gemini API (IA)

1. Acesse: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Faça login com sua conta Google
3. Clique em **"Get API Key"** ou **"Create API Key"**
4. Copie a API Key gerada

### 2. Google Calendar API

#### 2.1. Criar Projeto no Google Cloud Console

1. Acesse: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Clique em **"Select a project"** → **"NEW PROJECT"**
3. Nome: `Chatbot Agendamento`
4. Clique em **"CREATE"**

#### 2.2. Ativar a API do Google Calendar

1. Vá em **"APIs & Services"** → **"Library"**
2. Busque: **"Google Calendar API"**
3. Clique em **"ENABLE"**

#### 2.3. Configurar OAuth Consent Screen

1. Vá em **"APIs & Services"** → **"OAuth consent screen"**
2. Selecione **"External"** → **"CREATE"**
3. Preencha:
   - **App name:** `Chatbot Agendamento`
   - **User support email:** Seu email
   - **Developer contact:** Seu email
4. Clique em **"SAVE AND CONTINUE"**

5. Em **"Scopes"**, clique em **"ADD OR REMOVE SCOPES"**
6. Busque e marque: `https://www.googleapis.com/auth/calendar`
7. Clique em **"UPDATE"** → **"SAVE AND CONTINUE"**

8. Em **"Test users"**, clique em **"+ ADD USERS"**
9. Adicione seu email → **"ADD"** → **"SAVE AND CONTINUE"**

#### 2.4. Criar Credenciais OAuth

1. Vá em **"APIs & Services"** → **"Credentials"**
2. Clique em **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. **Application type:** `Desktop app`
4. **Name:** `Chatbot Agendamento Desktop`
5. Clique em **"CREATE"**
6. Clique em **"DOWNLOAD JSON"**
7. Salve o arquivo como `credentials.json` na raiz do projeto

### 3. Trello API

#### 3.1. Criar Power-Up

1. Acesse: [https://trello.com/power-ups/admin](https://trello.com/power-ups/admin)
2. Clique em **"New"**
3. Preencha:
   - **Name:** `Chatbot Agendamento`
   - **Workspace:** Selecione seu workspace
   - **Iframe connector URL:** `http://localhost`
4. Clique em **"Create"**

#### 3.2. Obter API Key

1. Na página do Power-Up, vá na aba **"API Key"**
2. Copie a **API Key**

#### 3.3. Gerar Token

1. Use este link (substitua `SUA_API_KEY`):
```
https://trello.com/1/authorize?key=SUA_API_KEY&name=ChatbotAgendamento&expiration=never&response_type=token&scope=read,write
```
2. Clique em **"Allow"**
3. Copie o **Token** gerado

#### 3.4. Obter Board ID e List ID

1. Abra seu quadro do Trello
2. Olhe a URL: `https://trello.com/b/aBc123Xy/nome-quadro`
3. **Board ID** = `aBc123Xy` (parte entre `/b/` e a próxima `/`)

4. Adicione `.json` na URL: `https://trello.com/b/aBc123Xy/nome-quadro.json`
5. Busque por `"lists"` (Ctrl+F)
6. Copie o `"id"` da lista onde quer criar os cards

## ⚙️ Configuração do Arquivo .env

Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
```env
# Google Calendar API
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary

# Trello API
TRELLO_API_KEY=sua_api_key_aqui
TRELLO_TOKEN=seu_token_aqui
TRELLO_BOARD_ID=seu_board_id_aqui
TRELLO_LIST_ID=seu_list_id_aqui

# Google Gemini API
GEMINI_API_KEY=sua_gemini_api_key_aqui

# Configurações da Aplicação
API_HOST=0.0.0.0
API_PORT=8000
```

**Substitua os valores:**
- `sua_api_key_aqui` → API Key do Trello
- `seu_token_aqui` → Token do Trello
- `seu_board_id_aqui` → Board ID do Trello
- `seu_list_id_aqui` → List ID do Trello
- `sua_gemini_api_key_aqui` → API Key do Gemini

## ▶️ Executando o Projeto

### 1. Iniciar o Backend
```bash
uvicorn main:app --reload
```

O servidor estará rodando em: `http://127.0.0.1:8000`

### 2. Fazer a Primeira Autenticação do Google Calendar

1. Acesse: `http://127.0.0.1:8000/test-google-calendar`
2. Uma janela do navegador abrirá pedindo permissão
3. **Se aparecer "Google hasn't verified this app":**
   - Clique em **"Advanced"** (Avançado)
   - Clique em **"Go to Chatbot Agendamento (unsafe)"**
4. Clique em **"Allow"** (Permitir)
5. Um arquivo `token.json` será criado automaticamente

### 3. Abrir o Frontend

Abra o arquivo `frontend/index.html` no navegador:

**Windows:**
```bash
start frontend\index.html
```

**Linux:**
```bash
xdg-open frontend/index.html
```

**Mac:**
```bash
open frontend/index.html
```

Ou simplesmente arraste o arquivo para o navegador.

## 📚 Documentação da API

Acesse a documentação interativa em: `http://127.0.0.1:8000/docs`

### Principais Endpoints

#### POST /chatbot/message
Envia mensagem em linguagem natural para o chatbot.

**Request:**
```json
{
  "message": "Quero marcar uma consulta amanhã às 14h"
}
```

**Response:**
```json
{
  "message": "✅ Consulta agendada com sucesso para 22/11/2025 às 14:00!...",
  "intent_detected": "create_appointment",
  "parameters_extracted": {...},
  "action_taken": "create_appointment",
  "data": {
    "calendar_event_id": "...",
    "event_link": "...",
    "trello_card_id": "..."
  }
}
```

#### POST /scheduling/check-availability
Verifica disponibilidade nos próximos N dias.

**Request:**
```json
{
  "days": 7
}
```

#### POST /scheduling/create-appointment
Cria agendamento manualmente (estruturado).

#### GET /scheduling/appointments
Lista agendamentos futuros.

## 🧪 Testando

### Testar Conexões
```bash
# Testar Google Calendar
curl http://127.0.0.1:8000/test-google-calendar

# Testar Trello
curl http://127.0.0.1:8000/test-trello

# Testar Gemini
curl http://127.0.0.1:8000/test-gemini
```

### Exemplos de Mensagens para o Chatbot

- "Quais horários estão disponíveis essa semana?"
- "Quero marcar uma consulta amanhã às 14h"
- "Marcar consulta dia 25 às 10h"
- "Lista meus agendamentos"
- "Quero agendar para próxima terça às 15h"

## 📁 Estrutura do Projeto
```
chatbot-agendamento-backend/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── models/
│   ├── __init__.py
│   └── schemas.py
├── routers/
│   ├── __init__.py
│   ├── chatbot.py
│   └── scheduling.py
├── services/
│   ├── __init__.py
│   ├── gemini_service.py
│   ├── google_calendar_service.py
│   └── trello_service.py
├── .env
├── .env.example
├── .gitignore
├── config.py
├── credentials.json
├── main.py
├── README.md
├── requirements.txt
└── token.json
```

## 🔒 Segurança

⚠️ **IMPORTANTE:** Nunca commite os seguintes arquivos:
- `.env`
- `credentials.json`
- `token.json`

Eles contêm informações sensíveis e já estão listados no `.gitignore`.

## 🐛 Solução de Problemas

### Erro: "Arquivo credentials.json não encontrado"
- Certifique-se de que o arquivo `credentials.json` está na raiz do projeto
- Verifique se seguiu todos os passos da configuração do Google Calendar API

### Erro: "Google hasn't verified this app"
- Isso é normal em modo de desenvolvimento
- Clique em "Advanced" → "Go to Chatbot Agendamento (unsafe)"

### Erro 403 no Trello
- Verifique se a API Key e Token estão corretos no `.env`
- Certifique-se de que o Token tem permissões de leitura e escrita

### CORS Error no Frontend
- Certifique-se de que o backend está rodando
- Verifique se o `main.py` tem o middleware CORS configurado

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:
1. Fazer fork do projeto
2. Criar uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abrir um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT.

## 👨‍💻 Autor

Desenvolvido com ❤️ por Pedro Juan


---

**⭐ Se este projeto te ajudou, considere dar uma estrela!**
