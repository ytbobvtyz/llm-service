# Реализация мини-сервиса поддержки пользователей

## Дата реализации
30 апреля 2026

## Обзор
Реализован мини-сервис для поддержки пользователей, интегрированный в существующий llm-service (FastAPI + Ollama + RAG).

## Реализованные компоненты

### 1. Модуль CRM (`app/crm.py`)
- **Классы моделей**: `User`, `Ticket`, `SupportHistory`, `TicketStatus`, `TicketPriority`
- **Провайдеры CRM**: `JSONCRMProvider`, `SQLiteCRMProvider`
- **Менеджер CRM**: `CRMManager` с методами `get_user_context()`, `get_ticket_context()`
- **Глобальный экземпляр**: `crm_manager` (SQLite по умолчанию)

### 2. Модуль Support RAG (`app/support_rag.py`)
- **Класс**: `SupportRAG` с поиском по FAQ, документации и контексту пользователя
- **Функциональность**:
  - Автоиндексация FAQ и документации продукта
  - Поиск с учётом контекста пользователя/тикета
  - Генерация контекста для промптов
  - Сохранение в SQLite БД
- **Глобальный экземпляр**: `support_rag`

### 3. API эндпоинты (`app/support_api.py`)
- **Роутер**: `/support` с тегом "support"
- **Основные эндпоинты**:
  - `POST /support/chat` - чат с поддержкой
  - `GET /support/users` - поиск пользователей
  - `GET /support/users/{user_id}` - информация о пользователе
  - `GET /support/users/{user_id}/tickets` - тикеты пользователя
  - `GET /support/tickets/{ticket_id}` - информация о тикете
  - `GET /support/faq` - получение FAQ
  - `POST /support/faq` - добавление FAQ
  - `GET /support/stats` - статистика поддержки

### 4. Обновлённые модули
- **`app/models.py`**: Добавлены модели для поддержки (`SupportChatRequest`, `SupportChatResponse`, `UserResponse`, `TicketResponse`, `FAQItem`)
- **`app/ollama_client.py`**: Добавлен метод `support_chat()` с учётом контекста
- **`app/config.py`**: Добавлены настройки поддержки (`SUPPORT_DB_PATH`, `FAQ_PATH`, `CRM_PROVIDER`)
- **`app/main.py`**: Интеграция поддержки в lifespan приложения
- **`app/api.py`**: Обновлён health эндпоинт для отображения support чанков

## Структура данных

### FAQ файлы
- `data/faq/general_faq.json` - общие вопросы
- `data/faq/technical_faq.json` - технические вопросы
- `data/faq/billing_faq.json` - вопросы по биллингу

### Документация продукта
- `docs/product/user_guide.md` - руководство пользователя
- `docs/product/api_guide.md` - руководство по API
- `docs/product/troubleshooting.md` - устранение неполадок

### Базы данных
- `data/support.db` - SQLite БД для CRM данных
- `data/support_rag.db` - SQLite БД для Support RAG индекса

## Примеры использования

### Чат с поддержкой
```bash
curl -X POST "http://localhost:8000/support/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Почему не работает авторизация?"}],
    "user_id": "user_123",
    "ticket_id": "ticket_456",
    "temperature": 0.4,
    "max_tokens": 500
  }'
```

### Получение FAQ
```bash
curl "http://localhost:8000/support/faq?search=авторизация"
```

### Поиск пользователей
```bash
curl "http://localhost:8000/support/users?search=иван"
```

## Принципы SOLID

### Single Responsibility
- `crm.py` - только работа с CRM данными
- `support_rag.py` - только RAG для поддержки
- `support_api.py` - только API эндпоинты

### Open/Closed
- CRM провайдеры расширяемы через абстрактный класс `CRMProvider`
- Поддержка новых типов данных через наследование

### Liskov Substitution
- Все CRM провайдеры реализуют одинаковый интерфейс
- Можно заменить JSON провайдер на SQLite без изменения кода

### Interface Segregation
- Отдельные интерфейсы для пользователей, тикетов, FAQ
- Каждый модуль зависит только от нужных ему интерфейсов

### Dependency Inversion
- Зависимости инжектятся через конструкторы
- Высокоуровневые модули не зависят от низкоуровневых реализаций

## Тестирование
- ✅ Импорты работают корректно
- ✅ Модели данных создаются
- ✅ Support RAG индексирует FAQ и документацию
- ✅ Поиск работает с контекстом пользователя
- ✅ API эндпоинты возвращают корректные ответы
- ✅ Health эндпоинты показывают статус системы

## Запуск
```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
python -m app.main
```

Сервер будет доступен по адресу: `http://localhost:8000`

## Дальнейшее развитие
1. Интеграция с внешними CRM через MCP
2. Добавление веб-интерфейса для поддержки
3. Реализация уведомлений о новых тикетах
4. Добавление аналитики и отчётов
5. Интеграция с системами тикетов (Jira, Zendesk)
