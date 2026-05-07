"""
Ядро логистического AI-агента для анализа ограничений на просушку дорог.
"""
import logging
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.config import config
from agent.tools.yandex_routes import router as yandex_router
from agent.tools.yandex_geocoder import geocoder
from agent.tools.rag_search import rag_search

logger = logging.getLogger(__name__)


class LogisticsAgent:
    """
    Основной класс логистического агента.
    Координирует работу всех инструментов для анализа маршрутов и ограничений.
    """
    
    def __init__(self):
        self._validate_config()
        logger.info("Логистический агент инициализирован")
    
    def _validate_config(self):
        """Проверка конфигурации."""
        if not config.yandex_maps_api_key:
            logger.warning("YANDEX_MAPS_API_KEY не установлен - геокодирование и построение маршрутов будут недоступны")
    
    async def process_request(self, message: str) -> Dict[str, Any]:
        """
        Обработка запроса пользователя.
        
        Args:
            message: Текст запроса пользователя
            
        Returns:
            Словарь с результатами обработки
        """
        logger.info(f"Обработка запроса: {message}")
        
        # Извлечение параметров маршрута из запроса
        route_params = self._extract_route_params(message)
        
        if not route_params.get("origin") or not route_params.get("destination"):
            return {
                "text": "Не удалось определить маршрут. Укажите пункт отправления и пункт назначения.",
                "json": None,
                "debug_info": {"error": "missing_route_params"}
            }
        
        debug_info = {
            "step": "route_extraction",
            "params": route_params,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Построение маршрутов
            routes_result = await yandex_router.build_routes(
                origin=route_params["origin"],
                destination=route_params["destination"],
                vehicle_type=route_params.get("vehicle_type", "truck"),
                truck_weight=route_params.get("truck_weight"),
                truck_axle_weight=route_params.get("truck_axle_weight"),
                truck_height=route_params.get("truck_height")
            )
            
            debug_info["routes"] = routes_result.get("routes", [])
            debug_info["step"] = "routes_built"
            
            if not routes_result.get("routes"):
                return {
                    "text": "Не удалось построить маршрут. Проверьте правильность адресов.",
                    "json": routes_result,
                    "debug_info": debug_info
                }
            
            # Определение регионов на маршруте
            primary_route = routes_result["routes"][0]
            polyline = primary_route.get("polyline_points", [])
            
            regions = await geocoder.extract_regions_from_polyline(
                polyline_points=polyline,
                step_km=200
            )
            
            debug_info["regions"] = regions
            debug_info["step"] = "regions_identified"
            
            # Поиск ограничений по регионам
            region_names = [r["region"] for r in regions if r.get("region")]
            
            if region_names:
                restrictions = await rag_search.search_restrictions(
                    regions=region_names,
                    year=route_params.get("year")
                )
                
                debug_info["restrictions"] = restrictions
                debug_info["step"] = "restrictions_found"
            else:
                restrictions = {"restrictions": [], "total_documents_found": 0}
            
            # Формирование ответа
            response_text = self._format_response(
                routes=routes_result,
                regions=regions,
                restrictions=restrictions,
                route_params=route_params
            )
            
            return {
                "text": response_text,
                "json": {
                    "routes": routes_result,
                    "regions": regions,
                    "restrictions": restrictions
                },
                "debug_info": debug_info
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            debug_info["error"] = str(e)
            debug_info["step"] = "error"
            
            return {
                "text": f"Произошла ошибка при обработке запроса: {str(e)}",
                "json": None,
                "debug_info": debug_info
            }
    
    def _extract_route_params(self, message: str) -> Dict[str, Any]:
        """
        Извлечение параметров маршрута из текста запроса.
        
        Args:
            message: Текст запроса пользователя
            
        Returns:
            Словарь с параметрами маршрута
        """
        params = {
            "origin": None,
            "destination": None,
            "vehicle_type": "truck",
            "truck_weight": None,
            "truck_axle_weight": None,
            "truck_height": None,
            "year": datetime.now().year
        }
        
        message_lower = message.lower()
        
        # Поиск паттернов маршрута "Откуда - Куда" или "Из ... в ..."
        route_patterns = [
            r'от\s+(.+?)\s+(?:до|в|→)\s+(.+)',
            r'из\s+(.+?)\s+(?:в|до|на|→)\s+(.+)',
            r'(.+?)\s*[-–—]\s*(.+?)(?:\s+для|\s+груз|\s+тонн|$)',
            r'(.+?)\s+до\s+(.+?)(?:\s+для|\s+груз|\s+тонн|$)',
        ]
        
        for pattern in route_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params["origin"] = match.group(1).strip()
                params["destination"] = match.group(2).strip()
                break
        
        # Если маршрут не найден, пробуем найти просто два города
        if not params["origin"] or not params["destination"]:
            # Ищем названия городов (упрощенно)
            words = message.split()
            if len(words) >= 2:
                # Берем первое и последнее слово как возможные города
                params["origin"] = words[0]
                params["destination"] = words[-1]
        
        # Извлечение веса грузовика
        weight_patterns = [
            r'(\d+)\s*тонн',
            r'(\d+)\s*т',
            r'вес\s*(\d+)',
        ]
        for pattern in weight_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params["truck_weight"] = float(match.group(1))
                break
        
        # Извлечение нагрузки на ось
        axle_patterns = [
            r'ос[её]\s*(\d+)',
            r'на\s*ось\s*(\d+)',
        ]
        for pattern in axle_patterns:
            match = re.search(pattern, message_lower)
            if match:
                params["truck_axle_weight"] = float(match.group(1))
                break
        
        # Извлечение года
        year_pattern = r'(20\d{2})'
        match = re.search(year_pattern, message)
        if match:
            params["year"] = int(match.group(1))
        
        return params
    
    def _format_response(
        self,
        routes: Dict[str, Any],
        regions: List[Dict[str, Any]],
        restrictions: Dict[str, Any],
        route_params: Dict[str, Any]
    ) -> str:
        """
        Форматирование текстового ответа.
        
        Args:
            routes: Результаты построения маршрутов
            regions: Определенные регионы
            restrictions: Найденные ограничения
            route_params: Параметры маршрута
            
        Returns:
            Отформатированный текст ответа
        """
        lines = []
        
        # Заголовок
        lines.append(f"🚛 **Маршрут: {route_params['origin']} → {route_params['destination']}**")
        lines.append("")
        
        # Маршруты
        if routes.get("routes"):
            lines.append("## Маршруты")
            for route in routes["routes"]:
                alt_marker = " (альтернативный)" if route.get("is_alternative") else ""
                lines.append(f"- **{route['id'] + 1}{alt_marker}**: {route['distance_km']:.0f} км, ~{route['duration_hours']:.1f} ч.")
            lines.append("")
        
        # Регионы
        if regions:
            lines.append("## Регионы следования")
            for region in regions:
                if region.get("region"):
                    lines.append(f"- {region['region']}")
            lines.append("")
        
        # Ограничения
        restrictions_list = restrictions.get("restrictions", [])
        if restrictions_list:
            lines.append("## Найденные ограничения")
            for region_restrictions in restrictions_list:
                region = region_restrictions.get("region", "Unknown")
                lines.append(f"### {region}")
                
                docs = region_restrictions.get("documents", [])
                for doc in docs:
                    lines.append(f"- **{doc['doc_type']}** ({doc['year']})")
                    
                    extracted = doc.get("extracted_limits", {})
                    if extracted.get("axle_weight_tons"):
                        lines.append(f"  - Нагрузка на ось: {extracted['axle_weight_tons']} т")
                    if extracted.get("period"):
                        lines.append(f"  - Период: {extracted['period']}")
            lines.append("")
        else:
            lines.append("## Ограничения")
            lines.append("Ограничения не найдены для регионов данного маршрута.")
            lines.append("")
        
        # Рекомендации
        if restrictions_list:
            lines.append("## Рекомендации")
            lines.append("Учитывайте найденные ограничения при планировании рейса.")
            lines.append("Рекомендуется уточнить информацию в местных органах власти.")
        
        return "\n".join(lines)


# Глобальный экземпляр агента
_agent: Optional[LogisticsAgent] = None


def initialize_agent() -> LogisticsAgent:
    """Инициализация агента."""
    global _agent
    _agent = LogisticsAgent()
    return _agent


def get_agent() -> Optional[LogisticsAgent]:
    """Получение экземпляра агента."""
    return _agent
