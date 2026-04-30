let messages = [
    {role: "assistant", content: "👋 Здравствуйте! Я AI-ассистент разработчика и поддержки пользователей.\n\n📋 Команды разработчика:\n/help - список команд\n/branch - текущая ветка Git\n/files - файлы в проекте\n/structure - структура проекта\n/readme - документация проекта\n\n👥 Команды поддержки пользователей:\n/support - чат с поддержкой\n/faq - просмотр FAQ\n/users - управление пользователями\n/tickets - управление тикетами\n/stats - статистика поддержки\n\n💬 Примеры вопросов для поддержки:\n• \"Почему не работает авторизация?\"\n• \"Как обновить тарифный план?\"\n• \"Какие системные требования?\"\n• \"Как восстановить доступ к аккаунту?\""}
];
let isLoading = false;
let currentResponseDiv = null;
let currentResponseText = "";

// Загрузка статуса RAG и поддержки
async function loadStatus() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        document.getElementById('statusText').innerHTML = '✅ Сервис готов';
        document.getElementById('ragStatus').innerHTML = `${data.rag_chunks} чанков`;
        document.getElementById('supportStatus').innerHTML = `${data.support_chunks} FAQ`;
        return true;
    } catch (e) {
        document.getElementById('statusText').innerHTML = '⚠️ Ошибка';
        document.getElementById('ragStatus').innerHTML = 'недоступен';
        document.getElementById('supportStatus').innerHTML = 'недоступен';
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
            let badges = '';
            if (msg.ragUsed) badges += '<span class="rag-badge">RAG</span> ';
            if (msg.supportUsed) badges += '<span class="support-badge">SUPPORT</span> ';
            contentHtml += `<div class="message-meta">🤖 Ассистент ${badges}${msg.latency ? `• ⚡ ${msg.latency}ms` : ''}</div>`;
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
function startTyping(content, finalContent, sources, ragUsed, supportUsed, latency) {
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
            let badges = '';
            if (ragUsed) badges += '<span class="rag-badge">RAG</span> ';
            if (supportUsed) badges += '<span class="support-badge">SUPPORT</span> ';
            metaDiv.innerHTML = `🤖 Ассистент ${badges}• ⚡ ${latency}ms`;
            messageDiv.querySelector('.message-content').appendChild(metaDiv);
            
            messageDiv.id = '';
        }
    }
    
    typeChar();
}

// Обработка команд поддержки
async function handleSupportCommand(command, args = '') {
    try {
        let endpoint = '';
        let method = 'GET';
        let body = null;
        
        switch(command) {
            case '/support':
                if (args.trim()) {
                    // Чат с поддержкой
                    endpoint = '/support/chat';
                    method = 'POST';
                    body = JSON.stringify({
                        messages: [{role: 'user', content: args}],
                        temperature: 0.4,
                        max_tokens: 500
                    });
                } else {
                    return "Используйте: /support [ваш вопрос]\nПример: /support Почему не работает авторизация?";
                }
                break;
            case '/faq':
                endpoint = '/support/faq';
                break;
            case '/users':
                endpoint = '/support/users';
                break;
            case '/tickets':
                endpoint = '/support/tickets';
                break;
            case '/stats':
                endpoint = '/support/stats';
                break;
            default:
                return `Неизвестная команда поддержки: ${command}`;
        }
        
        const response = await fetch(endpoint, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: body
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        // Форматирование ответа
        if (command === '/support') {
            return `🤖 Ассистент поддержки:\n\n${data.response}\n\n📊 Источники: ${data.sources?.length || 0}\n⚡ Задержка: ${data.latency_ms}ms`;
        } else if (command === '/faq') {
            if (data.length === 0) return "📋 FAQ пуст. Добавьте вопросы через API.";
            return `📋 FAQ (${data.length} вопросов):\n\n${data.slice(0, 5).map((item, i) => `${i+1}. ${item.question}`).join('\n')}`;
        } else if (command === '/users') {
            return `👥 Пользователи: ${data.length} найдено\n\n${data.slice(0, 5).map(user => `• ${user.name} (${user.email})`).join('\n')}`;
        } else if (command === '/stats') {
            return `📊 Статистика поддержки:\n\n• Всего пользователей: ${data.total_users}\n• Активных тикетов: ${data.active_tickets}\n• Решено сегодня: ${data.resolved_today}\n• Среднее время ответа: ${data.avg_response_time}\n• FAQ вопросов: ${data.faq_items}`;
        } else {
            return JSON.stringify(data, null, 2);
        }
        
    } catch (e) {
        console.error(e);
        return `❌ Ошибка при выполнении команды ${command}: ${e.message}`;
    }
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
    
    document.getElementById('metrics').innerHTML = '<span class="loading-spinner"></span> 🔍 Обработка запроса...';
    
    const startTime = Date.now();
    
    try {
        // Проверяем, является ли это командой поддержки
        const supportCommands = ['/support', '/faq', '/users', '/tickets', '/stats'];
        const isSupportCommand = supportCommands.some(cmd => text.startsWith(cmd));
        
        if (isSupportCommand) {
            // Обработка команд поддержки
            const [command, ...argsArray] = text.split(' ');
            const args = argsArray.join(' ');
            
            const result = await handleSupportCommand(command, args);
            const totalTime = Date.now() - startTime;
            
            startTyping(result, result, [], false, true, totalTime);
            
            messages.push({
                role: 'assistant',
                content: result,
                sources: [],
                ragUsed: false,
                supportUsed: true,
                latency: totalTime
            });
            
            document.getElementById('metrics').innerHTML = `✅ Поддержка | ⚡ ${totalTime}ms`;
            
        } else if (text.startsWith('/')) {
            // Обработка обычных команд
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
            
            startTyping(data.response, data.response, data.sources, data.rag_used, false, data.latency_ms);
            
            messages.push({
                role: 'assistant',
                content: data.response,
                sources: data.sources || [],
                ragUsed: data.rag_used || false,
                supportUsed: false,
                latency: data.latency_ms
            });
            
            let statusMsg = `✅ Готово | ⚡ ${data.latency_ms}ms (сеть: ${totalTime}ms)`;
            if (data.sources && data.sources.length > 0) {
                statusMsg += ` | 📚 Источники: ${data.sources.join(', ')}`;
            }
            document.getElementById('metrics').innerHTML = statusMsg;
            
        } else {
            // Обычный чат - пробуем поддержку, потом обычный чат
            try {
                // Сначала пробуем поддержку
                const supportResponse = await fetch('/support/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        messages: [{role: 'user', content: text}],
                        temperature: 0.4,
                        max_tokens: 500
                    })
                });
                
                if (supportResponse.ok) {
                    const supportData = await supportResponse.json();
                    const totalTime = Date.now() - startTime;
                    
                    startTyping(supportData.response, supportData.response, 
                               supportData.sources?.map(s => s.source_name) || [], 
                               false, true, supportData.latency_ms);
                    
                    messages.push({
                        role: 'assistant',
                        content: supportData.response,
                        sources: supportData.sources?.map(s => s.source_name) || [],
                        ragUsed: false,
                        supportUsed: true,
                        latency: supportData.latency_ms
                    });
                    
                    document.getElementById('metrics').innerHTML = `✅ Поддержка | ⚡ ${supportData.latency_ms}ms`;
                } else {
                    throw new Error('Support не доступен');
                }
                
            } catch (supportError) {
                // Если поддержка не сработала, используем обычный чат
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
                
                startTyping(data.response, data.response, data.sources, data.rag_used, false, data.latency_ms);
                
                messages.push({
                    role: 'assistant',
                    content: data.response,
                    sources: data.sources || [],
                    ragUsed: data.rag_used || false,
                    supportUsed: false,
                    latency: data.latency_ms
                });
                
                let statusMsg = `✅ Готово | ⚡ ${data.latency_ms}ms (сеть: ${totalTime}ms)`;
                if (data.sources && data.sources.length > 0) {
                    statusMsg += ` | 📚 Источники: ${data.sources.join(', ')}`;
                }
                document.getElementById('metrics').innerHTML = statusMsg;
            }
        }
        
    } catch (e) {
        console.error(e);
        document.getElementById('metrics').innerHTML = `❌ Ошибка: ${e.message}`;
        
        const errorMsg = `❌ **Ошибка:** ${e.message}\n\nПроверьте, что сервисы работают.`;
        messages.push({role: 'assistant', content: errorMsg, sources: []});
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

// Добавляем обработчики кликов на команды
document.addEventListener('DOMContentLoaded', function() {
    const commandElements = document.querySelectorAll('.commands code');
    commandElements.forEach(element => {
        element.addEventListener('click', function() {
            document.getElementById('messageInput').value = this.textContent;
            document.getElementById('messageInput').focus();
        });
    });
});

loadStatus();
setInterval(loadStatus, 30000);
displayMessages();
