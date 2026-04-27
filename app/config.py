#!/usr/bin/env python3
# app/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Ollama
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model_name: str = os.getenv("MODEL_NAME", "llama3.2:3b")
    
    # RAG
    db_path: str = os.getenv("DB_PATH", "data/metadata.db")
    index_path: str = os.getenv("INDEX_PATH", "data/faiss_index")
    
    # API
    rate_limit: str = os.getenv("RATE_LIMIT", "20/minute")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "768"))
    
    # Server
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))

config = Config()