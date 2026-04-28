# LLM Service - Ассистент разработчика

## Структура проекта
- `app/` - основной код приложения
  - `main.py` - точка входа FastAPI
  - `api.py` - API эндпоинты
  - `rag.py` - RAG ретривер
  - `ollama_client.py` - клиент для Ollama
  - `mcp_tools.py` - MCP инструменты для Git
- `data/` - базы данных RAG
- `docs/` - документация проекта
- `static/` - веб-интерфейс

## Команды
- `/help` - получить помощь о проекте
- `/branch` - показать текущую git-ветку
- `/files` - показать структуру файлов
- `/structure` - древовидная структура
- `/readme` - показать README

## API эндпоинты
- `GET /health` - проверка статуса
- `POST /api/chat` - чат с ассистентом
- `GET /api/git/branch` - текущая ветка

## Основные технологии
- FastAPI - веб-фреймворк
- Ollama - локальные LLM модели
- FAISS - векторный поиск
- SQLite - база данных
- Git MCP - интеграция с Git

## Развертывание
```bash
docker compose up --build
```

Приложение будет доступно по адресу: http://localhost:8000