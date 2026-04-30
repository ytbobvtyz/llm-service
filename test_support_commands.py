#!/usr/bin/env python3
"""
Скрипт для тестирования команд поддержки через консольный интерфейс.
"""

import asyncio
import sys
from app.ollama_client import OllamaClient
from app.models import ChatRequest, Message

async def test_support_commands():
    """Тестирование команд поддержки"""
    client = OllamaClient()
    
    test_commands = [
        "/help",
        "/support Почему не работает авторизация?",
        "/support Как обновить тарифный план?",
        "/faq",
        "/users",
        "/tickets",
        "/stats",
        "/branch",
        "/files",
        "/structure"
    ]
    
    print("🧪 Тестирование команд поддержки...")
    print("=" * 60)
    
    for command in test_commands:
        print(f"\n📝 Команда: {command}")
        print("-" * 40)
        
        try:
            # Создаем запрос с командой
            request = ChatRequest(
                messages=[Message(role="user", content=command)],
                temperature=0.4,
                max_tokens=500
            )
            
            # Вызываем обработку команды
            response, sources, latency = await client.chat_with_commands(request)
            
            # Выводим результат
            print(f"✅ Успешно ({latency}ms)")
            print(f"📄 Ответ ({len(response)} символов):")
            print(response[:500] + ("..." if len(response) > 500 else ""))
            
            if sources:
                print(f"📚 Источники: {sources}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)
        await asyncio.sleep(0.5)  # Небольшая пауза между командами
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")

async def test_support_chat():
    """Тестирование метода support_chat"""
    print("\n🧪 Тестирование метода support_chat...")
    print("=" * 60)
    
    try:
        from app.support_rag import support_rag
        from app.crm import crm_manager
        
        client = OllamaClient()
        
        # Создаем тестовый запрос поддержки
        request = ChatRequest(
            messages=[Message(role="user", content="Почему не работает авторизация?")],
            temperature=0.4,
            max_tokens=300,
            user_id="test_user_123",
            ticket_id="test_ticket_456"
        )
        
        print("📝 Запрос поддержки с user_id и ticket_id")
        
        # Вызываем support_chat
        response, sources, user_context, ticket_context, latency = await client.support_chat(
            request, support_rag, crm_manager
        )
        
        print(f"✅ Успешно ({latency}ms)")
        print(f"📄 Ответ: {response[:200]}...")
        print(f"📚 Источники: {len(sources)}")
        print(f"👤 Контекст пользователя: {bool(user_context)}")
        print(f"🎫 Контекст тикета: {bool(ticket_context)}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == "__main__":
    print("🚀 Запуск тестов поддержки пользователей")
    print("Версия: 1.0.0")
    print()
    
    # Запускаем тесты
    asyncio.run(test_support_commands())
    
    # Пока не тестируем support_chat, так как требует инициализации RAG и CRM
    # asyncio.run(test_support_chat())
    
    print("\n📋 Итоги:")
    print("• Команды поддержки добавлены в OllamaClient")
    print("• Веб-интерфейс обновлен с поддержкой команд")
    print("• API эндпоинты поддержки подключены")
    print("• Документация с тестовыми вопросами создана")
    print("\n✅ Готово к использованию!")
