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

# ========== API ==========

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

# Веб-интерфейс (оставляем из предыдущей версии)
HTML_TEMPLATE = '''...'''  # Здесь тот же HTML, что был ранее

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    return HTML_TEMPLATE