"""
API маршруты для логистического агента.
"""
import logging
import asyncio
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from app.config import config
from app.api.models import (
    ChatRequest,
    ChatResponse,
    StatusResponse,
    ComponentStatus,
    ReindexRequest,
    ReindexResponse,
    DebugEvent
)
from agent.core import get_agent, initialize_agent
from indexing.indexer import DocumentIndexer

logger = logging.getLogger(__name__)

# Инициализация rate limiter
limiter = Limiter(key_func=get_remote_address)

# Создание роутера
router = APIRouter()

# Глобальные состояния
_indexer: Optional[DocumentIndexer] = None
_agent = None


def get_indexer() -> DocumentIndexer:
    """Получение индексатора документов."""
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer(
            resolutions_path=config.resolutions_path,
            chroma_db_path=config.chroma_db_path,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
    return _indexer


def get_logistics_agent():
    """Получение агента."""
    global _agent
    if _agent is None:
        _agent = initialize_agent()
    return _agent


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Получение статуса системы."""
    import httpx
    
    # Проверка Ollama
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.ollama_base_url}/api/tags", timeout=5)
            ollama_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        ollama_status = "unhealthy"
    
    # Проверка Яндекс API
    yandex_status = "configured" if config.yandex_maps_api_key else "not_configured"
    
    # Проверка ChromaDB
    import os
    chroma_status = "exists" if os.path.exists(config.chroma_db_path) else "missing"
    
    # Проверка документов
    docs_status = "exists" if os.path.exists(config.resolutions_path) else "missing"
    
    return StatusResponse(
        status="operational",
        components={
            "ollama": ComponentStatus(status=ollama_status, message="Локальная LLM модель"),
            "yandex_api": ComponentStatus(status=yandex_status, message="API Яндекс Карт"),
            "chromadb": ComponentStatus(status=chroma_status, message="Векторная база данных"),
            "documents": ComponentStatus(status=docs_status, message="Документы с ограничениями")
        }
    )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{config.rate_limit}/minute")
async def chat(request: Request, chat_req: ChatRequest):
    """Основной эндпоинт для общения с агентом."""
    try:
        agent = get_logistics_agent()
        
        if agent is None:
            raise HTTPException(status_code=503, detail="Агент не инициализирован")
        
        # Обработка запроса
        result = await agent.process_request(chat_req.message)
        
        return ChatResponse(
            text=result.get("text", ""),
            json=result.get("json"),
            debug_info=result.get("debug_info"),
            session_id=chat_req.session_id
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке чата: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex", response_model=ReindexResponse)
async def reindex(request: Request, reindex_req: ReindexRequest = ReindexRequest()):
    """Переиндексация документов."""
    try:
        indexer = get_indexer()
        
        # Переиндексация
        result = indexer.index_directory()
        
        if result.get("success"):
            stats = result.get("stats", {})
            return ReindexResponse(
                success=True,
                message="Индексация завершена успешно",
                stats=stats
            )
        else:
            return ReindexResponse(
                success=False,
                message=f"Ошибка индексации: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при переиндексации: {e}")
        return ReindexResponse(
            success=False,
            message=str(e)
        )


@router.get("/debug/stream")
async def debug_stream():
    """SSE поток отладочной информации."""
    import asyncio
    import json
    from fastapi.encoders import jsonable_encoder
    
    async def event_generator():
        # Отправляем тестовое событие
        event = DebugEvent(
            type="system_ready",
            message="Система готова к работе",
            data={"version": "1.0.0"}
        )
        yield f"data: {json.dumps(jsonable_encoder(event))}\n\n"
        await asyncio.sleep(0.1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
