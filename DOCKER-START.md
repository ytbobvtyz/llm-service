# Запуск через Docker

## Быстрый старт

### 1. Подготовка
```bash
# Убедитесь, что Docker и Docker Compose установлены
docker --version
docker-compose --version

# Проверьте, что порты 8000 и 11434 свободны
# Если порт 11434 занят, остановите существующий Ollama:
sudo systemctl stop ollama  # если установлен как сервис
# или
docker stop ollama  # если запущен в другом контейнере
```

### 2. Запуск системы
```bash
# Запустить все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановить все сервисы
docker-compose down
```

### 3. Проверка работоспособности
```bash
# Проверить статус контейнеров
docker-compose ps

# Проверить health эндпоинт
curl http://localhost:8000/health

# Проверить health поддержки
curl http://localhost:8000/support/health

# Проверить Ollama
curl http://localhost:11434/api/tags
```

## Расширенная настройка

### Переменные окружения
Создайте файл `.env` для настройки:
```env
# Ollama
OLLAMA_URL=http://ollama:11434
MODEL_NAME=llama3.2:3b

# Support
SUPPORT_DB_PATH=data/support.db
SUPPORT_RAG_DB_PATH=data/support_rag.db
FAQ_PATH=data/faq
PRODUCT_DOCS_PATH=docs/product
CRM_PROVIDER=sqlite

# API
RATE_LIMIT=30/minute
MAX_TOKENS=1024
TEMPERATURE=0.4
API_KEY=your_secret_key_here
```

### Запуск с переменными окружения
```bash
# Запуск с .env файлом
docker-compose --env-file .env up -d

# Или установите переменные в системе
export API_KEY=your_secret_key
docker-compose up -d
```

## Управление контейнерами

### Пересборка после изменений
```bash
# Пересобрать образ и запустить
docker-compose up -d --build

# Только пересобрать
docker-compose build
```

### Очистка
```bash
# Остановить и удалить контейнеры
docker-compose down

# Остановить, удалить контейнеры и volumes
docker-compose down -v

# Остановить, удалить контейнеры, volumes и образы
docker-compose down -v --rmi all
```

### Логи и отладка
```bash
# Просмотр логов всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f rag-service
docker-compose logs -f ollama

# Войти в контейнер
docker-compose exec rag-service bash

# Проверить файлы в контейнере
docker-compose exec rag-service ls -la /app/data/
```

## Примеры использования

### Чат с поддержкой
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

### Получение FAQ
```bash
curl "http://localhost:8000/support/faq"
```

### Статистика
```bash
curl "http://localhost:8000/support/stats"
```

## Устранение неполадок

### Проблема: Порт 11434 уже используется
```bash
# Найдите процесс, использующий порт
sudo lsof -i :11434

# Остановите процесс или измените порт в docker-compose.yml
# Измените в docker-compose.yml:
#   ports:
#     - "11435:11434"  # использовать другой внешний порт
```

### Проблема: Контейнеры не запускаются
```bash
# Проверьте логи
docker-compose logs

# Проверьте доступность портов
netstat -tulpn | grep :8000
netstat -tulpn | grep :11434

# Проверьте образы
docker images | grep llm-service
```

### Проблема: Ollama не загружает модель
```bash
# Проверьте логи Ollama
docker-compose logs ollama

# Загрузите модель вручную
docker-compose exec ollama ollama pull llama3.2:3b

# Проверьте доступные модели
curl http://localhost:11434/api/tags
```

### Проблема: Нет данных поддержки
```bash
# Проверьте volumes
docker-compose exec rag-service ls -la /app/data/

# Проверьте создание FAQ
docker-compose exec rag-service ls -la /app/data/faq/

# Пересоздайте данные
docker-compose down -v
docker-compose up -d
```

## Производительность

### Увеличение лимитов
```bash
# В docker-compose.yml добавьте:
rag-service:
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '1.0'
  mem_limit: 2g
  cpus: 1.0

ollama:
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: '2.0'
  mem_limit: 4g
  cpus: 2.0
```

### Кэширование
Для production используйте reverse proxy с кэшированием:
```nginx
location /support/chat {
    proxy_pass http://rag-service:8000;
    proxy_cache my_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_methods POST;
    proxy_cache_key "$request_body";
}
```

## Безопасность

### API Key
Всегда используйте API Key для production:
```bash
# Установите в .env
API_KEY=your_strong_secret_key_here

# Используйте в запросах
curl -X POST "http://localhost:8000/support/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_strong_secret_key_here" \
  -d '{"messages": [...]}'
```

### Ограничение доступа
В production ограничьте доступ к портам:
```bash
# Используйте firewall
sudo ufw allow 8000/tcp from 192.168.1.0/24
sudo ufw allow 11434/tcp from 192.168.1.0/24
```

## Мониторинг

### Health checks
```bash
# Автоматические health checks
docker-compose ps

# Ручная проверка
curl -f http://localhost:8000/health || echo "Сервис недоступен"
```

### Метрики
Добавьте эндпоинт для метрик:
```python
# В app/main.py
@app.get("/metrics")
async def metrics():
    return {
        "uptime": time.time() - start_time,
        "requests_processed": request_count,
        "active_connections": active_conn_count
    }
```

## Резервное копирование

### Данные Ollama
```bash
# Резервное копирование volumes
docker run --rm -v ollama_data:/source -v $(pwd)/backup:/backup alpine \
  tar czf /backup/ollama_backup_$(date +%Y%m%d).tar.gz -C /source .

# Восстановление
docker run --rm -v ollama_data:/target -v $(pwd)/backup:/backup alpine \
  tar xzf /backup/ollama_backup_20250101.tar.gz -C /target
```

### Данные приложения
```bash
# Резервное копирование data директории
tar czf data_backup_$(date +%Y%m%d).tar.gz data/

# Восстановление
tar xzf data_backup_20250101.tar.gz
```

## Обновление

### Обновление кода
```bash
# Получить последние изменения
git pull origin main

# Пересобрать и запустить
docker-compose up -d --build
```

### Обновление моделей Ollama
```bash
# Обновить модель
docker-compose exec ollama ollama pull llama3.2:latest

# Перезапустить сервис
docker-compose restart rag-service
```

## Production развертывание

### Использование Docker Swarm
```bash
# Инициализировать swarm
docker swarm init

# Развернуть stack
docker stack deploy -c docker-compose.yml llm-service

# Проверить сервисы
docker service ls
```

### Использование Kubernetes
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-service
  template:
    metadata:
      labels:
        app: rag-service
    spec:
      containers:
      - name: rag-service
        image: rag-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: OLLAMA_URL
          value: "http://ollama:11434"
```
