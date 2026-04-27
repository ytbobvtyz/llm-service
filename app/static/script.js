let messages = [
    {role: "assistant", content: "👋 Здравствуйте! Я AI-ассистент с доступом к вашим документам.\n\nЗадайте вопрос — я найду информацию в документах и укажу источники."}
];
let isLoading = false;
let currentResponseDiv = null;
let currentResponseText = "";

// Загрузка статуса RAG
async function loadStatus() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        document.getElementById('statusText').innerHTML = '✅ Сервис готов';
        document.getElementById('ragStatus').innerHTML = `${data.rag_chunks} чанков`;
        return true;
    } catch (e) {
        document.getElementById('statusText').innerHTML = '⚠️ Ошибка';
        document.getElementById('ragStatus').innerHTML = 'недоступен';
        return false;
    }
}

// Отображение истории сообщений
function displayMessages() {
    const container = document.getElementById('chatMessages');
    container.innerHTML = '';
    
    messages.forEach(msg => {
        const isUser = msg.role === 'user';
        const div = document.createElement('div');
        div.className = `message ${isUser ? 'user' : 'assistant'}`;
        
        let contentHtml = `<div class="message-content">${(msg.content || '').replace(/\n/g, '<br>')}`;
        
        if (!isUser && msg.sources && msg.sources.length > 0) {
            contentHtml += `<div class="sources">📚 Источники: ${msg.sources.join(', ')}</div>`;
        }
        if (!isUser) {
            contentHtml += `<div class="message-meta">🤖 Ассистент ${msg.ragUsed ? '<span class="rag-badge">RAG</span>' : ''} ${msg.latency ? `• ⚡ ${msg.latency}ms` : ''}</div>`;
        } else {
            contentHtml += `<div class="message-meta">👤 Вы</div>`;
        }
        
        contentHtml += `</div>`;
        div.innerHTML = contentHtml;
        container.appendChild(div);
    });
    
    container.scrollTop = container.scrollHeight;
}

// Построчный вывод
function startTyping(content, finalContent, sources, ragUsed, latency) {
    const container = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = 'typing-message';
    messageDiv.innerHTML = `<div class="message-content"><span class="typing-text"></span><span class="cursor">▌</span></div>`;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    
    const typingSpan = messageDiv.querySelector('.typing-text');
    const cursorSpan = messageDiv.querySelector('.cursor');
    let i = 0;
    
    function typeChar() {
        if (i < finalContent.length) {
            typingSpan.innerHTML += finalContent[i];
            i++;
            setTimeout(typeChar, 5 + Math.random() * 10);
        } else {
            cursorSpan.remove();
            
            if (sources && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.innerHTML = `📚 Источники: ${sources.join(', ')}`;
                messageDiv.querySelector('.message-content').appendChild(sourcesDiv);
            }
            
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            metaDiv.innerHTML = `🤖 Ассистент ${ragUsed ? '<span class="rag-badge">RAG</span>' : ''} • ⚡ ${latency}ms`;
            messageDiv.querySelector('.message-content').appendChild(metaDiv);
            
            messageDiv.id = '';
        }
    }
    
    typeChar();
}

// Отправка сообщения
async function sendMessage() {
    if (isLoading) return;
    
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text) return;
    
    messages.push({role: 'user', content: text});
    displayMessages();
    
    input.value = '';
    isLoading = true;
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    sendBtn.textContent = '⏳ Генерация...';
    
    document.getElementById('metrics').innerHTML = '<span class="loading-spinner"></span> 🔍 Поиск в документах...';
    
    const startTime = Date.now();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                messages: messages,
                temperature: 0.4,
                max_tokens: 768,
                use_rag: true
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const totalTime = Date.now() - startTime;
        
        if (!data.response || data.response === "") {
            throw new Error("Модель вернула пустой ответ. Проверьте Ollama.");
        }
        
        startTyping(data.response, data.response, data.sources, data.rag_used, data.latency_ms);
        
        messages.push({
            role: 'assistant',
            content: data.response,
            sources: data.sources || [],
            ragUsed: data.rag_used || false,
            latency: data.latency_ms
        });
        
        let statusMsg = `✅ Готово | ⚡ ${data.latency_ms}ms (сеть: ${totalTime}ms)`;
        if (data.sources && data.sources.length > 0) {
            statusMsg += ` | 📚 Источники: ${data.sources.join(', ')}`;
        }
        document.getElementById('metrics').innerHTML = statusMsg;
        
    } catch (e) {
        console.error(e);
        document.getElementById('metrics').innerHTML = `❌ Ошибка: ${e.message}`;
        
        const errorMsg = `❌ **Ошибка:** ${e.message}\n\nПроверьте, что Ollama работает и модель загружена.`;
        messages.push({role: 'assistant', content: errorMsg, sources: []});
        displayMessages();
    }
    
    isLoading = false;
    sendBtn.disabled = false;
    sendBtn.textContent = 'Отправить';
    input.focus();
}

document.getElementById('messageInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

loadStatus();
setInterval(loadStatus, 30000);
displayMessages();