FROM python:3.12-slim

WORKDIR /app

# Установка git и зависимостей
RUN apt-get update && apt-get install -y \
    gcc g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY docs/ ./docs/
COPY data/ ./data/

ENV OLLAMA_URL=http://ollama:11434
ENV MODEL_NAME=llama3.2:3b

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]