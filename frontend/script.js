const API_URL = 'http://127.0.0.1:8000';

const SESSION_ID = 'session_' + Math.random().toString(36).substring(2, 15);

const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');

sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

window.addEventListener('load', startConversation);

async function startConversation() {
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
        .replace(/📅|✅|🔗|⚠️|👋|🤖|🩺|🦷|👁️|❤️|👤|📞|📧|🏥|📍|📫|🗓️/g, (emoji) => `<span class="emoji">${emoji}</span>`);
    
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
    const message = messageInput.value.trim();
    
    if (!message) return;
    
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
        
        if (!response.ok) {
            throw new Error('Erro na comunicação com o servidor');
        }
        
        const data = await response.json();
        
        showTyping(false);
        
        addMessage(data.message);
        
    } catch (error) {
        showTyping(false);
        addMessage('Desculpe, ocorreu um erro ao processar sua mensagem. Verifique se o servidor está rodando.');
        console.error('Erro:', error);
    } finally {
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

async function resetConversation() {
    try {
        await fetch(`${API_URL}/chatbot/reset?session_id=${SESSION_ID}`, {
            method: 'POST'
        });
        
        chatMessages.innerHTML = '';
        startConversation();
        
    } catch (error) {
        console.error('Erro ao reiniciar:', error);
    }
}

messageInput.focus();