let messages = [];
let isLoading = false;

// Загрузка статуса системы
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Обновление статус индикаторов
        const ollamaStatus = data.components.ollama?.status || 'unknown';
        const yandexStatus = data.components.yandex_api?.status || 'unknown';
        const chromaStatus = data.components.chromadb?.status || 'unknown';
        const docsStatus = data.components.documents?.status || 'unknown';
        
        // Главный статус
        document.getElementById('statusText').textContent = data.status === 'operational' ? '✅ Система готова' : '⚠️ Ограниченная работа';
        
        // Статус индикаторы
        updateStatusDot('ollamaDot', ollamaStatus);
        updateStatusDot('yandexDot', yandexStatus);
        updateStatusDot('chromaDot', chromaStatus);
        updateStatusDot('docsDot', docsStatus);
        updateStatusDot('mainStatusDot', ollamaStatus === 'healthy' ? 'ok' : 'warning');
        
        // Количество документов
        document.getElementById('docCount').textContent = docsStatus === 'exists' ? '3' : '0';
        
        addLogEntry('Статус загружен', 'info');
        return true;
    } catch (e) {
        console.error('Ошибка загрузки статуса:', e);
        document.getElementById('statusText').textContent = '❌ Ошибка подключения';
        addLogEntry('Ошибка загрузки статуса: ' + e.message, 'error');
        return false;
    }
}

function updateStatusDot(id, status) {
    const dot = document.getElementById(id);
    if (dot) {
        dot.className = 'status-dot';
        if (status === 'healthy' || status === 'configured' || status === 'exists' || status === 'ok') {
            dot.classList.add('ok');
        } else if (status === 'unhealthy' || status === 'not_configured' || status === 'missing') {
            dot.classList.add('error');
        } else {
            dot.classList.add('warning');
        }
    }
}

// Добавление записи в лог
function addLogEntry(message, type = 'info') {
    const log = document.getElementById('debugLog');
    if (log) {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.textContent = message;
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
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
        
        // JSON данные
        if (!isUser && msg.json) {
            contentHtml += `<details class="json-block"><summary>📊 JSON данные</summary><pre>${JSON.stringify(msg.json, null, 2)}</pre></details>`;
        }
        
        contentHtml += `</div>`;
        div.innerHTML = contentHtml;
        container.appendChild(div);
    });
    
    container.scrollTop = container.scrollHeight;
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
    sendBtn.textContent = '⏳ Обработка...';
    
    addLogEntry('Отправка запроса: ' + text.substring(0, 50) + '...', 'info');
    
    const startTime = Date.now();
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: text
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const totalTime = Date.now() - startTime;
        
        addLogEntry('Получен ответ за ' + totalTime + 'мс', 'success');
        
        // Логирование шагов
        if (data.debug_info) {
            const steps = data.debug_info.step || 'unknown';
            addLogEntry('Этап: ' + steps, 'info');
        }
        
        messages.push({
            role: 'assistant',
            content: data.text,
            json: data.json,
            debug_info: data.debug_info
        });
        
        displayMessages();
        
    } catch (e) {
        console.error(e);
        addLogEntry('Ошибка: ' + e.message, 'error');
        
        const errorMsg = `❌ Ошибка: ${e.message}\n\nПроверьте, что сервисы работают и API ключ настроен.`;
        messages.push({role: 'assistant', content: errorMsg});
        displayMessages();
    }
    
    isLoading = false;
    sendBtn.disabled = false;
    sendBtn.textContent = 'Отправить';
    input.focus();
}

// Установка вопроса из быстрых кнопок
function setQuestion(question) {
    document.getElementById('messageInput').value = question;
    document.getElementById('messageInput').focus();
}

// Инициализация
document.getElementById('messageInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Загрузка статуса при старте
loadStatus();
setInterval(loadStatus, 30000);

// Подключение к SSE потоку отладки
if (typeof EventSource !== 'undefined') {
    const eventSource = new EventSource('/debug/stream');
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            addLogEntry(data.message, data.type === 'error' ? 'error' : 'info');
        } catch (e) {
            console.error('Ошибка парсинга SSE:', e);
        }
    };
    
    eventSource.onerror = function() {
        addLogEntry('SSE отключен', 'warning');
    };
}
