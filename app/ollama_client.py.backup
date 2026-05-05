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
        """Обработка MCP команд и команд поддержки"""
        from app.mcp_tools import git_mcp
        
        start = time.time()
        
        # Очищаем команду от лишних пробелов
        command = command.strip()
        command_lower = command.lower()
        
        # Команды поддержки
        if command_lower.startswith('/support'):
            return await self._handle_support_command(command, start)
        
        elif command_lower == '/faq':
            return await self._handle_faq_command(start)
        
        elif command_lower == '/users':
            return await self._handle_users_command(start)
        
        elif command_lower == '/tickets':
            return await self._handle_tickets_command(start)
        
        elif command_lower == '/stats':
            return await self._handle_stats_command(start)
        
        # Старые команды разработчика
        elif command_lower == '/help':
            response = """**🔧 Доступные команды:**

**Команды разработчика:**
| Команда | Описание |
|---------|----------|
| `/help` | Показать эту справку |
| `/branch` | Показать текущую git-ветку |
| `/files` | Список файлов в проекте |
| `/structure` | Древовидная структура проекта |
| `/diff` | Показать незакоммиченные изменения |
| `/readme` | Показать содержимое README |

**👥 Команды поддержки пользователей:**
| Команда | Описание |
|---------|----------|
| `/support [вопрос]` | Чат с поддержкой пользователей |
| `/faq` | Просмотр FAQ (часто задаваемых вопросов) |
| `/users` | Управление пользователями |
| `/tickets` | Управление тикетами поддержки |
| `/stats` | Статистика поддержки |

**💬 Примеры вопросов для поддержки:**
- "Почему не работает авторизация?"
- "Как обновить тарифный план?"
- "Какие системные требования?"
- "Как восстановить доступ к аккаунту?"
- "Как очистить кэш приложения?"

**Примеры вопросов о проекте:**
- "Какая структура проекта?"
- "Где лежит main.py?"
- "Расскажи про API эндпоинты"
- "Как работает RAG система?" """
            return response, [], int((time.time() - start) * 1000)
        
        elif command_lower == '/branch':
            branch_info = git_mcp.get_current_branch()
            response = f"🌿 **Текущая git-ветка:** `{branch_info['branch']}`"
            return response, [], int((time.time() - start) * 1000)
        
        elif command_lower == '/files':
            files = git_mcp.get_file_list()
            if files:
                file_list = "\n".join([f"• `{f}`" for f in files[:30]])
                if len(files) > 30:
                    file_list += f"\n\n... и еще {len(files) - 30} файлов"
                response = f"**📁 Файлы проекта ({len(files)} всего):**\n\n{file_list}"
            else:
                response = "❌ Не удалось получить список файлов"
            return response, [], int((time.time() - start) * 1000)
        
        elif command_lower == '/structure':
            structure = git_mcp.get_project_structure()
            response = f"**📂 Структура проекта:**\n```\n{structure}\n```"
            return response, [], int((time.time() - start) * 1000)
        
        elif command_lower == '/diff':
            diff = git_mcp.get_diff()
            response = f"**📝 Изменения в репозитории:**\n```\n{diff}\n```"
            return response, [], int((time.time() - start) * 1000)
        
        elif command_lower == '/readme':
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
    
    async def _handle_support_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /support"""
        try:
            # Извлекаем вопрос из команды
            parts = command.split(' ', 1)
            if len(parts) < 2 or not parts[1].strip():
                return "🤖 **Использование:** `/support [ваш вопрос]`\n\nПример: `/support Почему не работает авторизация?`", [], int((time.time() - start_time) * 1000)
            
            question = parts[1].strip()
            
            # Имитируем ответ поддержки
            support_responses = {
                "авторизация": "**Проблемы с авторизацией:**\n\n1. Проверьте правильность ввода email и пароля\n2. Очистите кэш браузера и cookies\n3. Попробуйте использовать режим инкогнито\n4. Если проблема сохраняется, сбросьте пароль через 'Забыли пароль?'\n\n📞 Для срочной помощи: support@example.com",
                "тарифный план": "**Обновление тарифного плана:**\n\n1. Войдите в личный кабинет\n2. Перейдите в раздел 'Тарифы и оплата'\n3. Выберите нужный план и нажмите 'Обновить'\n4. Следуйте инструкциям по оплате\n\n💡 Бизнес-план включает приоритетную поддержку и расширенные функции.",
                "системные требования": "**Системные требования:**\n\n• **Браузер:** Chrome 90+, Firefox 88+, Safari 14+\n• **ОС:** Windows 10+, macOS 10.15+, Ubuntu 20.04+\n• **Память:** 4 ГБ RAM минимум\n• **Интернет:** 10 Мбит/с стабильное соединение\n\n📱 Мобильное приложение доступно для iOS 14+ и Android 10+.",
                "восстановить доступ": "**Восстановление доступа к аккаунту:**\n\n1. На странице входа нажмите 'Забыли пароль?'\n2. Введите email, связанный с аккаунтом\n3. Проверьте почту и перейдите по ссылке\n4. Установите новый пароль\n\n🔒 Если email недоступен, обратитесь в поддержку с документами.",
                "очистить кэш": "**Очистка кэша приложения:**\n\n**Веб-версия:**\n1. Нажмите Ctrl+Shift+Delete (Windows/Linux) или Cmd+Shift+Delete (Mac)\n2. Выберите 'Кэш' и 'Cookies'\n3. Нажмите 'Очистить данные'\n\n**Мобильное приложение:**\n1. Настройки → Приложения → Наше приложение\n2. Хранилище → Очистить кэш\n3. Перезапустите приложение"
            }
            
            # Ищем подходящий ответ
            question_lower = question.lower()
            response = "🤖 **Ассистент поддержки:**\n\n"
            
            for keyword, answer in support_responses.items():
                if keyword in question_lower:
                    response += answer
                    break
            else:
                response += f"**Вопрос:** {question}\n\n**Ответ:** Благодарим за обращение! Наша команда поддержки рассмотрит ваш вопрос в ближайшее время.\n\n📧 Для срочных вопросов: support@example.com\n📞 Телефон: +7 (800) 123-45-67\n\n⏰ Часы работы: Пн-Пт 9:00-18:00"
            
            latency = int((time.time() - start_time) * 1000)
            response += f"\n\n⚡ Время обработки: {latency}ms"
            
            return response, [], latency
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при обработке команды поддержки:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_faq_command(self, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /faq"""
        try:
            # Имитируем FAQ
            faq_items = [
                {"question": "Как восстановить пароль?", "answer": "Используйте функцию 'Забыли пароль?' на странице входа."},
                {"question": "Как обновить тарифный план?", "answer": "В личном кабинете в разделе 'Тарифы и оплата'."},
                {"question": "Какие системные требования?", "answer": "Современный браузер и стабильное интернет-соединение."},
                {"question": "Как связаться с поддержкой?", "answer": "Email: support@example.com, телефон: +7 (800) 123-45-67."},
                {"question": "Есть ли мобильное приложение?", "answer": "Да, для iOS и Android в соответствующих магазинах."}
            ]
            
            response = "📋 **Часто задаваемые вопросы (FAQ):**\n\n"
            for i, item in enumerate(faq_items, 1):
                response += f"{i}. **{item['question']}**\n   {item['answer']}\n\n"
            
            response += f"Всего вопросов: {len(faq_items)}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при получении FAQ:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_users_command(self, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /users"""
        try:
            # Имитируем список пользователей
            users = [
                {"id": 1, "name": "Иван Петров", "email": "ivan@example.com", "plan": "Бизнес"},
                {"id": 2, "name": "Мария Сидорова", "email": "maria@example.com", "plan": "Про"},
                {"id": 3, "name": "Алексей Иванов", "email": "alex@example.com", "plan": "Базовый"},
                {"id": 4, "name": "Елена Кузнецова", "email": "elena@example.com", "plan": "Бизнес"},
                {"id": 5, "name": "Дмитрий Смирнов", "email": "dmitry@example.com", "plan": "Про"}
            ]
            
            response = "👥 **Пользователи системы:**\n\n"
            for user in users:
                response += f"• **{user['name']}** ({user['email']}) - {user['plan']}\n"
            
            response += f"\nВсего пользователей: {len(users)}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при получении списка пользователей:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_tickets_command(self, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /tickets"""
        try:
            # Имитируем список тикетов
            tickets = [
                {"id": 101, "title": "Проблема с авторизацией", "status": "В работе", "priority": "Высокий"},
                {"id": 102, "title": "Вопрос по тарифному плану", "status": "Открыт", "priority": "Средний"},
                {"id": 103, "title": "Ошибка в отчетах", "status": "Решен", "priority": "Высокий"},
                {"id": 104, "title": "Запрос на интеграцию", "status": "В ожидании", "priority": "Низкий"},
                {"id": 105, "title": "Восстановление доступа", "status": "В работе", "priority": "Критический"}
            ]
            
            response = "🎫 **Тикеты поддержки:**\n\n"
            for ticket in tickets:
                status_emoji = "🟢" if ticket['status'] == 'Решен' else "🟡" if ticket['status'] == 'В работе' else "🔴"
                priority_emoji = "🔴" if ticket['priority'] == 'Критический' else "🟠" if ticket['priority'] == 'Высокий' else "🟡"
                response += f"• #{ticket['id']}: {ticket['title']} {status_emoji}{priority_emoji}\n"
            
            response += f"\nВсего тикетов: {len(tickets)}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при получении списка тикетов:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_stats_command(self, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /stats"""
        try:
            # Имитируем статистику
            stats = {
                "total_users": 42,
                "active_tickets": 7,
                "resolved_today": 3,
                "avg_response_time": "2 часа 15 минут",
                "faq_items": 15,
                "satisfaction_rate": "94%"
            }
            
            response = "📊 **Статистика поддержки:**\n\n"
            response += f"• 👥 Всего пользователей: **{stats['total_users']}**\n"
            response += f"• 🎫 Активных тикетов: **{stats['active_tickets']}**\n"
            response += f"• ✅ Решено сегодня: **{stats['resolved_today']}**\n"
            response += f"• ⏱️ Среднее время ответа: **{stats['avg_response_time']}**\n"
            response += f"• 📋 FAQ вопросов: **{stats['faq_items']}**\n"
            response += f"• 😊 Удовлетворенность: **{stats['satisfaction_rate']}**\n\n"
            response += "📈 **Тренды:**\n"
            response += "• Обращений стало на 15% меньше за неделю\n"
            response += "• Время решения снизилось на 25%\n"
            response += "• Удовлетворенность выросла на 8%"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при получении статистики:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
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
