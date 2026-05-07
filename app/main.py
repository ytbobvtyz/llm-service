import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import config
from app.api import router
from app.api.models import StatusResponse
from agent.core import initialize_agent
from indexing.indexer import DocumentIndexer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("=" * 60)
    print("🚀 Запуск логистического агента для анализа ограничений на просушку дорог")
    print(f"   Модель: {config.ollama_model}")
    print(f"   Яндекс API ключ: {'установлен' if config.yandex_maps_api_key else 'отсутствует'}")
    print(f"   ChromaDB путь: {config.chroma_db_path}")
    print(f"   Документы: {config.resolutions_path}")
    print("=" * 60)
    
    # Инициализация индексатора документов
    app.state.indexer = DocumentIndexer(
        resolutions_path=config.resolutions_path,
        chroma_db_path=config.chroma_db_path,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap
    )
    
    # Инициализация агента
    app.state.agent = initialize_agent()
    
    yield
    
    # Shutdown
    print("Завершение работы логистического агента...")


app = FastAPI(
    title="Логистический агент для анализа ограничений на просушку дорог",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
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

# Static files
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Корневой маршрут для веб-интерфейса
@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = "app/static/index.html"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Логистический агент для анализа ограничений на просушку дорог</h1>", status_code=404)

# Статус системы
@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    from app.api.models import ComponentStatus, StatusResponse
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
    yandex_status = "unknown"
    if config.yandex_maps_api_key:
        yandex_status = "configured"
    else:
        yandex_status = "not_configured"
    
    # Проверка ChromaDB
    chroma_status = "unknown"
    if os.path.exists(config.chroma_db_path):
        chroma_status = "exists"
    
    return StatusResponse(
        status="operational",
        components={
            "ollama": ComponentStatus(status=ollama_status, message="Локальная LLM модель"),
            "yandex_api": ComponentStatus(status=yandex_status, message="API Яндекс Карт"),
            "chromadb": ComponentStatus(status=chroma_status, message="Векторная база данных"),
            "documents": ComponentStatus(status="exists" if os.path.exists(config.resolutions_path) else "missing", message="Документы с ограничениями")
        }
    )

# Include API routers
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level="info"
    )
