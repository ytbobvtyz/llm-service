#!/bin/bash

set -e

echo "🚚 Запуск логистического агента в Docker"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и повторите попытку."
    exit 1
fi

# Проверка docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ docker-compose не установлен. Установите docker-compose и повторите попытку."
    exit 1
fi

# Определение команды docker-compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Выбор конфигурации
echo ""
echo "Выберите режим запуска:"
echo "1) Полный стек (Ollama + приложение) - требует ~4ГБ памяти"
echo "2) Только приложение (Ollama должна быть запущена локально)"
echo "3) Только приложение с внешней Ollama"
read -p "Введите номер варианта [1]: " choice

case ${choice:-1} in
    1)
        echo "Запуск полного стека..."
        if [ ! -f ".env" ]; then
            echo "Создание .env файла с переменными по умолчанию..."
            cat > .env << ENV_FILE
YANDEX_MAPS_API_KEY=your_api_key_here
ENV_FILE
            echo "⚠️  Обязательно обновите .env файл и установите ваш Яндекс API ключ!"
        fi
        $DOCKER_COMPOSE -f docker-compose.yml up --build
        ;;
    2)
        echo "Запуск только приложения (Ollama должна быть запущена локально на хосте)..."
        $DOCKER_COMPOSE -f docker-compose.app.yml up --build
        ;;
    3)
        read -p "Введите URL Ollama (например, http://192.168.1.100:11434): " ollama_url
        export OLLAMA_BASE_URL=${ollama_url}
        $DOCKER_COMPOSE -f docker-compose.app.yml up --build
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac
