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
    
    def _is_help_request(self, message: str) -> bool:
        """Проверка, является ли запрос справочным."""
        message_lower = message.lower().strip()
        
        help_patterns = [
            r'^помоги',
            r'^помощь',
            r'^help',
            r'^что\s+ты\s+умеешь',
            r'^как\s+работаешь',
            r'^как\s+тебя\s+использовать',
            r'^инструкция',
            r'^справка',
            r'^что\s+делаешь',
            r'^расскажи\s+о\s+себе',
        ]
        
        for pattern in help_patterns:
            if re.match(pattern, message_lower):
                return True
        
        return False
    
    async def process_request(self, message: str) -> Dict[str, Any]:
        """
        Обработка запроса пользователя.
        
        Args:
            message: Текст запроса пользователя
            
        Returns:
            Словарь с результатами обработки
        """
        logger.info(f"Обработка запроса: {message}")
        
        # Проверяем, является ли это справочным запросом
        if self._is_help_request(message):
            debug_info = {
                "step": "help",
                "timestamp": datetime.now().isoformat()
            }
            return {
                "text": self._get_help_message(),
                "json": None,
                "debug_info": debug_info
            }
        
        # Извлечение параметров маршрута из запроса
        route_params = self._extract_route_params(message)
        
        debug_info = {
            "step": "start",
            "params": route_params,
            "timestamp": datetime.now().isoformat()
        }
        
        # Если не удалось определить маршрут - возвращаем подсказку
        if not route_params.get("origin") or not route_params.get("destination"):
            return {
                "text": self._get_help_message(),
                "json": None,
                "debug_info": debug_info
            }
        
        try:
            debug_info["step"] = "building_routes"
            
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
                    "text": f"Не удалось построить маршрут от {route_params['origin']} до {route_params['destination']}. "
                            f"Проверьте названия городов или попробуйте другой маршрут.",
                    "json": routes_result,
                    "debug_info": debug_info
                }
            
            # Определение регионов на маршруте
            primary_route = routes_result["routes"][0]
            polyline = primary_route.get("polyline_points", [])
            
            debug_info["step"] = "identifying_regions"
            
            regions = await geocoder.extract_regions_from_polyline(
                polyline_points=polyline,
                step_km=200
            )
            
            debug_info["regions"] = regions
            debug_info["step"] = "regions_identified"
            
            # Поиск ограничений по регионам
            region_names = [r["region"] for r in regions if r.get("region")]
            
            if region_names:
                debug_info["step"] = "searching_restrictions"
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
            
            # Формируем понятный ответ об ошибке
            error_message = self._format_error_message(e, route_params)
            
            return {
                "text": error_message,
                "json": None,
                "debug_info": debug_info
            }
    
    def _get_help_message(self) -> str:
        """Получение справочного сообщения."""
        return """🚛 **Логистический помощник**

Я помогу вам спланировать рейс по РФ в период паводков. Просто укажите маршрут.

**Примеры запросов:**
• "Пермь-Москва"
• "Казань-Екатеринбург паводки"
• "Екатеринбург-Москва для грузовика 8 тонн"
• "Построй маршрут Москва-Казань"

**Что я делаю:**
1. Строю оптимальные маршруты через Яндекс API
2. Определяю регионы следования
3. Ищу ограничения на просушку дорог в базе документов
4. Предлагаю альтернативные маршруты при необходимости

Просто укажите пункт отправления и пункт назначения!"""
    
    def _format_error_message(self, error: Exception, route_params: Dict[str, Any]) -> str:
        """Формирование понятного сообщения об ошибке."""
        error_str = str(error).lower()
        
        if "403" in error_str or "401" in error_str or "bad request" in error_str:
            return f"""⚠️ **Ошибка при построении маршрута**

Не удалось построить маршрут от **{route_params['origin']}** до **{route_params['destination']}**.

Возможные причины:
• API ключ Яндекс Карт не имеет доступа к Router API
• Неверный формат названий городов

Попробуйте:
• Убедиться, что API ключ имеет доступ к Яндекс Router API
• Использовать более точные названия городов (например: "Пермь, Пермский край" вместо "Пермь")

Текущий маршрут: {route_params['origin']} → {route_params['destination']}"""
        
        elif "timeout" in error_str or "timed out" in error_str:
            return f"""⏱️ **Превышен таймаут**

Не удалось построить маршрут от **{route_params['origin']}** до **{route_params['destination']}** вовремя.

Попробуйте повторить запрос позже."""
        
        else:
            return f"""❌ **Ошибка при обработке запроса**

Не удалось обработать запрос: {str(error)}

Маршрут: {route_params['origin']} → {route_params['destination']}

Попробуйте:
• Проверить названия городов
• Повторить запрос позже
• Использовать более короткий маршрут"""
    
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
            r'построй\s+(?:маршрут\s+)?(?:из\s+)?(.+?)\s+(?:в|до|→)\s+(.+)',
            r'маршрут\s+(?:из\s+)?(.+?)\s+(?:в|до|→)\s+(.+)',
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
                params["origin"] = words[0].strip()
                params["destination"] = words[-1].strip()
        
        # Извлечение веса грузовика
        weight_patterns = [
            r'(\d+)\s*тонн',
            r'(\d+)\s*т',
            r'вес\s*(\d+)',
            r'груз\s*(\d+)',
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
            r'осевая?\s*нагрузк[аи]?\s*(\d+)',
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
            lines.append("### Маршруты")
            for route in routes["routes"]:
                alt_marker = " (альтернативный)" if route.get("is_alternative") else ""
                lines.append(f"- **{route['id'] + 1}{alt_marker}**: {route['distance_km']:.0f} км, ~{route['duration_hours']:.1f} ч.")
            lines.append("")
        
        # Регионы
        if regions:
            lines.append("### Регионы следования")
            for region in regions:
                if region.get("region"):
                    lines.append(f"- {region['region']}")
            lines.append("")
        
        # Ограничения
        restrictions_list = restrictions.get("restrictions", [])
        if restrictions_list:
            lines.append("### Найденные ограничения")
            for region_restrictions in restrictions_list:
                region = region_restrictions.get("region", "Unknown")
                lines.append(f"**{region}:**")
                
                docs = region_restrictions.get("documents", [])
                for doc in docs:
                    lines.append(f"- **{doc['doc_type']}** ({doc['year']})")
                    
                    extracted = doc.get("extracted_limits", {})
                    if extracted.get("axle_weight_tons"):
                        lines.append(f"  • Нагрузка на ось: {extracted['axle_weight_tons']} т")
                    if extracted.get("period"):
                        lines.append(f"  • Период: {extracted['period']}")
            lines.append("")
        else:
            lines.append("### Ограничения")
            lines.append("Ограничения не найдены для регионов данного маршрута.")
            lines.append("")
        
        # Рекомендации
        if restrictions_list:
            lines.append("### Рекомендации")
            lines.append("• Учитывайте найденные ограничения при планировании рейса")
            lines.append("• Рекомендуется уточнить информацию в местных органах власти")
        
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
