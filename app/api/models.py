from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ComponentStatus(BaseModel):
    """Статус компонента системы."""
    status: str  # healthy, unhealthy, unknown, configured, exists, missing
    message: str


class StatusResponse(BaseModel):
    """Ответ со статусом системы."""
    status: str  # operational, degraded, offline
    components: Dict[str, ComponentStatus]
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Запрос на общение с агентом."""
    message: str
    session_id: Optional[str] = None
    stream: bool = False


class RoutePoint(BaseModel):
    """Точка маршрута."""
    lat: float
    lon: float


class RouteSegment(BaseModel):
    """Сегмент маршрута."""
    id: int
    distance_km: float
    duration_hours: float
    polyline_points: List[RoutePoint]
    is_alternative: bool = False


class RouteResponse(BaseModel):
    """Ответ с маршрутами."""
    routes: List[RouteSegment]
    query_params: Dict[str, Any]


class RegionInfo(BaseModel):
    """Информация о регионе."""
    region: str
    point: RoutePoint


class RestrictionsChunk(BaseModel):
    """Чанк с ограничениями."""
    text: str
    distance: float


class DocumentInfo(BaseModel):
    """Информация о документе."""
    source: str
    doc_type: str
    year: int
    relevant_chunks: List[RestrictionsChunk]
    extracted_limits: Dict[str, Any]


class RegionRestrictions(BaseModel):
    """Ограничения по региону."""
    region: str
    documents: List[DocumentInfo]


class RestrictionsResponse(BaseModel):
    """Ответ с ограничениями."""
    restrictions: List[RegionRestrictions]
    total_documents_found: int


class ChatResponse(BaseModel):
    """Ответ от агента."""
    text: str
    json: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class DebugEvent(BaseModel):
    """Событие для отладочного потока."""
    type: str  # route_built, regions_identified, documents_found, error
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ReindexRequest(BaseModel):
    """Запрос на переиндексацию."""
    force: bool = False
    path: Optional[str] = None


class ReindexResponse(BaseModel):
    """Ответ на запрос переиндексации."""
    success: bool
    message: str
    stats: Optional[Dict[str, Any]] = None
