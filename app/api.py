import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import config
from app.models import ChatRequest, ChatResponse, HealthResponse
from app.mcp_tools import git_mcp

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
    from app.main import app
    
    # Используем новую функцию с поддержкой команд и документации проекта
    project_rag = app.state.project_rag if hasattr(app.state, 'project_rag') else None
    
    response, sources, latency = await ollama_client_instance.chat_with_commands(
        chat_req, project_rag
    )
    
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

# Новые MCP эндпоинты
@router.get("/api/git/branch")
async def get_git_branch():
    """MCP: Получить текущую git-ветку"""
    return git_mcp.get_current_branch()

@router.get("/api/git/files")
async def get_git_files(extension: Optional[str] = None):
    """MCP: Получить список файлов"""
    files = git_mcp.get_file_list(extension)
    return {"files": files, "count": len(files)}

@router.get("/api/git/structure")
async def get_git_structure():
    """MCP: Получить структуру проекта"""
    return {"structure": git_mcp.get_project_structure()}

@router.get("/api/git/diff")
async def get_git_diff():
    """MCP: Получить текущие изменения"""
    return {"diff": git_mcp.get_diff()}

@router.get("/api/docs/readme")
async def get_readme():
    """Получить README проекта"""
    content = git_mcp.get_readme_content()
    if content:
        return {"content": content}
    raise HTTPException(status_code=404, detail="README not found")