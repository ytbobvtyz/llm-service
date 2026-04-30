# LLM Service с поддержкой пользователей - Docker запуск

## Быстрый старт

### 1. Запуск через скрипт (рекомендуется)
```bash
# Сделайте скрипт исполняемым (если нужно)
chmod +x start.sh

# Запустите систему
./start.sh
```

### 2. Ручной запуск через Docker Compose
```bash
# Запуск в фоновом режиме
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

## Что запускается

### Сервисы
1. **rag-service** (порт 8000) - основной сервис с RAG и поддержкой пользователей
2. **ollama** (порт 11434) - LLM модель для генерации ответов

### Данные
- `data/` - базы данных и FAQ файлы
- `docs/` - документация продукта
- `app/static/` - статические файлы веб-интерфейса

## Проверка работоспособности

### Health checks
```bash
# Проверить основной сервис
curl http://localhost:8000/health

# Проверить поддержку
curl http://localhost:8000/support/health

# Проверить Ollama
curl http://localhost:11434/api/tags
```

### Примеры запросов

#### Чат с поддержкой
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

#### Получение FAQ
```bash
curl "http://localhost:8000/support/faq"
```

#### Статистика
```bash
curl "http://localhost:8000/support/stats"
```

## Управление

### Команды Docker Compose
```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Пересборка
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f rag-service
docker-compose logs -f ollama

# Вход в контейнер
docker-compose exec rag-service bash
```

### Полезные команды внутри контейнера
```bash
# Проверить данные
docker-compose exec rag-service ls -la /app/data/

# Проверить логи
docker-compose exec rag-service tail -f /var/log/...

# Проверить процессы
docker-compose exec rag-service ps aux
```

## Настройка

### Переменные окружения
Создайте `.env` файл:
```env
# Ollama
OLLAMA_URL=http://ollama:11434
MODEL_NAME=llama3.2:3b

# Support
CRM_PROVIDER=sqlite
RATE_LIMIT=30/minute
MAX_TOKENS=1024
TEMPERATURE=0.4

# Безопасность
API_KEY=your_secret_key_here
```

### Изменение портов
Если порты заняты, измените `docker-compose.yml`:
```yaml
services:
  rag-service:
    ports:
      - "8080:8000"  # внешний:внутренний
  
  ollama:
    ports:
      - "11435:11434"  # внешний:внутренний
```

## Устранение неполадок

### Проблема: Порт уже используется
```bash
# Найдите процесс
sudo lsof -i :8000
sudo lsof -i :11434

# Остановите или измените порт
```

### Проблема: Контейнеры не запускаются
```bash
# Проверьте логи
docker-compose logs

# Проверьте образы
docker images

# Пересоберите
docker-compose build --no-cache
```

### Проблема: Ollama не загружает модель
```bash
# Проверьте доступность Ollama
curl http://localhost:11434/api/tags

# Загрузите модель вручную
docker-compose exec ollama ollama pull llama3.2:3b
```

### Проблема: Нет данных поддержки
```bash
# Проверьте volumes
docker-compose exec rag-service ls -la /app/data/

# Создайте примеры данных
docker-compose exec rag-service python3 -c "
from app.support_rag import support_rag
print(f'Чанков поддержки: {len(support_rag.chunks)}')
"
```

## Производительность

### Мониторинг
```bash
# Использование ресурсов
docker stats

# Логи в реальном времени
docker-compose logs -f --tail=100
```

### Оптимизация
В `docker-compose.yml`:
```yaml
services:
  rag-service:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
  
  ollama:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

## Резервное копирование

### Данные Ollama
```bash
# Резервное копирование
docker run --rm -v ollama_data:/source -v $(pwd)/backup:/backup alpine \
  tar czf /backup/ollama_backup.tar.gz -C /source .

# Восстановление
docker run --rm -v ollama_data:/target -v $(pwd)/backup:/backup alpine \
  tar xzf /backup/ollama_backup.tar.gz -C /target
```

### Данные приложения
```bash
# Резервное копирование
tar czf data_backup.tar.gz data/

# Восстановление
tar xzf data_backup.tar.gz
```

## Обновление

### Обновление кода
```bash
# Получить изменения
git pull origin main

# Пересобрать
docker-compose up -d --build
```

### Обновление модели
```bash
# Обновить модель Ollama
docker-compose exec ollama ollama pull llama3.2:latest

# Перезапустить
docker-compose restart rag-service
```

## Дополнительная информация

### Документация
- [Архитектура системы](.kilocode/memory-bank/support-assistant-architecture.md)
- [Детали реализации](.kilocode/memory-bank/support-assistant-implementation.md)
- [Инструкция по использованию](.kilocode/memory-bank/support-assistant-usage.md)

### API документация
После запуска откройте в браузере:
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc

### Исходный код
- `app/` - исходный код приложения
- `app/crm.py` - модуль CRM
- `app/support_rag.py` - Support RAG
- `app/support_api.py` - API поддержки
- `app/main.py` - основной файл приложения

### Конфигурация
- `docker-compose.yml` - конфигурация Docker
- `Dockerfile` - образ приложения
- `.env` - переменные окружения (создать)
- `config.py` - конфигурация приложения
