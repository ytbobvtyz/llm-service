# Инструкция по использованию ассистента поддержки пользователей

## Быстрый старт

### 1. Настройка окружения
```bash
# Клонировать репозиторий (если нужно)
git clone <repository>
cd llm-service

# Установить зависимости
pip install -r requirements.txt

# Создать .env файл (опционально)
cp .env.example .env
# Отредактировать .env при необходимости
```

### 2. Запуск сервера
```bash
# Запустить основной сервер
python -m app.main

# Или с uvicorn напрямую
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Проверка работоспособности
```bash
# Проверить health эндпоинт
curl http://localhost:8000/health

# Проверить health поддержки
curl http://localhost:8000/support/health

# Получить список FAQ
curl http://localhost:8000/support/faq
```

## Основные сценарии использования

### Сценарий 1: Ответ на вопрос пользователя
```bash
curl -X POST "http://localhost:8000/support/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Почему не работает авторизация?"}
    ],
    "temperature": 0.4,
    "max_tokens": 500
  }'
```

**Ожидаемый ответ:**
```json
{
  "response": "Проверьте: 1) Правильность логина/пароля 2) Подключение к интернету...",
  "sources": [
    {
      "text": "Вопрос: Почему не работает авторизация?\\nОтвет: Проверьте...",
      "source_type": "faq",
      "source_name": "general_faq.json",
      "score": 5
    }
  ],
  "latency_ms": 1200,
  "user_context": null,
  "ticket_context": null
}
```

### Сценарий 2: Ответ с учётом контекста пользователя
```bash
curl -X POST "http://localhost:8000/support/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Как обновить тарифный план?"}
    ],
    "user_id": "user_123",
    "temperature": 0.4,
    "max_tokens": 500
  }'
```

**Особенности:**
- Ответ учитывает тарифный план пользователя
- Предлагаются решения в соответствии с историей обращений
- Для бизнес-пользователей предлагаются приоритетные решения

### Сценарий 3: Работа с существующим тикетом
```bash
curl -X POST "http://localhost:8000/support/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Каков статус моего запроса?"}
    ],
    "user_id": "user_123",
    "ticket_id": "ticket_456",
    "temperature": 0.4,
    "max_tokens": 500
  }'
```

**Особенности:**
- Ответ включает информацию о тикете
- Учитывается история переписки по тикету
- Предлагаются следующие шаги в соответствии со статусом тикета

## Управление данными

### Добавление нового FAQ вопроса
```bash
curl -X POST "http://localhost:8000/support/faq" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Как экспортировать данные?",
    "answer": "Зайдите в Настройки → Экспорт данных → Выберите формат (CSV, JSON, PDF) → Нажмите Экспорт.",
    "tags": ["экспорт", "данные", "настройки"]
  }'
```

### Поиск пользователей
```bash
# Поиск по имени или email
curl "http://localhost:8000/support/users?search=иван&limit=10"

# Получить всех пользователей (с пагинацией)
curl "http://localhost:8000/support/users?limit=20"
```

### Получение информации о пользователе
```bash
curl "http://localhost:8000/support/users/user_123"
```

### Получение тикетов пользователя
```bash
curl "http://localhost:8000/support/users/user_123/tickets?limit=5"
```

## Интеграция с внешними системами

### Через MCP (Model Context Protocol)
Система поддерживает интеграцию с внешними CRM через MCP. Пример конфигурации:

```python
# В config.py
CRM_PROVIDER = "mcp"
MCP_CRM_URL = "http://external-crm:8080"

# Или через переменные окружения
export CRM_PROVIDER=mcp
export MCP_CRM_URL=http://external-crm:8080
```

### Собственный CRM провайдер
Для создания собственного провайдера унаследуйте `CRMProvider`:

```python
from app.crm import CRMProvider

class CustomCRMProvider(CRMProvider):
    def get_user(self, user_id: str):
        # Реализация получения пользователя
        pass
    
    def get_user_tickets(self, user_id: str, limit: int = 10):
        # Реализация получения тикетов
        pass
    
    # ... остальные методы
```

## Настройка конфигурации

### Основные переменные окружения
```bash
# Ollama
export OLLAMA_URL=http://ollama:11434
export MODEL_NAME=llama3.2:3b

# Support
export SUPPORT_DB_PATH=data/support.db
export SUPPORT_RAG_DB_PATH=data/support_rag.db
export FAQ_PATH=data/faq
export PRODUCT_DOCS_PATH=docs/product
export CRM_PROVIDER=sqlite  # или json

# API
export RATE_LIMIT=20/minute
export MAX_TOKENS=768
export TEMPERATURE=0.4
```

### Конфигурация через .env файл
```env
# .env файл
OLLAMA_URL=http://localhost:11434
MODEL_NAME=llama3.2:3b
CRM_PROVIDER=sqlite
FAQ_PATH=data/faq
RATE_LIMIT=30/minute
```

## Мониторинг и отладка

### Health checks
```bash
# Общий health check
curl http://localhost:8000/health

# Health check поддержки
curl http://localhost:8000/support/health
```

**Ответ health check:**
```json
{
  "status": "ok",
  "rag_chunks": 150,
  "project_docs_chunks": 45,
  "support_chunks": 29,
  "model": "llama3.2:3b"
}
```

### Статистика
```bash
curl http://localhost:8000/support/stats
```

**Ответ статистики:**
```json
{
  "total_users": 150,
  "active_tickets": 12,
  "resolved_today": 5,
  "avg_response_time": "2h 30m",
  "faq_items": 29
}
```

### Логирование
Логи выводятся в консоль при запуске сервера:
```
🚀 Запуск RAG LLM Service с поддержкой пользователей
   Модель: llama3.2:3b
   RAG индекс: data/metadata.db
   Support RAG: data/support_rag.db
   CRM провайдер: sqlite
============================================================
✅ Загружено 29 чанков поддержки из data/support_rag.db
```

## Примеры интеграции

### Python клиент
```python
import requests

class SupportClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def ask_support(self, question, user_id=None, ticket_id=None):
        response = requests.post(
            f"{self.base_url}/support/chat",
            json={
                "messages": [{"role": "user", "content": question}],
                "user_id": user_id,
                "ticket_id": ticket_id
            }
        )
        return response.json()

# Использование
client = SupportClient()
answer = client.ask_support("Почему не работает авторизация?", user_id="user_123")
print(answer["response"])
```

### JavaScript клиент
```javascript
async function askSupport(question, userId = null, ticketId = null) {
  const response = await fetch('http://localhost:8000/support/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: question }],
      user_id: userId,
      ticket_id: ticketId
    }),
  });
  return await response.json();
}

// Использование
const answer = await askSupport('Как обновить тариф?', 'user_123');
console.log(answer.response);
```

## Устранение неполадок

### Проблема: Сервер не запускается
**Решение:**
1. Проверьте установлены ли зависимости: `pip list | grep fastapi`
2. Проверьте порт 8000: `netstat -tulpn | grep :8000`
3. Проверьте логи ошибок в консоли

### Проблема: Ollama недоступен
**Решение:**
1. Проверьте запущен ли Ollama: `docker ps | grep ollama`
2. Проверьте URL в конфигурации
3. Проверьте доступность: `curl http://ollama:11434/api/tags`

### Проблема: Нет ответа от поддержки
**Решение:**
1. Проверьте health эндпоинты
2. Проверьте наличие FAQ файлов в `data/faq/`
3. Проверьте логи на наличие ошибок индексации

### Проблема: Медленные ответы
**Решение:**
1. Увеличьте `MAX_TOKENS` в конфигурации
2. Проверьте производительность Ollama
3. Оптимизируйте промпты в `ollama_client.py`
