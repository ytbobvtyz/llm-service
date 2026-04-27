import time
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import config
from app.models import ChatRequest, ChatResponse, HealthResponse

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

# Глобальные состояния (будут установлены в main.py)
rag_instance = None
ollama_client_instance = None

def setup(rag, ollama_client):
    global rag_instance, ollama_client_instance
    rag_instance = rag
    ollama_client_instance = ollama_client

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        rag_chunks=len(rag_instance.chunks) if rag_instance else 0,
        model=config.model_name
    )

@router.post("/api/chat")
@limiter.limit(config.rate_limit)
async def chat(request: Request, chat_req: ChatRequest):
    start_time = time.time()
    last_message = chat_req.messages[-1].content if chat_req.messages else ""
    
    # RAG поиск
    sources = []
    rag_context = ""
    if chat_req.use_rag and rag_instance and rag_instance.chunks:
        chunks = rag_instance.search(last_message, top_k=3)
        if chunks:
            sources = list(set(c['filename'] for c in chunks))
            rag_context = "\n\nИз документов:\n" + "\n".join([
                f"[{c['filename']}] {c['text'][:400]}..." for c in chunks
            ])
    
    # Генерация ответа
    response, latency = await ollama_client_instance.generate(chat_req, rag_context)
    
    return ChatResponse(
        response=response,
        sources=sources,
        latency_ms=latency,
        rag_used=len(sources) > 0
    )

@router.get("/api/rag/search")
@limiter.limit("30/minute")
async def rag_search(request: Request, q: str, top_k: int = 3):
    if not rag_instance:
        raise HTTPException(status_code=503, detail="RAG not loaded")
    results = rag_instance.search(q, top_k)
    return {"query": q, "results": results}