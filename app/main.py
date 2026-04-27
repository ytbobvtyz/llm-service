import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import config
from app.rag import RAGRetriever
from app.ollama_client import OllamaClient
from app.api import router, setup as setup_api, limiter

# Убедимся, что папка для статики существует
os.makedirs("app/static", exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Запуск RAG LLM Service")
    print(f"   Модель: {config.model_name}")
    print(f"   RAG индекс: {config.db_path}")
    
    app.state.rag = RAGRetriever(config.db_path, config.index_path)
    app.state.ollama_client = OllamaClient()
    
    setup_api(app.state.rag, app.state.ollama_client)
    
    yield
    # Shutdown
    await app.state.ollama_client.client.aclose()

app = FastAPI(title="RAG LLM Service", version="2.0.0", lifespan=lifespan)

# Rate limiting
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
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Корневой маршрут для веб-интерфейса
@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = "app/static/index.html"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Index.html not found</h1>", status_code=404)

# Include API router
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