FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc g++ \
    git \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements и установка Python зависимостей
COPY requirements-docker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Установка дополнительных зависимостей для поддержки
RUN pip install --no-cache-dir \
    slowapi==0.1.9 \
    httpx==0.27.0 \
    numpy==1.26.0 \
    pydantic==2.8.0 \
    python-multipart==0.0.9

# Копирование исходного кода
COPY app/ ./app/
COPY docs/ ./docs/
COPY data/ ./data/

# Создание необходимых директорий
RUN mkdir -p /app/data/faq /app/docs/product /app/app/static

# Переменные окружения по умолчанию
ENV OLLAMA_URL=http://ollama:11434
ENV MODEL_NAME=llama3.2:3b
ENV SUPPORT_DB_PATH=data/support.db
ENV SUPPORT_RAG_DB_PATH=data/support_rag.db
ENV FAQ_PATH=data/faq
ENV PRODUCT_DOCS_PATH=docs/product
ENV CRM_PROVIDER=sqlite
ENV RATE_LIMIT=20/minute
ENV MAX_TOKENS=768
ENV TEMPERATURE=0.4
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
