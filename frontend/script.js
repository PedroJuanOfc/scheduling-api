// Debug: detectar reloads
window.addEventListener('beforeunload', (e) => {
    console.log('⚠️ PÁGINA VAI RECARREGAR!');
});

console.log('🚀 Script carregado');

const API_URL = 'http://127.0.0.1:8000';

let SESSION_ID = sessionStorage.getItem('chatbot_session_id');
let isNewSession = false;

if (!SESSION_ID) {
    SESSION_ID = 'session_' + Math.random().toString(36).substring(2, 15);
    sessionStorage.setItem('chatbot_session_id', SESSION_ID);
    isNewSession = true;
}

console.log('📋 Session ID:', SESSION_ID, '| Nova sessão:', isNewSession);

const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');

sendButton.addEventListener('click', function(e) {
    e.preventDefault();
    console.log('🖱️ Botão clicado');
    sendMessage();
});

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        console.log('⌨️ Enter pressionado');
        sendMessage();
    }
});

window.addEventListener('load', initChat);

async function initChat() {
    console.log('🏁 initChat chamado');
    if (isNewSession) {
        await startConversation();
    } else {
        addMessage("Olá novamente! 👋 Como posso te ajudar?\n\nVocê pode:\n• Agendar uma consulta\n• Ver horários disponíveis\n• Tirar dúvidas");
    }
}

async function startConversation() {
    console.log('🎬 startConversation chamado');
    showTyping(true);
    
    try {
        const response = await fetch(`${API_URL}/chatbot/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: "oi",
                session_id: SESSION_ID
            })
        });
        
        if (!response.ok) {
            throw new Error('Erro na comunicação com o servidor');
        }
        
        const data = await response.json();
        showTyping(false);
        
        chatMessages.innerHTML = '';
        addMessage(data.message);
        
    } catch (error) {
        showTyping(false);
        addMessage('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
        console.error('Erro:', error);
    }
}

function addMessage(text, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    let formattedText = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/📅|✅|🔗|⚠️|👋|🤖|🩺|🦷|👁️|❤️|👤|📞|📧|🏥|📍|📫|🗓️|😊|•/g, (match) => `<span class="emoji">${match}</span>`);
    
    contentDiv.innerHTML = formattedText;
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping(show = true) {
    typingIndicator.style.display = show ? 'flex' : 'none';
    if (show) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

async function sendMessage() {
    console.log('📤 sendMessage chamado');
    const message = messageInput.value.trim();
    
    if (!message) {
        console.log('⚠️ Mensagem vazia, retornando');
        return;
    }
    
    console.log('📤 Enviando:', message);
    
    addMessage(message, true);
    
    messageInput.value = '';
    sendButton.disabled = true;
    messageInput.disabled = true;
    
    showTyping(true);
    
    try {
        const response = await fetch(`${API_URL}/chatbot/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: message,
                session_id: SESSION_ID
            })
        });
        
        console.log('📥 Response status:', response.status);
        
        if (!response.ok) {
            throw new Error('Erro na comunicação com o servidor');
        }
        
        const data = await response.json();
        
        console.log('📥 Data recebida:', data);
        
        showTyping(false);
        
        addMessage(data.message);
        
    } catch (error) {
        showTyping(false);
        console.error('❌ Erro:', error);
        addMessage('Desculpe, ocorreu um erro ao processar sua mensagem.');
    } finally {
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

async function resetConversation() {
    console.log('🔄 resetConversation chamado');
    try {
        await fetch(`${API_URL}/chatbot/reset?session_id=${SESSION_ID}`, {
            method: 'POST'
        });
        
        SESSION_ID = 'session_' + Math.random().toString(36).substring(2, 15);
        sessionStorage.setItem('chatbot_session_id', SESSION_ID);
        isNewSession = true;
        
        chatMessages.innerHTML = '';
        await startConversation();
        
    } catch (error) {
        console.error('Erro ao reiniciar:', error);
    }
}

messageInput.focus();