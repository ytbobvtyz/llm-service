import time
import httpx
from app.config import config
from app.models import ChatRequest

class OllamaClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(self, request: ChatRequest, context: str) -> tuple[str, int]:
        last_message = request.messages[-1].content if request.messages else ""
        
        prompt = f"""{context}

История диалога:
{self._format_history(request.messages[:-1])}

Пользователь: {last_message}

Ассистент:"""
        
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                        "num_ctx": config.context_length
                    }
                }
            )
            data = response.json()
            latency = int((time.time() - start_time) * 1000)
            return data.get("response", ""), latency
        except Exception as e:
            raise Exception(f"Ollama error: {e}")
    
    def _format_history(self, messages) -> str:
        if not messages:
            return "Нет истории"
        history = []
        for msg in messages[-5:]:
            role = "Пользователь" if msg.role == "user" else "Ассистент"
            history.append(f"{role}: {msg.content}")
        return "\n".join(history)
    
    async def chat_with_commands(self, request: ChatRequest, project_rag=None) -> tuple[str, list, int]:
        """Обработка специальных команд"""
        last_message = request.messages[-1].content if request.messages else ""
        print(f"[DEBUG] chat_with_commands: last_message='{last_message}'")
        print(f"[DEBUG] Starts with '/': {last_message.startswith('/')}")
        
        # Обработка команд (с / или без для некоторых основных команд)
        command_message = last_message.lower().strip()
        # Основные команды, которые распознаются даже без /
        basic_commands = ['help', 'branch', 'files', 'structure', 'diff', 'readme', 'rag']
        
        # Если команда начинается с /
        if last_message.startswith('/'):
            print(f"[DEBUG] Handling command with '/': {last_message}")
            return await self._handle_command(last_message, project_rag)
        # Если без /, но это одна из основных команд
        elif command_message in basic_commands:
            print(f"[DEBUG] Handling basic command without '/': {command_message}")
            return await self._handle_command(f'/{command_message}', project_rag)
        
        # Обычный чат с RAG
        print(f"[DEBUG] Handling regular chat (not a command)")
        return await self._regular_chat(request, project_rag)
    
    async def _handle_command(self, command: str, project_rag=None) -> tuple[str, list, int]:
        """Обработка MCP команд"""
        from app.mcp_tools import git_mcp
        import time
        
        print(f"[DEBUG] _handle_command received command: '{command}'")
        start = time.time()
        
        if command == '/help':
            response = """**Доступные команды:**

/help или просто help - показать эту справку
/branch или просто branch - показать текущую git-ветку
/files или просто files - список файлов в проекте
/structure или просто structure - древовидная структура проекта
/diff или просто diff - показать незакоммиченные изменения
/readme или просто readme - показать содержимое README
/rag или просто rag - поиск в документации проекта

Примеры вопросов:
- "Какая структура проекта?"
- "Где лежит main.py?"
- "Расскажи про API эндпоинты"
- "Как работает RAG система?" """
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/branch':
            branch_info = git_mcp.get_current_branch()
            response = f"🌿 Текущая git-ветка: **{branch_info['branch']}**"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/files':
            files = git_mcp.get_file_list()
            if files:
                file_list = "\n".join([f"- {f}" for f in files[:30]])
                if len(files) > 30:
                    file_list += f"\n... и еще {len(files) - 30} файлов"
                response = f"**Файлы проекта ({len(files)} всего):**\n\n{file_list}"
            else:
                response = "❌ Не удалось получить список файлов"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/structure':
            structure = git_mcp.get_project_structure()
            response = f"**Структура проекта:**\n```\n{structure}\n```"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/diff':
            diff = git_mcp.get_diff()
            response = f"**Изменения в репозитории:**\n```\n{diff}\n```"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/readme':
            readme = git_mcp.get_readme_content()
            if readme:
                # Ограничиваем длину для читаемости
                if len(readme) > 2000:
                    readme = readme[:2000] + "\n... (обрезано)"
                response = f"**README.md:**\n{readme}"
            else:
                response = "❌ README.md не найден"
            return response, [], int((time.time() - start) * 1000)
        
        else:
            response = f"❌ Неизвестная команда: `{command}`\n\nВведите `/help` для списка доступных команд."
            return response, [], int((time.time() - start) * 1000)
    
    async def _regular_chat(self, request: ChatRequest, project_rag=None) -> tuple[str, list, int]:
        """Обычный чат с поиском по документации"""
        from app.main import app
        rag = app.state.rag if hasattr(app.state, 'rag') else None
        
        last_message = request.messages[-1].content if request.messages else ""
        print(f"[DEBUG] _regular_chat: last_message='{last_message}'")
        print(f"[DEBUG] project_rag exists: {project_rag is not None}")
        print(f"[DEBUG] project_rag.chunks count: {len(project_rag.chunks) if project_rag and hasattr(project_rag, 'chunks') else 0}")
        print(f"[DEBUG] old rag exists: {rag is not None}")
        print(f"[DEBUG] old rag.chunks count: {len(rag.chunks) if rag and hasattr(rag, 'chunks') else 0}")
        
        # Поиск в документации проекта
        sources = []
        context = ""
        
        if project_rag and project_rag.chunks:
            print(f"[DEBUG] Searching in project_rag for: '{last_message}'")
            chunks = project_rag.search(last_message, top_k=3)
            print(f"[DEBUG] project_rag search results: {len(chunks)} chunks")
            if chunks:
                sources = list(set(c['filename'] for c in chunks))
                print(f"[DEBUG] project_rag sources: {sources}")
                context = "\n\nИз документации проекта:\n" + "\n".join([
                    f"[{c['filename']}] {c['text'][:400]}..." for c in chunks
                ])
        
        # Если есть старый RAG, тоже используем
        if rag and rag.chunks:
            print(f"[DEBUG] Searching in old rag for: '{last_message}'")
            rag_chunks = rag.search(last_message, top_k=2)
            print(f"[DEBUG] old rag search results: {len(rag_chunks)} chunks")
            if rag_chunks:
                for c in rag_chunks:
                    if c['filename'] not in sources:
                        sources.append(c['filename'])
                print(f"[DEBUG] old rag sources: {[c['filename'] for c in rag_chunks]}")
                context += "\n\nИз документов логистики:\n" + "\n".join([
                    f"[{c['filename']}] {c['text'][:300]}..." for c in rag_chunks[:2]
                ])
        
        # Формируем промпт
        history = []
        for msg in request.messages[:-1]:
            role = "Пользователь" if msg.role == "user" else "Ассистент"
            history.append(f"{role}: {msg.content}")
        history_text = "\n".join(history[-5:]) if history else "Нет истории"
        
        prompt = f"""Ты ассистент разработчика. Отвечай на вопросы о проекте.

{context}

История диалога:
{history_text}

Пользователь: {last_message}

Ассистент:"""
        
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                        "num_ctx": config.context_length
                    }
                }
            )
            data = response.json()
            latency = int((time.time() - start_time) * 1000)
            return data.get("response", ""), sources, latency
        except Exception as e:
            raise Exception(f"Ollama error: {e}")