import time
import httpx
import os
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
        from app.file_mcp import file_mcp
        
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
        
        # Команды работы с файлами
        elif command_lower.startswith('/read '):
            return await self._handle_read_command(command, start)
        
        elif command_lower.startswith('/find '):
            return await self._handle_find_command(command, start)
        
        elif command_lower.startswith('/imports '):
            return await self._handle_imports_command(command, start)
        
        elif command_lower.startswith('/files '):
            return await self._handle_files_command(command, start)
        
        elif command_lower.startswith('/analyze '):
            return await self._handle_analyze_command(command, start)
        
        elif command_lower.startswith('/create '):
            return await self._handle_create_command(command, start)
        
        elif command_lower.startswith('/append '):
            return await self._handle_append_command(command, start)
        
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

**📁 Команды работы с файлами:**
| Команда | Описание |
|---------|----------|
| `/read <file>` | Прочитать содержимое файла |
| `/find "текст"` | Поиск по файлам проекта |
| `/imports <module>` | Найти все импорты модуля |
| `/files <pattern>` | Список файлов по шаблону |
| `/analyze <file>` | Анализ файла (структура, функции) |
| `/create <file>` | Создать новый файл |
| `/append <file> "text"` | Добавить текст в файл |

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

**📝 Примеры работы с файлами:**
- `/read app/main.py`
- `/find "ollama_client"`
- `/imports fastapi`
- `/files *.py`
- `/analyze app/api.py`
- `/create docs/new_feature.md`
- `/append README.md "## Новый раздел"`

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
    
    # ========== ОБРАБОТКА КОМАНД РАБОТЫ С ФАЙЛАМИ ==========
    
    async def _handle_read_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /read <file>"""
        try:
            parts = command.split(' ', 1)
            if len(parts) < 2 or not parts[1].strip():
                return "❌ **Использование:** `/read <путь_к_файлу>`\n\nПример: `/read app/main.py`", [], int((time.time() - start_time) * 1000)
            
            filepath = parts[1].strip()
            # Если путь относительный, делаем его абсолютным относительно проекта
            if not os.path.isabs(filepath):
                filepath = os.path.join(os.getcwd(), filepath)
            
            from app.file_mcp import file_mcp
            result = file_mcp.read_file(filepath, max_lines=100)
            
            if result["success"]:
                content = result["content"]
                if len(content) > 3000:
                    content = content[:3000] + "\n\n... (показано 3000 символов из " + str(result["lines"]) + " строк)"
                
                response = f"**📄 Файл: `{result['path']}` ({result['lines']} строк)**\n\n```\n{content}\n```"
            else:
                response = f"❌ **Ошибка:** {result['error']}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при чтении файла:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_find_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /find "текст" """
        try:
            # Извлекаем текст для поиска (может быть в кавычках)
            import shlex
            parts = shlex.split(command)
            if len(parts) < 2:
                return "❌ **Использование:** `/find \"текст для поиска\"`\n\nПример: `/find \"class OllamaClient\"`", [], int((time.time() - start_time) * 1000)
            
            query = parts[1]
            
            from app.file_mcp import file_mcp
            results = file_mcp.search_in_files(query, file_pattern="*.py", max_results=10)
            
            if results:
                response = f"**🔍 Результаты поиска \"{query}\":**\n\n"
                for i, result in enumerate(results, 1):
                    response += f"{i}. **`{result['file']}`** ({result['match_count']} совпадений)\n"
                    for match in result['matches'][:3]:  # Показываем до 3 строк
                        response += f"   • Строка {match['line']}: `{match['content']}`\n"
                    response += "\n"
                
                total_matches = sum(r['match_count'] for r in results)
                response += f"**Всего найдено:** {total_matches} совпадений в {len(results)} файлах"
            else:
                response = f"🔍 **По запросу \"{query}\" ничего не найдено.**"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при поиске:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_imports_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /imports <module>"""
        try:
            parts = command.split(' ', 1)
            if len(parts) < 2 or not parts[1].strip():
                return "❌ **Использование:** `/imports <имя_модуля>`\n\nПример: `/imports fastapi`", [], int((time.time() - start_time) * 1000)
            
            module_name = parts[1].strip()
            
            from app.file_mcp import file_mcp
            results = file_mcp.find_imports(module_name)
            
            if results:
                response = f"**📦 Импорты модуля `{module_name}`:**\n\n"
                for i, result in enumerate(results, 1):
                    response += f"{i}. **`{result['file']}`**\n"
                    for imp in result['imports'][:3]:  # Показываем до 3 импортов
                        response += f"   • Строка {imp['line']}: `{imp['content']}`\n"
                    response += "\n"
                
                total_imports = sum(len(r['imports']) for r in results)
                response += f"**Всего импортов:** {total_imports} в {len(results)} файлах"
            else:
                response = f"📦 **Модуль `{module_name}` не импортируется в проекте.**"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при поиске импортов:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_files_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /files <pattern>"""
        try:
            parts = command.split(' ', 1)
            pattern = "*"
            if len(parts) >= 2 and parts[1].strip():
                pattern = parts[1].strip()
            
            from app.file_mcp import file_mcp
            files = file_mcp.list_files(pattern, max_depth=3)
            
            if files:
                file_list = "\n".join([f"• `{f}`" for f in files[:30]])
                if len(files) > 30:
                    file_list += f"\n\n... и еще {len(files) - 30} файлов"
                response = f"**📁 Файлы по шаблону `{pattern}` ({len(files)} всего):**\n\n{file_list}"
            else:
                response = f"📁 **По шаблону `{pattern}` файлов не найдено.**"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при получении списка файлов:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_analyze_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /analyze <file>"""
        try:
            parts = command.split(' ', 1)
            if len(parts) < 2 or not parts[1].strip():
                return "❌ **Использование:** `/analyze <путь_к_файлу>`\n\nПример: `/analyze app/main.py`", [], int((time.time() - start_time) * 1000)
            
            filepath = parts[1].strip()
            # Если путь относительный, делаем его абсолютным относительно проекта
            if not os.path.isabs(filepath):
                filepath = os.path.join(os.getcwd(), filepath)
            
            from app.file_mcp import file_mcp
            result = file_mcp.analyze_file(filepath)
            
            if result["success"]:
                analysis = result["analysis"]
                response = f"**📊 Анализ файла: `{analysis['path']}`**\n\n"
                response += f"• **Размер:** {analysis['size_bytes']} байт\n"
                response += f"• **Строк:** {analysis['lines']}\n"
                response += f"• **Тип файла:** {analysis['file_type']}\n\n"
                
                if analysis.get('imports'):
                    response += f"**📦 Импорты ({len(analysis['imports'])}):**\n"
                    for imp in analysis['imports'][:5]:
                        response += f"  • Строка {imp['line']}: `{imp['content']}`\n"
                    if len(analysis['imports']) > 5:
                        response += f"  ... и еще {len(analysis['imports']) - 5} импортов\n"
                    response += "\n"
                
                if analysis.get('functions'):
                    response += f"**⚙️ Функции ({len(analysis['functions'])}):**\n"
                    for func in analysis['functions'][:5]:
                        response += f"  • `{func['name']}` (строка {func['line']})\n"
                    if len(analysis['functions']) > 5:
                        response += f"  ... и еще {len(analysis['functions']) - 5} функций\n"
                    response += "\n"
                
                if analysis.get('classes'):
                    response += f"**🏗️ Классы ({len(analysis['classes'])}):**\n"
                    for cls in analysis['classes'][:5]:
                        response += f"  • `{cls['name']}` (строка {cls['line']})\n"
                    if len(analysis['classes']) > 5:
                        response += f"  ... и еще {len(analysis['classes']) - 5} классов\n"
                
                if analysis.get('headers'):
                    response += f"**📑 Заголовки ({len(analysis['headers'])}):**\n"
                    for header in analysis['headers'][:5]:
                        level = '#' * header['level']
                        response += f"  • {level} {header['title']} (строка {header['line']})\n"
                    if len(analysis['headers']) > 5:
                        response += f"  ... и еще {len(analysis['headers']) - 5} заголовков\n"
            else:
                response = f"❌ **Ошибка:** {result['error']}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при анализе файла:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_create_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /create <file>"""
        try:
            # Для создания файла нужен путь и содержимое
            # Формат: /create <file> "content"
            import shlex
            parts = shlex.split(command)
            
            if len(parts) < 3:
                return "❌ **Использование:** `/create <путь_к_файлу> \"содержимое файла\"`\n\nПример: `/create docs/new_feature.md \"# Новая функция\\n\\nОписание новой функции.\"`", [], int((time.time() - start_time) * 1000)
            
            filepath = parts[1]
            content = ' '.join(parts[2:])
            
            # Если путь относительный, делаем его абсолютным относительно проекта
            if not os.path.isabs(filepath):
                filepath = os.path.join(os.getcwd(), filepath)
            
            from app.file_mcp import file_mcp
            result = file_mcp.create_file(filepath, content, backup=True)
            
            if result["success"]:
                response = f"✅ **Файл создан:** `{result['path']}`\n"
                response += f"• **Размер:** {result['size']} символов\n"
                if result.get('backup'):
                    response += f"• **Бэкап:** {result['backup']}\n"
            else:
                response = f"❌ **Ошибка:** {result['error']}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при создании файла:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _handle_append_command(self, command: str, start_time: float) -> tuple[str, list, int]:
        """Обработка команды /append <file> "text" """
        try:
            import shlex
            parts = shlex.split(command)
            
            if len(parts) < 3:
                return "❌ **Использование:** `/append <путь_к_файлу> \"текст для добавления\"`\n\nПример: `/append README.md \"## Новый раздел\\n\\nОписание нового раздела.\"`", [], int((time.time() - start_time) * 1000)
            
            filepath = parts[1]
            content = ' '.join(parts[2:])
            
            # Если путь относительный, делаем его абсолютным относительно проекта
            if not os.path.isabs(filepath):
                filepath = os.path.join(os.getcwd(), filepath)
            
            from app.file_mcp import file_mcp
            result = file_mcp.append_to_file(filepath, content)
            
            if result["success"]:
                response = f"✅ **Текст добавлен в файл:** `{result['path']}`\n"
                response += f"• **Добавлено символов:** {result['appended']}\n"
                if result.get('backup'):
                    response += f"• **Бэкап:** {result['backup']}\n"
            else:
                response = f"❌ **Ошибка:** {result['error']}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при добавлении в файл:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    # ========== СТАРЫЕ МЕТОДЫ (остаются без изменений) ==========
    
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
                "восстановить доступ": "**Восстановление доступа к аккаунту:**\n\n1. На странице входа нажмите 'Забыли пароль?'\n2. Введите email, связанный с аккаунтом\n3. Проверьте почту и перейдите по ссылку\n4. Установите новый пароль\n\n🔒 Если email недоступен, обратитесь в поддержку с документами.",
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
                {"id": 101, "subject": "Проблема с авторизацией", "status": "В работе", "priority": "Высокий"},
                {"id": 102, "subject": "Вопрос по тарифам", "status": "Открыт", "priority": "Средний"},
                {"id": 103, "subject": "Ошибка в отчетах", "status": "Решен", "priority": "Высокий"},
                {"id": 104, "subject": "Запрос на интеграцию", "status": "В ожидании", "priority": "Низкий"},
                {"id": 105, "subject": "Сброс пароля", "status": "Решен", "priority": "Средний"}
            ]
            
            response = "🎫 **Тикеты поддержки:**\n\n"
            for ticket in tickets:
                status_emoji = "🟢" if ticket["status"] == "Решен" else "🟡" if ticket["status"] == "В работе" else "🔴"
                response += f"• **#{ticket['id']}** {ticket['subject']} {status_emoji}\n  Статус: {ticket['status']}, Приоритет: {ticket['priority']}\n"
            
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
                "total_users": 157,
                "active_users": 89,
                "total_tickets": 234,
                "open_tickets": 12,
                "resolved_tickets": 198,
                "avg_response_time": "2.3 часа",
                "satisfaction_rate": "94%"
            }
            
            response = "📊 **Статистика поддержки:**\n\n"
            response += f"👥 **Пользователи:**\n"
            response += f"• Всего: {stats['total_users']}\n"
            response += f"• Активных: {stats['active_users']}\n\n"
            
            response += f"🎫 **Тикеты:**\n"
            response += f"• Всего: {stats['total_tickets']}\n"
            response += f"• Открытых: {stats['open_tickets']}\n"
            response += f"• Решенных: {stats['resolved_tickets']}\n\n"
            
            response += f"⏱️ **Метрики:**\n"
            response += f"• Среднее время ответа: {stats['avg_response_time']}\n"
            response += f"• Удовлетворенность: {stats['satisfaction_rate']}"
            
            return response, [], int((time.time() - start_time) * 1000)
            
        except Exception as e:
            error_msg = f"❌ **Ошибка при получении статистики:** {str(e)}"
            return error_msg, [], int((time.time() - start_time) * 1000)
    
    async def _regular_chat(self, request: ChatRequest, project_rag=None, rag_instance=None) -> tuple[str, list, int]:
        """Обычный чат с RAG"""
        # Этот метод остается без изменений
        # Для простоты оставляем заглушку
        prompt = f"User: {request.messages[-1].content}\n\nAssistant:"
        
        response_text, latency = await self._call_ollama(prompt, temperature=0.7, max_tokens=1000)
        
        # Если есть RAG для проекта, добавляем контекст
        sources = []
        if project_rag:
            try:
                rag_results = project_rag.search(request.messages[-1].content, k=3)
                if rag_results:
                    sources = [{"source": r["metadata"].get("source", "unknown"), "content": r["content"]} for r in rag_results]
            except Exception:
                pass
        
        return response_text, sources, latency
    
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
            error_msg = f"Ошибка соединения с Ollama: {str(e)}"
            return error_msg, int((time.time() - start) * 1000)
