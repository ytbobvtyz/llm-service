# LLM Service - Ассистент разработчика

## Структура проекта
- `app/` - основной код приложения
  - `main.py` - точка входа FastAPI
  - `api.py` - API эндпоинты
  - `rag.py` - RAG ретривер
  - `ollama_client.py` - клиент для Ollama
  - `mcp_tools.py` - MCP инструменты для Git
  - `models.py` - модели данных
  - `config.py` - конфигурация
- `data/` - базы данных RAG
- `docs/` - документация проекта
- `static/` - веб-интерфейс

## Команды
- `/help` - получить помощь о проекте
- `/branch` - показать текущую git-ветку
- `/files` - показать структуру файлов
- `/structure` - показать древовидную структуру проекта
- `/diff` - показать незакоммиченные изменения
- `/readme` - показать содержимое README
- `/rag` - поиск в документации проекта

## API эндпоинты
- `GET /health` - проверка статуса
- `POST /api/chat` - чат с ассистентом
- `GET /api/rag/search` - поиск в документации
- `GET /api/git/branch` - текущая ветка
- `GET /api/git/files` - список файлов
- `GET /api/git/structure` - структура проекта
- `GET /api/git/diff` - изменения в репозитории
- `GET /api/docs/readme` - содержимое README

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