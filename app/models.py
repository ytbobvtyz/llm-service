#!/usr/bin/env python3
# app/models.py
from typing import List, Optional
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(0.4, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(768, ge=1, le=2048)
    use_rag: Optional[bool] = True

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    latency_ms: int
    rag_used: bool

class HealthResponse(BaseModel):
    status: str
    rag_chunks: int
    model: str