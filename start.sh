#!/bin/bash

# Скрипт для запуска llm-service с поддержкой пользователей

set -e

echo "🚀 Запуск llm-service с поддержкой пользователей"
echo "================================================"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и повторите попытку."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и повторите попытку."
    exit 1
fi

# Проверка портов
check_port() {
    local port=$1
    local service=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        echo "⚠️  Порт $port используется. Остановите $service или освободите порт."
        read -p "Попробовать остановить существующий контейнер? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker stop $service 2>/dev/null || true
            docker rm $service 2>/dev/null || true
            echo "✅ Контейнер $service остановлен."
        else
            echo "❌ Запуск прерван. Освободите порт $port и повторите попытку."
            exit 1
        fi
    fi
}

echo "🔍 Проверка портов..."
check_port 8000 "rag-service"
check_port 11434 "ollama"

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p data/faq docs/product app/static

# Проверка наличия FAQ файлов
if [ ! -f "data/faq/general_faq.json" ]; then
    echo "📝 Создание примеров FAQ..."
    cat > data/faq/general_faq.json << 'FAQEOF'
[
  {
    "question": "Почему не работает авторизация?",
    "answer": "Проверьте: 1) Правильность логина/пароля 2) Подключение к интернету 3) Статус сервера в статусной панели. Если проблема persists, сбросьте пароль через 'Забыли пароль?'",
    "tags": ["авторизация", "логин", "пароль", "ошибка"]
  },
  {
    "question": "Как восстановить доступ к аккаунту?",
    "answer": "Используйте функцию 'Забыли пароль?' на странице входа. Вам придёт письмо со ссылкой для сброса. Если не получаете письмо, проверьте папку 'Спам'.",
    "tags": ["восстановление", "пароль", "аккаунт", "доступ"]
  }
]
FAQEOF
fi

# Запуск сервисов
echo "🐳 Запуск Docker контейнеров..."
docker-compose up -d --build

echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка health
echo "🏥 Проверка здоровья сервисов..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ RAG сервис запущен и работает"
else
    echo "❌ RAG сервис не отвечает"
    docker-compose logs rag-service
    exit 1
fi

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama запущен и работает"
else
    echo "⚠️  Ollama запускается, может потребоваться больше времени..."
    sleep 10
fi

echo ""
echo "================================================"
echo "✅ Система успешно запущена!"
echo ""
echo "🌐 Доступные эндпоинты:"
echo "   • Веб-интерфейс: http://localhost:8000"
echo "   • API документация: http://localhost:8000/docs"
echo "   • Health check: http://localhost:8000/health"
echo "   • Support health: http://localhost:8000/support/health"
echo ""
echo "🔧 Полезные команды:"
echo "   • Просмотр логов: docker-compose logs -f"
echo "   • Остановка: docker-compose down"
echo "   • Перезапуск: docker-compose restart"
echo ""
echo "💬 Пример запроса к поддержке:"
echo "   curl -X POST http://localhost:8000/support/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Почему не работает авторизация?\"}]}'"
echo "================================================"

# Опционально: следить за логами
read -p "Показать логи? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose logs -f
fi
