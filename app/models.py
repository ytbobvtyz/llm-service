from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(0.4, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(768, ge=1, le=4096)
    use_rag: Optional[bool] = True
    user_id: Optional[str] = None
    ticket_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    latency_ms: int
    rag_used: bool
    user_context_used: bool = False
    ticket_context_used: bool = False


class HealthResponse(BaseModel):
    status: str
    rag_chunks: int
    project_docs_chunks: int
    support_chunks: int
    model: str


# Модели для поддержки пользователей
class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    subscription_plan: str
    created_at: str
    last_contact_at: str


class TicketResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    status: str
    priority: str
    created_at: str
    updated_at: str
    assigned_to: Optional[str] = None


class SupportHistoryResponse(BaseModel):
    id: str
    user_id: str
    ticket_id: Optional[str] = None
    question: str
    answer: str
    timestamp: str


class FAQItem(BaseModel):
    question: str
    answer: str
    tags: List[str] = []


class SupportChatRequest(BaseModel):
    messages: List[ChatMessage]
    user_id: Optional[str] = None
    ticket_id: Optional[str] = None
    temperature: Optional[float] = Field(0.4, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(1024, ge=1, le=4096)


class SupportChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    latency_ms: int
    user_context: Optional[Dict[str, Any]] = None
    ticket_context: Optional[Dict[str, Any]] = None
