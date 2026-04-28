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
project_rag_instance = None
ollama_client_instance = None

def setup(rag, project_rag, ollama_client):
    global rag_instance, project_rag_instance, ollama_client_instance
    rag_instance = rag
    project_rag_instance = project_rag
    ollama_client_instance = ollama_client

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        rag_chunks=len(rag_instance.chunks) if rag_instance else 0,
        project_docs_chunks=len(project_rag_instance.chunks) if project_rag_instance else 0,
        model=config.model_name
    )

@router.post("/api/chat")
@limiter.limit(config.rate_limit)
async def chat(request: Request, chat_req: ChatRequest):
    start_time = time.time()
    
    # Используем chat_with_commands для обработки команд
    response, sources, latency = await ollama_client_instance.chat_with_commands(
        chat_req, 
        project_rag_instance
    )
    
    return ChatResponse(
        response=response,
        sources=sources,
        latency_ms=latency,
        rag_used=len(sources) > 0
    )

@router.get("/api/git/branch")
async def get_git_branch():
    """MCP: Получить текущую git-ветку"""
    from app.mcp_tools import git_mcp
    return git_mcp.get_current_branch()

@router.get("/api/git/files")
async def get_git_files(extension: str = None):
    """MCP: Получить список файлов"""
    from app.mcp_tools import git_mcp
    files = git_mcp.get_file_list(extension)
    return {"files": files, "count": len(files)}

@router.get("/api/git/structure")
async def get_git_structure():
    """MCP: Получить структуру проекта"""
    from app.mcp_tools import git_mcp
    return {"structure": git_mcp.get_project_structure()}

@router.get("/api/git/diff")
async def get_git_diff():
    """MCP: Получить текущие изменения"""
    from app.mcp_tools import git_mcp
    return {"diff": git_mcp.get_diff()}

@router.get("/api/docs/readme")
async def get_readme():
    """Получить README проекта"""
    from app.mcp_tools import git_mcp
    content = git_mcp.get_readme_content()
    if content:
        return {"content": content}
    raise HTTPException(status_code=404, detail="README not found")