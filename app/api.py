import time
import os
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address


from app.config import config
from app.models import ChatRequest, ChatResponse, HealthResponse

API_KEY = os.getenv("API_KEY", "")

def verify_api_key(request: Request):
    if API_KEY:
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
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
        project_rag_instance,
        rag_instance
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

@router.post("/api/review")
@limiter.limit("10/minute")
async def review_code(request: Request, review_req: dict):
    """
    Анализ кода для PR review
    Ожидает: { "diff": "...", "files": ["file1.py", ...], "pr_title": "..." }
    """
    diff = review_req.get("diff", "")
    files = review_req.get("files", [])
    pr_title = review_req.get("pr_title", "")
    
    if not diff:
        raise HTTPException(status_code=400, detail="Diff is required")
    
    prompt = f"""Ты — опытный ревьюер кода. Проанализируй следующие изменения и верни структурированный ответ.

**PR заголовок:** {pr_title}
**Изменённые файлы:** {', '.join(files[:20])}

**DIFF изменений:**
```diff
{diff[:8000]}
Что нужно оценить:

Потенциальные баги и логические ошибки

Архитектурные проблемы (нарушения SOLID, связанность)

Проблемы с производительностью

Стиль кода и читаемость

Отсутствие тестов или документации

Формат ответа (Markdown):

🐛 Потенциальные баги
[список]

🏗️ Архитектурные проблемы
[список]

⚡ Рекомендации по улучшению
[список]

✅ Что хорошо
[список]

Если всё отлично, напиши: "✅ Код выглядит хорошо. Ничего критического не найдено."

Ревью:"""

    try:
        response = await ollama_client_instance.client.post(
        f"{config.ollama_url}/api/generate",
        json={
        "model": config.model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
        "temperature": 0.2, # низкая температура для консистентности
        "num_predict": 2048
        }
        }
        )
        data = response.json()
        review_text = data.get("response", "")

        return {
        "review": review_text,
        "files_reviewed": len(files),
        "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))