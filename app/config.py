import os
from dataclasses import dataclass

@dataclass
class Config:
    # Ollama
    ollama_url: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    model_name: str = os.getenv("MODEL_NAME", "llama3.2:3b")
    
    # RAG
    db_path: str = os.getenv("DB_PATH", "data/metadata.db")
    index_path: str = os.getenv("INDEX_PATH", "data/faiss_index")
    
    # API
    rate_limit: str = os.getenv("RATE_LIMIT", "20/minute")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "768"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.4"))
    
    # Server
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))
    
    # Context
    context_length: int = int(os.getenv("CONTEXT_LENGTH", "4096"))

config = Config()