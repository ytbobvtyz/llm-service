#!/bin/bash

echo "🚀 Быстрый запуск llm-service с поддержкой пользователей"
echo "========================================================"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    exit 1
fi

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker-compose down 2>/dev/null

# Проверка портов
echo "🔍 Проверка портов..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Порт 8000 занят. Освободите порт или измените конфигурацию."
    exit 1
fi

if lsof -i :11434 > /dev/null 2>&1; then
    echo "⚠️  Порт 11434 занят. Останавливаю существующий Ollama..."
    docker stop ollama 2>/dev/null || true
    docker rm ollama 2>/dev/null || true
fi

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p data/faq docs/product

# Запуск сервисов
echo "🐳 Запуск сервисов..."
docker-compose up -d

echo "⏳ Ожидание запуска (20 секунд)..."
sleep 20

# Проверка
echo "🏥 Проверка здоровья..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ RAG сервис запущен"
else
    echo "❌ RAG сервис не отвечает"
    docker-compose logs rag-service
    exit 1
fi

echo ""
echo "========================================================"
echo "✅ Система запущена!"
echo ""
echo "🌐 Доступные адреса:"
echo "   • Веб: http://localhost:8000"
echo "   • API: http://localhost:8000/docs"
echo "   • Ollama: http://localhost:11434"
echo ""
echo "💬 Пример запроса:"
echo "   curl -X POST http://localhost:8000/support/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Помогите с авторизацией\"}]}'"
echo "========================================================"
