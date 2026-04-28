#!/usr/bin/env python3
"""
Тестирование обработки команд в OllamaClient
"""

import sys
import os

# Добавляем корень проекта в путь Python перед импортом
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Python path: {sys.path}")

try:
    from app.models import ChatRequest, ChatMessage
    from app.ollama_client import OllamaClient
    print("✅ Все модули успешно импортированы")
    
    # Проверяем импорт из mcp_tools в ollama_client
    from app.mcp_tools import git_mcp
    print(f"✅ mcp_tools.git_mcp: {git_mcp}")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Создаем mock проект RAG для тестирования
class MockProjectRAG:
    def __init__(self):
        self.chunks = []
    
    def search(self, query, top_k=3):
        print(f"MockProjectRAG.search called with query: '{query}', top_k={top_k}")
        return []

async def test_commands():
    client = OllamaClient()
    
    # Создаем mock для тестирования
    mock_project_rag = MockProjectRAG()
    
    tests = [
        (["/help"], "Должен вернуть справку по командам"),
        (["help"], "Должен распознать без /"),
        (["/branch"], "Должен вернуть текущую ветку"),
        (["branch"], "Должен распознать без /"),
        (["/files"], "Должен вернуть список файлов"),
        (["files"], "Должен распознать без /"),
        (["/structure"], "Должен вернуть структуру проекта"),
        (["structure"], "Должен распознать без /"),
        (["Как работает проект?"], "Должен искать в project_rag"),
        (["Расскажи о структуре проекта"], "Должен искать в project_rag"),
    ]
    
    print("🧪 Тестирование обработки команд")
    print("=" * 60)
    
    for messages_content, description in tests:
        print(f"\nТест: {description}")
        print(f"Сообщение: {messages_content[0]}")
        
        messages = [ChatMessage(role="user", content=msg) for msg in messages_content]
        request = ChatRequest(
            messages=messages,
            temperature=0.4,
            max_tokens=768,
            use_rag=True
        )
        
        try:
            # Важно: проект_раг передается как параметр
            response, sources, latency = await client.chat_with_commands(
                request, mock_project_rag
            )
            
            # Для команд, мы ожидаем быстрый ответ (без запроса к Ollama)
            # Команды не должны иметь источников (sources должен быть пустым списком)
            print(f"  Ответ получен (latency: {latency}ms)")
            print(f"  Источники: {sources}")
            if response:
                print(f"  Первые 100 символов ответа: {response[:100]}...")
            
            # Если это команда, источник должен быть пустым
            if messages_content[0].lower() in ['/help', 'help', '/branch', 'branch', '/files', 'files', '/structure', 'structure']:
                if len(sources) == 0:
                    print("  ✅ Успешно: команда обработана правильно (нет источников)")
                else:
                    print(f"  ⚠️ Внимание: команда вернула источники: {sources}")
                    
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            
            # Выводим детали об ошибке импорта
            if "ImportError" in str(e) or "ModuleNotFoundError" in str(e):
                import traceback
                exc_info = sys.exc_info()
                tb_lines = traceback.format_exception(*exc_info)
                tb_text = ''.join(tb_lines)
                print(f"  🔍 Детали ошибки импорта:")
                for line in tb_lines[-3:]:
                    print(f"      {line.strip()}")
        
        print(f"{'_' * 60}")

if __name__ == "__main__":
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_commands())
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()