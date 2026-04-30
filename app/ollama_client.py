import time
import httpx
from typing import Dict, List, Optional, Any
from app.config import config
from app.models import ChatRequest


class OllamaClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat_with_commands(self, request: ChatRequest, project_rag=None, rag_instance=None) -> tuple[str, list, int]:
        """Обработка специальных команд и обычного чата"""
        last_message = request.messages[-1].content if request.messages else ""
        
        # Обработка команд (начинаются с /)
        if last_message.startswith('/'):
            return await self._handle_command(last_message, project_rag)
        
        # Обычный чат с RAG — передаём оба источника
        return await self._regular_chat(request, project_rag, rag_instance)
    
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
    
    async def _regular_chat(self, request: ChatRequest, project_rag=None, rag_instance=None) -> tuple[str, list, int]:
        """Обычный чат с поиском по документации проекта и логистике"""
        last_message = request.messages[-1].content if request.messages else ""
        
        sources = []
        context = ""
        
        # Поиск в документации проекта
        if project_rag and project_rag.chunks:
            chunks = project_rag.search(last_message, top_k=3)
            if chunks:
                context += "\n📚 Информация из документации проекта:\n"
                for i, chunk in enumerate(chunks, 1):
                    context += f"{i}. {chunk.get('text', '')[:300]}...\n"
                sources.extend([f"docs:{chunk.get('filename', '')}" for chunk in chunks])
        
        # Поиск в логистике (старый RAG)
        if rag_instance and rag_instance.chunks and request.use_rag:
            chunks = rag_instance.search(last_message, top_k=2)
            if chunks:
                context += "\n📦 Информация из базы знаний логистики:\n"
                for i, chunk in enumerate(chunks, 1):
                    context += f"{i}. {chunk.get('text', '')[:300]}...\n"
                sources.extend([f"logistics:{chunk.get('filename', '')}" for chunk in chunks])
        
        # Формируем промпт
        prompt = self._build_prompt(request.messages, context)
        
        # Отправляем запрос к Ollama
        response_text, latency = await self._call_ollama(prompt, request.temperature, request.max_tokens)
        
        return response_text, sources, latency
    
    async def support_chat(self, request, support_rag, crm_manager) -> tuple[str, list, Dict, Dict, int]:
        """Чат с поддержкой с учётом контекста пользователя и тикета"""
        start_time = time.time()
        
        last_message = request.messages[-1].content if request.messages else ""
        user_id = request.user_id
        ticket_id = request.ticket_id
        
        # Получаем контекст из Support RAG
        context = support_rag.get_context_for_prompt(last_message, user_id, ticket_id)
        
        # Получаем контекст пользователя и тикета для ответа
        user_context = {}
        ticket_context = {}
        
        if user_id:
            user_context = crm_manager.get_user_context(user_id)
        
        if ticket_id:
            ticket_context = crm_manager.get_ticket_context(ticket_id)
        
        # Формируем промпт для поддержки
        prompt = self._build_support_prompt(request.messages, context, user_context, ticket_context)
        
        # Отправляем запрос к Ollama
        response_text, latency = await self._call_ollama(
            prompt, 
            request.temperature, 
            request.max_tokens
        )
        
        # Получаем источники из поиска
        search_results = support_rag.search(last_message, user_id, ticket_id, top_k=3)
        sources = [
            {
                'text': result['text'][:200],
                'source_type': result['source_type'],
                'source_name': result['source_name'],
                'score': result['score']
            }
            for result in search_results
        ]
        
        # Добавляем запись в историю поддержки если есть user_id
        if user_id:
            from app.crm import SupportHistory
            import uuid
            from datetime import datetime
            
            history = SupportHistory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                ticket_id=ticket_id,
                question=last_message,
                answer=response_text[:1000],  # Ограничиваем длину
                timestamp=datetime.now().isoformat()
            )
            
            crm_manager.provider.add_support_history(history)
        
        return response_text, sources, user_context, ticket_context, latency
    
    def _build_prompt(self, messages, context: str = "") -> str:
        """Строит промпт для обычного чата"""
        conversation = ""
        for msg in messages:
            conversation += f"{msg.role}: {msg.content}\n"
        
        if context:
            prompt = f"""Ты — полезный AI ассистент. Отвечай на вопросы пользователя, используя предоставленный контекст.

{context}

Текущий диалог:
{conversation}

Ассистент:"""
        else:
            prompt = f"""Ты — полезный AI ассистент. Отвечай на вопросы пользователя.

Текущий диалог:
{conversation}

Ассистент:"""
        
        return prompt
    
    def _build_support_prompt(self, messages, context: str = "", 
                             user_context: Dict = None, ticket_context: Dict = None) -> str:
        """Строит промпт для поддержки пользователей"""
        conversation = ""
        for msg in messages:
            conversation += f"{msg.role}: {msg.content}\n"
        
        # Формируем контекстную информацию
        context_info = ""
        if context:
            context_info += f"\n{context}\n"
        
        if user_context:
            user_info = user_context.get('user', {})
            context_info += f"\n👤 Информация о пользователе:\n"
            context_info += f"- Имя: {user_info.get('name', 'Неизвестно')}\n"
            context_info += f"- Email: {user_info.get('email', 'Неизвестно')}\n"
            context_info += f"- Тарифный план: {user_info.get('subscription_plan', 'Неизвестно')}\n"
            
            recent_tickets = user_context.get('recent_tickets', [])
            if recent_tickets:
                context_info += f"- Недавние обращения: {len(recent_tickets)}\n"
                for ticket in recent_tickets[:2]:
                    context_info += f"  • {ticket.get('title', 'Без названия')} ({ticket.get('status', 'Неизвестно')})\n"
        
        if ticket_context:
            ticket_info = ticket_context.get('ticket', {})
            context_info += f"\n🎫 Информация о тикете:\n"
            context_info += f"- Заголовок: {ticket_info.get('title', 'Без названия')}\n"
            context_info += f"- Описание: {ticket_info.get('description', 'Нет описания')[:200]}...\n"
            context_info += f"- Статус: {ticket_info.get('status', 'Неизвестно')}\n"
            context_info += f"- Приоритет: {ticket_info.get('priority', 'Неизвестно')}\n"
        
        prompt = f"""Ты — AI ассистент технической поддержки. Твоя задача — помогать пользователям решать проблемы с продуктом.

Инструкции:
1. Используй предоставленный контекст для точных ответов
2. Учитывай информацию о пользователе и его истории обращений
3. Будь вежливым, профессиональным и полезным
4. Если не знаешь ответа, предложи обратиться в поддержку по email или телефону
5. Для пользователей на бизнес-тарифе предлагай более быстрые решения
6. Форматируй ответы с использованием markdown для читаемости

{context_info}

Текущий диалог с пользователем:
{conversation}

Ассистент поддержки:"""
        
        return prompt
    
    async def _call_ollama(self, prompt: str, temperature: float, max_tokens: int) -> tuple[str, int]:
        """Вызов Ollama API"""
        start = time.time()
        
        try:
            response = await self.client.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                latency = int((time.time() - start) * 1000)
                return response_text, latency
            else:
                error_msg = f"Ошибка Ollama: {response.status_code}"
                return error_msg, int((time.time() - start) * 1000)
        
        except Exception as e:
            error_msg = f"Ошибка подключения к Ollama: {str(e)}"
            return error_msg, int((time.time() - start) * 1000)
