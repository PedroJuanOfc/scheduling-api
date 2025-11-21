// URL da API (ajuste se necessário)
const API_URL = 'http://127.0.0.1:8000';

// Elementos do DOM
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');

// Event listeners
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Função para adicionar mensagem ao chat
function addMessage(text, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Processar quebras de linha e formatação
    const formattedText = text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/📅|✅|🔗|⚠️|👋|🤖/g, (emoji) => `<span>${emoji}</span>`);
    
    contentDiv.innerHTML = `<p>${formattedText}</p>`;
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Scroll para o final
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Função para mostrar/esconder indicador de digitação
function showTyping(show = true) {
    typingIndicator.style.display = show ? 'flex' : 'none';
    if (show) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Função para enviar mensagem
async function sendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Adicionar mensagem do usuário
    addMessage(message, true);
    
    // Limpar input e desabilitar botão
    messageInput.value = '';
    sendButton.disabled = true;
    messageInput.disabled = true;
    
    // Mostrar indicador de digitação
    showTyping(true);
    
    try {
        // Fazer requisição para a API
        const response = await fetch(`${API_URL}/chatbot/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        if (!response.ok) {
            throw new Error('Erro na comunicação com o servidor');
        }
        
        const data = await response.json();
        
        // Esconder indicador de digitação
        showTyping(false);
        
        // Adicionar resposta do bot
        addMessage(data.message);
        
    } catch (error) {
        showTyping(false);
        addMessage('Desculpe, ocorreu um erro ao processar sua mensagem. Verifique se o servidor está rodando.');
        console.error('Erro:', error);
    } finally {
        // Reabilitar input e botão
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// Focar no input ao carregar
messageInput.focus();