import logging
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from math import radians, sin, cos, sqrt, atan2

from app.config import config
from agent.tools.yandex_geocoder import geocoder

logger = logging.getLogger(__name__)


class YandexRouter:
    """Клиент для работы с Яндекс Router API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.yandex_maps_api_key
        self.base_url = "https://api.routing.yandex.net/v2/route"
        self.timeout = 15.0
        self.max_retries = 2
    
    async def _make_request_with_retry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение запроса с повторными попытками."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(self.base_url, params=params)
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Таймаут при запросе к Router API (попытка {attempt + 1}/{self.max_retries + 1})")
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.error(f"Ошибка HTTP {e.response.status_code} при запросе к Router API: {e.response.text}")
                # Не повторяем при ошибках 4xx (кроме 429)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    break
                    
            except Exception as e:
                last_exception = e
                logger.error(f"Ошибка при запросе к Router API: {e}")
            
            # Экспоненциальная задержка перед повторной попыткой
            if attempt < self.max_retries:
                delay = (2 ** attempt) * 0.5  # 0.5, 1, 2 секунды
                await asyncio.sleep(delay)
        
        # Если все попытки не удались
        raise ValueError(f"Не удалось выполнить запрос к Router API после {self.max_retries + 1} попыток: {last_exception}")
    
    async def build_routes(
        self,
        origin: str,
        destination: str,
        waypoints: Optional[List[str]] = None,
        vehicle_type: str = "truck",
        results: int = 3,
        **truck_params
    ) -> Dict[str, Any]:
        """
        Построение маршрутов через Яндекс Router API.
        
        Args:
            origin: Пункт отправления
            destination: Пункт назначения
            waypoints: Промежуточные точки
            vehicle_type: Тип транспортного средства
            results: Количество альтернативных маршрутов
            **truck_params: Параметры грузовика
            
        Returns:
            Словарь с информацией о маршрутах
        """
        try:
            # Геокодирование точек
            logger.info(f"Геокодирование точек маршрута: {origin} → {destination}")
            origin_coords = await geocoder.geocode_address(origin)
            destination_coords = await geocoder.geocode_address(destination)
            
            waypoint_coords = []
            if waypoints:
                for waypoint in waypoints:
                    coords = await geocoder.geocode_address(waypoint)
                    waypoint_coords.append(coords)
            
            # Подготовка параметров запроса
            params = {
                "apikey": self.api_key,
                "origin": f"{origin_coords[1]},{origin_coords[0]}",  # lon,lat
                "destination": f"{destination_coords[1]},{destination_coords[0]}",
                "mode": "driving",
                "vehicle_type": vehicle_type,
                "results": results
            }
            
            # Добавление промежуточных точек
            if waypoint_coords:
                waypoints_str = "|".join([f"{lon},{lat}" for lat, lon in waypoint_coords])
                params["waypoints"] = waypoints_str
            
            # Добавление параметров грузовика
            if vehicle_type == "truck":
                if "truck_axle_weight" in truck_params:
                    params["truck_axle_weight"] = truck_params["truck_axle_weight"]
                if "truck_weight" in truck_params:
                    params["truck_weight"] = truck_params["truck_weight"]
                if "truck_height" in truck_params:
                    params["truck_height"] = truck_params["truck_height"]
            
            # Выполнение запроса
            logger.info(f"Запрос к Яндекс Router API: {origin} → {destination}")
            data = await self._make_request_with_retry(params)
            
            # Парсинг ответа
            routes = []
            route_data = data.get("routes", [])
            
            for i, route in enumerate(route_data):
                # Извлечение полилинии
                geometry = route.get("geometry", {})
                polyline = geometry.get("polylines", [])
                
                if not polyline:
                    logger.warning(f"Маршрут {i} не содержит полилинии")
                    continue
                
                # Декодирование полилинии (упрощенное - Яндекс возвращает массив координат)
                polyline_points = []
                for segment in polyline:
                    # Каждый сегмент - это строка с координатами
                    points_str = segment.get("points", "")
                    if points_str:
                        # Формат: "lat1 lon1 lat2 lon2 ..."
                        coords = list(map(float, points_str.split()))
                        for j in range(0, len(coords), 2):
                            if j + 1 < len(coords):
                                polyline_points.append((coords[j], coords[j + 1]))
                
                # Извлечение расстояния и времени
                segments = route.get("legs", [{}])[0].get("segments", [])
                total_distance = 0
                total_duration = 0
                
                for segment in segments:
                    total_distance += segment.get("distance", {}).get("value", 0)
                    total_duration += segment.get("duration", {}).get("value", 0)
                
                routes.append({
                    "id": i,
                    "distance_km": total_distance / 1000,  # метры → километры
                    "duration_hours": total_duration / 3600,  # секунды → часы
                    "polyline_points": polyline_points,
                    "is_alternative": i > 0
                })
            
            # Формирование результата
            result = {
                "routes": routes,
                "query_params": {
                    "origin": origin,
                    "destination": destination,
                    "vehicle_type": vehicle_type,
                    **truck_params
                }
            }
            
            logger.info(f"Построено маршрутов: {len(routes)}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при построении маршрута {origin} → {destination}: {e}")
            raise ValueError(f"Ошибка при построении маршрута: {str(e)}")
    
    @staticmethod
    def decode_polyline(polyline_str: str) -> List[Tuple[float, float]]:
        """
        Декодирование полилинии в формате Google.
        Примечание: Яндекс может использовать другой формат, но оставляем для совместимости.
        """
        points = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(polyline_str):
            # Декодирование широты
            b = 0
            shift = 0
            result = 0
            
            while True:
                b = ord(polyline_str[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            delta_lat = ~(result >> 1) if (result & 1) else (result >> 1)
            lat += delta_lat
            
            # Декодирование долготы
            shift = 0
            result = 0
            
            while True:
                b = ord(polyline_str[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            delta_lng = ~(result >> 1) if (result & 1) else (result >> 1)
            lng += delta_lng
            
            points.append((lat / 1e5, lng / 1e5))
        
        return points


# Создаем глобальный экземпляр роутера
router = YandexRouter()
