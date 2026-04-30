#!/usr/bin/env python3
"""
API эндпоинты для ассистента поддержки пользователей.
"""

import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import config
from app.models import (
    SupportChatRequest, SupportChatResponse, UserResponse, TicketResponse,
    SupportHistoryResponse, FAQItem, HealthResponse
)

# Импортируем глобальные экземпляры
from app.crm import crm_manager
from app.support_rag import support_rag

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/support", tags=["support"])

# Глобальные состояния (будут установлены в main.py)
ollama_client_instance = None


def setup(ollama_client):
    """Настройка зависимостей"""
    global ollama_client_instance
    ollama_client_instance = ollama_client


@router.get("/health", response_model=HealthResponse)
async def support_health():
    """Проверка здоровья сервиса поддержки"""
    return HealthResponse(
        status="ok",
        rag_chunks=0,  # Для совместимости
        project_docs_chunks=0,  # Для совместимости
        support_chunks=len(support_rag.chunks) if support_rag else 0,
        model=config.model_name
    )


@router.post("/chat", response_model=SupportChatResponse)
@limiter.limit(config.rate_limit)
async def support_chat(request: Request, chat_req: SupportChatRequest):
    """Основной эндпоинт для ассистента поддержки"""
    if not ollama_client_instance:
        raise HTTPException(status_code=500, detail="Ollama client not initialized")
    
    # Проверяем наличие пользователя если указан user_id
    if chat_req.user_id:
        user = crm_manager.provider.get_user(chat_req.user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {chat_req.user_id} not found")
    
    # Проверяем наличие тикета если указан ticket_id
    if chat_req.ticket_id:
        ticket = crm_manager.provider.get_ticket(chat_req.ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {chat_req.ticket_id} not found")
    
    # Вызываем чат поддержки
    response, sources, user_context, ticket_context, latency = await ollama_client_instance.support_chat(
        chat_req, support_rag, crm_manager
    )
    
    return SupportChatResponse(
        response=response,
        sources=sources,
        latency_ms=latency,
        user_context=user_context,
        ticket_context=ticket_context
    )


@router.get("/users", response_model=List[UserResponse])
async def get_users(search: Optional[str] = None, limit: int = 20):
    """Получить список пользователей"""
    if search:
        users = crm_manager.provider.search_users(search)
    else:
        # Для простоты возвращаем пустой список если нет поиска
        # В реальной системе здесь была бы пагинация
        users = []
    
    return users[:limit]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Получить пользователя по ID"""
    user = crm_manager.provider.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@router.get("/users/{user_id}/tickets", response_model=List[TicketResponse])
async def get_user_tickets(user_id: str, limit: int = 10):
    """Получить тикеты пользователя"""
    user = crm_manager.provider.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    tickets = crm_manager.provider.get_user_tickets(user_id, limit=limit)
    return tickets


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str):
    """Получить тикет по ID"""
    ticket = crm_manager.provider.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.get("/users/{user_id}/history", response_model=List[SupportHistoryResponse])
async def get_user_support_history(user_id: str, limit: int = 20):
    """Получить историю поддержки пользователя"""
    # В текущей реализации история хранится в БД
    # Для простоты возвращаем пустой список
    # В реальной системе здесь был бы запрос к БД
    return []


@router.get("/faq", response_model=List[FAQItem])
async def get_faq(search: Optional[str] = None, tag: Optional[str] = None):
    """Получить FAQ"""
    # Загружаем FAQ из файлов
    faq_items = []
    faq_dir = config.faq_path
    
    if not os.path.exists(faq_dir):
        return []
    
    for filename in os.listdir(faq_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(faq_dir, filename)
            try:
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                
                for item in items:
                    # Фильтрация по поиску
                    if search and search.lower() not in item.get('question', '').lower():
                        continue
                    
                    # Фильтрация по тегу
                    if tag and tag not in item.get('tags', []):
                        continue
                    
                    faq_items.append(FAQItem(**item))
            
            except Exception as e:
                print(f"Ошибка загрузки FAQ файла {filename}: {e}")
    
    return faq_items


@router.post("/faq")
async def add_faq_item(item: FAQItem):
    """Добавить новый FAQ вопрос"""
    faq_dir = config.faq_path
    os.makedirs(faq_dir, exist_ok=True)
    
    # Загружаем существующие FAQ
    faq_file = os.path.join(faq_dir, "general_faq.json")
    items = []
    
    if os.path.exists(faq_file):
        import json
        with open(faq_file, 'r', encoding='utf-8') as f:
            items = json.load(f)
    
    # Добавляем новый вопрос
    items.append(item.dict())
    
    # Сохраняем
    with open(faq_file, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    
    # Переиндексируем Support RAG
    support_rag._index_faq()
    support_rag._save_to_db()
    
    return {"status": "success", "message": "FAQ item added"}


@router.post("/tickets")
async def create_ticket(ticket_data: dict):
    """Создать новый тикет"""
    # В реальной системе здесь была бы валидация и создание тикета
    # Для демонстрации возвращаем успех
    return {
        "status": "success",
        "ticket_id": str(uuid.uuid4()),
        "message": "Ticket created (demo mode)"
    }


@router.get("/stats")
async def get_support_stats():
    """Получить статистику поддержки"""
    # В реальной системе здесь была бы агрегация данных
    return {
        "total_users": 0,  # Демо значение
        "active_tickets": 0,
        "resolved_today": 0,
        "avg_response_time": "2h 30m",
        "faq_items": len(support_rag.chunks) // 2  # Примерное количество FAQ
    }
