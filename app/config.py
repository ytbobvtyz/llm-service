import os
from pydantic_settings import BaseSettings
from typing import Optional


class Config(BaseSettings):
    # API ключи
    yandex_maps_api_key: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    
    # Пути
    chroma_db_path: str = "./chroma_db"
    resolutions_path: str = "./resolutions"
    
    # Настройки сервера
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Настройки индексации
    chunk_size: int = 1000
    chunk_overlap: int = 100
    
    # Настройки маршрутизации
    default_vehicle_type: str = "truck"
    default_axle_weight: float = 10.0  # тонн
    default_period_days: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаем глобальный экземпляр конфигурации
config = Config()
