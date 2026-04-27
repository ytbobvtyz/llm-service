#!/usr/bin/env python3
# app/main.py
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx

from app.config import config
from app.rag import RAGRetriever
from app.models import ChatRequest, ChatResponse, HealthResponse

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Запуск RAG LLM Service")
    print(f"   Модель: {config.model_name}")
    print(f"   RAG индекс: {config.db_path}")
    app.state.rag = RAGRetriever(config.db_path, config.index_path)
    app.state.client = httpx.AsyncClient(timeout=120.0)
    yield
    # Shutdown
    await app.state.client.aclose()

app = FastAPI(title="RAG LLM Service", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== API ENDPOINTS ==========

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        rag_chunks=len(app.state.rag.chunks),
        model=config.model_name
    )

@app.post("/api/chat")
@limiter.limit(config.rate_limit)
async def chat(request: Request, chat_req: ChatRequest):
    start_time = time.time()
    last_message = chat_req.messages[-1].content if chat_req.messages else ""
    
    # RAG поиск
    sources = []
    rag_context = ""
    if chat_req.use_rag and app.state.rag.chunks:
        chunks = app.state.rag.search(last_message, top_k=3)
        if chunks:
            sources = list(set(c['filename'] for c in chunks))
            rag_context = "\n\nИз документов:\n" + "\n".join([
                f"[{c['filename']}] {c['text'][:400]}..." for c in chunks
            ])
    
    # История диалога
    history = []
    for msg in chat_req.messages[:-1]:
        role = "Пользователь" if msg.role == "user" else "Ассистент"
        history.append(f"{role}: {msg.content}")
    history_text = "\n".join(history[-5:]) if history else "Нет истории"
    
    # Промпт
    prompt = f"""Ты эксперт по логистике. Отвечай по существу.

{rag_context}

История диалога:
{history_text}

Пользователь: {last_message}

Ассистент:"""
    
    try:
        resp = await app.state.client.post(
            f"{config.ollama_url}/api/generate",
            json={
                "model": config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": chat_req.temperature,
                    "num_predict": config.max_tokens
                }
            }
        )
        data = resp.json()
        answer = data.get("response", "")
        
        return ChatResponse(
            response=answer,
            sources=sources,
            latency_ms=int((time.time() - start_time) * 1000),
            rag_used=len(sources) > 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/search")
@limiter.limit("30/minute")
async def rag_search(request: Request, q: str, top_k: int = 3):
    results = app.state.rag.search(q, top_k)
    return {"query": q, "results": results}

# ========== ВЕБ-ИНТЕРФЕЙС ==========

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG LLM Service — Локальный AI-ассистент</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #0d1117 0%, #0a0c10 100%);
            color: #e6edf3;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #58a6ff, #a371f7);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #8b949e;
        }
        
        /* Status Bar */
        .status-bar {
            background: #161b22;
            border-radius: 12px;
            padding: 12px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            border: 1px solid #30363d;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #3fb950;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Chat Container */
        .chat-container {
            background: #161b22;
            border-radius: 16px;
            border: 1px solid #30363d;
            overflow: hidden;
            margin-bottom: 20px;
        }
        
        .chat-messages {
            height: 500px;
            overflow-y: auto;
            padding: 20px;
        }
        
        .message {
            display: flex;
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message.assistant {
            justify-content: flex-start;
        }
        
        .message-content {
            max-width: 75%;
            padding: 12px 18px;
            border-radius: 20px;
            word-wrap: break-word;
            line-height: 1.5;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #1f6feb, #1a5bc4);
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .message.assistant .message-content {
            background: #21262d;
            border-bottom-left-radius: 4px;
        }
        
        .message-meta {
            font-size: 11px;
            color: #8b949e;
            margin-top: 5px;
        }
        
        /* Input Area */
        .input-area {
            display: flex;
            gap: 12px;
            padding: 20px;
            background: #0d1117;
            border-top: 1px solid #30363d;
        }
        
        .input-area input {
            flex: 1;
            padding: 14px 18px;
            border-radius: 28px;
            border: 1px solid #30363d;
            background: #0d1117;
            color: #e6edf3;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }
        
        .input-area input:focus {
            border-color: #58a6ff;
        }
        
        .input-area input:disabled {
            opacity: 0.5;
        }
        
        .input-area button {
            padding: 14px 28px;
            border-radius: 28px;
            border: none;
            background: linear-gradient(135deg, #1f6feb, #1a5bc4);
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, opacity 0.2s;
        }
        
        .input-area button:hover:not(:disabled) {
            opacity: 0.9;
            transform: scale(1.02);
        }
        
        .input-area button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        /* Metrics */
        .metrics {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            color: #8b949e;
            text-align: center;
            padding: 10px;
            background: #161b22;
            border-radius: 8px;
            margin-top: 10px;
        }
        
        .loading-spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #30363d;
            border-top-color: #58a6ff;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            vertical-align: middle;
            margin-right: 8px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .sources {
            font-size: 11px;
            color: #a371f7;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #30363d;
        }
        
        /* Scrollbar */
        .chat-messages::-webkit-scrollbar {
            width: 8px;
        }
        
        .chat-messages::-webkit-scrollbar-track {
            background: #0d1117;
            border-radius: 4px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb {
            background: #30363d;
            border-radius: 4px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: #58a6ff;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            font-size: 12px;
            color: #8b949e;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #30363d;
        }
        
        /* RAG Badge */
        .rag-badge {
            display: inline-block;
            background: #2d1b4e;
            color: #a371f7;
            padding: 2px 8px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 RAG LLM Service</h1>
            <p>Локальный AI-ассистент с поиском по документам</p>
        </div>
        
        <div class="status-bar">
            <div class="status-item">
                <div class="status-dot"></div>
                <span id="status-text">Подключение...</span>
            </div>
            <div class="status-item">
                <span>🦙 Модель: <strong>llama3.2:3b</strong></span>
            </div>
            <div class="status-item">
                <span>📄 RAG: <strong id="rag-status">загрузка...</strong></span>
            </div>
        </div>
        
        <div class="chat-container">
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-content">
                        👋 Здравствуйте! Я AI-ассистент с доступом к вашим документам.
                        <br><br>
                        Задайте вопрос о логистике, перевозках или документах — я найду информацию и укажу источники.
                    </div>
                </div>
            </div>
            
            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Задайте вопрос..." autofocus>
                <button id="sendBtn" onclick="sendMessage()">Отправить</button>
            </div>
        </div>
        
        <div class="metrics" id="metrics">
            💡 Напишите вопрос, и я найду ответ в документах
        </div>
        
        <div class="footer">
            🔒 Приватный сервис | Все данные на вашем сервере | RAG на основе FAISS
        </div>
    </div>
    
    <script>
        let messages = [
            {role: "assistant", content: "👋 Здравствуйте! Я AI-ассистент с доступом к вашим документам.\n\nЗадайте вопрос — я найду информацию в документах и укажу источники."}
        ];
        let isLoading = false;
        
        // Загрузка статуса RAG при старте
        async function loadRAGStatus() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                document.getElementById('rag-status').innerHTML = `📄 ${data.rag_chunks} чанков`;
                document.getElementById('status-text').innerHTML = '✅ Сервис готов';
            } catch (e) {
                document.getElementById('rag-status').innerHTML = '❌ RAG недоступен';
                document.getElementById('status-text').innerHTML = '⚠️ Ошибка подключения';
            }
        }
        
        // Отображение сообщений
        function displayMessages() {
            const container = document.getElementById('chatMessages');
            container.innerHTML = messages.map(msg => {
                const isUser = msg.role === 'user';
                const content = (msg.content || '').replace(/\\n/g, '<br>');
                
                let sourcesHtml = '';
                if (msg.sources && msg.sources.length > 0) {
                    sourcesHtml = `<div class="sources">📚 Источники: ${msg.sources.join(', ')}</div>`;
                }
                
                let ragBadge = '';
                if (msg.ragUsed) {
                    ragBadge = `<span class="rag-badge" style="margin-left: 8px;">RAG</span>`;
                }
                
                return `
                    <div class="message ${isUser ? 'user' : 'assistant'}">
                        <div class="message-content">
                            ${content}
                            ${sourcesHtml}
                            <div class="message-meta">
                                ${isUser ? '👤 Вы' : '🤖 Ассистент'} ${ragBadge}
                                ${msg.latency ? ` • ⚡ ${msg.latency}ms` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            container.scrollTop = container.scrollHeight;
        }
        
        // Отправка сообщения
        async function sendMessage() {
            if (isLoading) return;
            
            const input = document.getElementById('messageInput');
            const text = input.value.trim();
            if (!text) return;
            
            // Добавляем сообщение пользователя
            messages.push({role: 'user', content: text});
            displayMessages();
            
            // Очищаем и блокируем
            input.value = '';
            isLoading = true;
            const sendBtn = document.getElementById('sendBtn');
            sendBtn.disabled = true;
            sendBtn.textContent = '⏳ Отправка...';
            
            // Обратная связь: показываем, что идёт поиск
            document.getElementById('metrics').innerHTML = '<span class="loading-spinner"></span> 🔍 Поиск в документах...';
            
            try {
                const startTime = Date.now();
                
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
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                const totalTime = Date.now() - startTime;
                
                // Добавляем ответ ассистента
                messages.push({
                    role: 'assistant',
                    content: data.response || "⚠️ Пустой ответ от модели",
                    sources: data.sources || [],
                    ragUsed: data.rag_used || false,
                    latency: data.latency_ms
                });
                displayMessages();
                
                // Обратная связь: результат
                let statusMsg = `✅ Готово | ⚡ ${data.latency_ms}ms (сеть: ${totalTime}ms)`;
                if (data.sources && data.sources.length > 0) {
                    statusMsg += ` | 📚 Источники: ${data.sources.join(', ')}`;
                } else if (data.rag_used === false) {
                    statusMsg += ` | ⚠️ RAG не найден — модель отвечает из знаний`;
                }
                document.getElementById('metrics').innerHTML = statusMsg;
                
            } catch (e) {
                console.error(e);
                document.getElementById('metrics').innerHTML = `❌ Ошибка: ${e.message}. Проверьте, что сервер запущен.`;
                
                messages.push({
                    role: 'assistant',
                    content: `❌ **Ошибка:** ${e.message}\n\nПроверьте, что сервер запущен и Ollama работает.`,
                    sources: []
                });
                displayMessages();
            }
            
            isLoading = false;
            sendBtn.disabled = false;
            sendBtn.textContent = 'Отправить';
            input.focus();
        }
        
        // Enter для отправки
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        // Загрузка статуса при старте
        loadRAGStatus();
        setInterval(loadRAGStatus, 30000);
        displayMessages();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    return HTML_TEMPLATE

# ========== ЗАПУСК ==========

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 RAG LLM Service запущен")
    print(f"   Web UI: http://localhost:{config.port}")
    print(f"   API: http://localhost:{config.port}/api/chat")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info"
    )