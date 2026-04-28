import time
import httpx
from app.config import config
from app.models import ChatRequest


class OllamaClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat_with_commands(self, request: ChatRequest, project_rag=None) -> tuple[str, list, int]:
        """Обработка специальных команд и обычного чата"""
        last_message = request.messages[-1].content if request.messages else ""
        
        # Обработка команд (начинаются с /)
        if last_message.startswith('/'):
            return await self._handle_command(last_message, project_rag)
        
        # Обычный чат с RAG
        return await self._regular_chat(request, project_rag)
    
    async def _handle_command(self, command: str, project_rag=None) -> tuple[str, list, int]:
        """Обработка MCP команд"""
        from app.mcp_tools import git_mcp
        
        start = time.time()
        
        # Очищаем команду от лишних пробелов
        command = command.strip().lower()
        
        if command == '/help':
            response = """**🔧 Доступные команды:**

| Команда | Описание |
|---------|----------|
| `/help` | Показать эту справку |
| `/branch` | Показать текущую git-ветку |
| `/files` | Список файлов в проекте |
| `/structure` | Древовидная структура проекта |
| `/diff` | Показать незакоммиченные изменения |
| `/readme` | Показать содержимое README |

**Примеры вопросов о проекте:**
- "Какая структура проекта?"
- "Где лежит main.py?"
- "Расскажи про API эндпоинты"
- "Как работает RAG система?" """
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/branch':
            branch_info = git_mcp.get_current_branch()
            response = f"🌿 **Текущая git-ветка:** `{branch_info['branch']}`"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/files':
            files = git_mcp.get_file_list()
            if files:
                file_list = "\n".join([f"• `{f}`" for f in files[:30]])
                if len(files) > 30:
                    file_list += f"\n\n... и еще {len(files) - 30} файлов"
                response = f"**📁 Файлы проекта ({len(files)} всего):**\n\n{file_list}"
            else:
                response = "❌ Не удалось получить список файлов"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/structure':
            structure = git_mcp.get_project_structure()
            response = f"**📂 Структура проекта:**\n```\n{structure}\n```"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/diff':
            diff = git_mcp.get_diff()
            response = f"**📝 Изменения в репозитории:**\n```\n{diff}\n```"
            return response, [], int((time.time() - start) * 1000)
        
        elif command == '/readme':
            readme = git_mcp.get_readme_content()
            if readme:
                if len(readme) > 2000:
                    readme = readme[:2000] + "\n\n... (обрезано)"
                response = f"**📖 README.md:**\n\n{readme}"
            else:
                response = "❌ README.md не найден"
            return response, [], int((time.time() - start) * 1000)
        
        else:
            response = f"❌ **Неизвестная команда:** `{command}`\n\nВведите `/help` для списка доступных команд."
            return response, [], int((time.time() - start) * 1000)
    
    async def _regular_chat(self, request: ChatRequest, project_rag=None) -> tuple[str, list, int]:
        """Обычный чат с поиском по документации проекта"""
        last_message = request.messages[-1].content if request.messages else ""
        
        # Поиск в документации проекта
        sources = []
        context = ""
        
        if project_rag and project_rag.chunks:
            chunks = project_rag.search(last_message, top_k=3)
            if chunks:
                sources = list(set(c['filename'] for c in chunks))
                context = "\n\n**📚 Из документации проекта:**\n" + "\n".join([
                    f"[{c['filename']}]\n{c['text'][:500]}..." for c in chunks
                ])
        
        # Формируем промпт
        history = []
        for msg in request.messages[:-1]:
            role = "Пользователь" if msg.role == "user" else "Ассистент"
            history.append(f"{role}: {msg.content}")
        history_text = "\n".join(history[-5:]) if history else "Нет истории"
        
        prompt = f"""Ты — ассистент разработчика. Отвечай на вопросы ТОЛЬКО на основе предоставленной документации проекта.

{context}

**История диалога:**
{history_text}

**Вопрос пользователя:** {last_message}

**Инструкции:**
1. Используй только информацию из документации проекта
2. Если информации нет — честно скажи "В документации не найдено"
3. Указывай источник (имя файла)
4. Отвечай на русском языке, кратко и по делу

**Ответ:**"""
        
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": config.temperature,
                        "num_predict": config.max_tokens,
                        "num_ctx": config.context_length
                    }
                }
            )
            data = response.json()
            latency = int((time.time() - start_time) * 1000)
            return data.get("response", ""), sources, latency
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