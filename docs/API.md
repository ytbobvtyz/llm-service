# API Документация

## Основные эндпоинты

### POST /api/chat
Тело запроса:
```json
{
  "messages": [{"role": "user", "content": "вопрос о проекте"}],
  "temperature": 0.4,
  "use_rag": true,
  "max_tokens": 1000
}
```

Ответ:
```json
{
  "response": "текст ответа",
  "sources": ["источник1.md", "README.md"],
  "latency_ms": 123,
  "rag_used": true
}
```

### GET /api/git/branch
Возвращает текущую git-ветку

Ответ:
```json
{
  "branch": "main",
  "status": "success"
}
```

### GET /api/git/files
Возвращает список файлов в проекте

Параметры:
- `extension` (опционально) - фильтр по расширению файлов

Пример: `GET /api/git/files?extension=.py`

Ответ:
```json
{
  "files": ["app/main.py", "app/api.py"],
  "count": 2
}
```

### GET /api/git/structure
Возвращает древовидную структуру проекта

Ответ:
```json
{
  "structure": "app/\n├── main.py\n└── api.py"
}
```

### GET /api/git/diff
Возвращает незакоммиченные изменения

Ответ:
```json
{
  "diff": "main.py | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)"
}
```

### GET /api/docs/readme
Возвращает содержимое README

Ответ:
```json
{
  "content": "# LLM Service - Ассистент разработчика..."
}
```

### GET /health
Проверка статуса приложения

Ответ:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T12:00:00"
}
```

### GET /api/rag/search
Поиск по документации проекта

Параметры:
- `query` - поисковый запрос
- `top_k` (опционально, по умолчанию 3) - количество результатов

Пример: `GET /api/rag/search?query=API эндпоинты&top_k=5`

Ответ:
```json
{
  "results": [
    {
      "text": "### GET /api/git/branch\nВозвращает текущую git-ветку...",
      "filename": "API.md",
      "score": 5
    }
  ]
}
```

## Команды (синхронные)

### `/help`
Показывает список доступных команд и примеры вопросов

### `/branch`
Показывает текущую git-ветку

### `/files`
Список файлов в проекте

### `/structure`
Древовидная структура проекта

### `/diff`
Показывает незакоммиченные изменения

### `/readme`
Показывает содержимое README