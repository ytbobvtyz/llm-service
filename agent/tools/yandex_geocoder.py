import logging
import asyncio
from typing import List, Tuple, Dict, Any, Optional
import httpx
from math import radians, sin, cos, sqrt, atan2

from app.config import config

logger = logging.getLogger(__name__)


class YandexGeocoder:
    """Клиент для работы с Яндекс Геокодером."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.yandex_maps_api_key
        self.base_url = "https://geocode-maps.yandex.ru/1.x"
        self.timeout = 10.0
        self.retry_delay = 0.05  # 50 мс между запросами
    
    async def geocode_address(self, address: str) -> Tuple[float, float]:
        """
        Прямое геокодирование: адрес → координаты.
        
        Args:
            address: Адрес для геокодирования
            
        Returns:
            Кортеж (широта, долгота)
            
        Raises:
            ValueError: Если адрес не найден или произошла ошибка API
        """
        try:
            params = {
                "apikey": self.api_key,
                "geocode": address,
                "format": "json",
                "results": 1
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Парсинг ответа
            features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
            if not features:
                raise ValueError(f"Адрес не найден: {address}")
            
            # Извлечение координат
            pos = features[0]["GeoObject"]["Point"]["pos"]
            lon, lat = map(float, pos.split())
            
            logger.info(f"Геокодирование успешно: {address} → ({lat:.6f}, {lon:.6f})")
            return lat, lon
            
        except httpx.TimeoutException:
            logger.error(f"Таймаут при геокодировании адреса: {address}")
            raise ValueError(f"Таймаут при геокодировании адреса: {address}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка HTTP при геокодировании: {e}")
            raise ValueError(f"Ошибка API Яндекс Геокодера: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Ошибка при геокодировании адреса {address}: {e}")
            raise ValueError(f"Ошибка при геокодировании: {str(e)}")
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Обратное геокодирование: координаты → регион.
        
        Args:
            lat: Широта
            lon: Долгота
            
        Returns:
            Название региона или None если не удалось определить
        """
        try:
            params = {
                "apikey": self.api_key,
                "geocode": f"{lon},{lat}",
                "format": "json",
                "kind": "district",
                "results": 1,
                "sco": "latlong"  # Указываем, что передаем координаты
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Парсинг ответа для извлечения региона
            features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
            if not features:
                return None
            
            # Ищем AdministrativeAreaName в компонентах
            geo_object = features[0]["GeoObject"]
            components = geo_object.get("metaDataProperty", {}).get("GeocoderMetaData", {}).get("Address", {}).get("Components", [])
            
            for component in components:
                if component.get("kind") == "province" or component.get("kind") == "area":
                    return component.get("name")
            
            # Если не нашли province/area, пробуем district
            for component in components:
                if component.get("kind") == "district":
                    return component.get("name")
            
            # Если ничего не нашли, возвращаем локализованное имя
            return geo_object.get("name")
            
        except Exception as e:
            logger.debug(f"Не удалось определить регион для координат ({lat}, {lon}): {e}")
            return None
    
    async def batch_reverse_geocode(self, coordinates: List[Tuple[float, float]]) -> List[Optional[str]]:
        """
        Батчевое обратное геокодирование.
        
        Args:
            coordinates: Список кортежей (широта, долгота)
            
        Returns:
            Список названий регионов (или None если не удалось определить)
        """
        if not coordinates:
            return []
        
        results = []
        
        # Яндекс Геокодер не поддерживает батчевые запросы через API,
        # поэтому отправляем последовательно с задержкой
        for i, (lat, lon) in enumerate(coordinates):
            try:
                region = await self.reverse_geocode(lat, lon)
                results.append(region)
                
                # Добавляем задержку между запросами, кроме последнего
                if i < len(coordinates) - 1:
                    await asyncio.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.warning(f"Ошибка при обратном геокодировании точки {i}: {e}")
                results.append(None)
        
        return results
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Вычисление расстояния между двумя точками по формуле Хаверсинуса.
        
        Args:
            lat1, lon1: Координаты первой точки
            lat2, lon2: Координаты второй точки
            
        Returns:
            Расстояние в километрах
        """
        # Радиус Земли в километрах
        R = 6371.0
        
        # Преобразование градусов в радианы
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Разницы координат
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Формула Хаверсинуса
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    async def extract_regions_from_polyline(
        self,
        polyline_points: List[Tuple[float, float]],
        step_km: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Извлечение регионов из полилинии маршрута.
        
        Args:
            polyline_points: Список точек полилинии (широта, долгота)
            step_km: Шаг в километрах для выборки точек
            
        Returns:
            Список словарей с информацией о регионах
        """
        if len(polyline_points) < 2:
            return []
        
        # Вычисление кумулятивных расстояний
        cumulative_distances = [0.0]
        sampled_points = [polyline_points[0]]
        
        for i in range(1, len(polyline_points)):
            lat1, lon1 = polyline_points[i-1]
            lat2, lon2 = polyline_points[i]
            distance = self.haversine_distance(lat1, lon1, lat2, lon2)
            cumulative_distances.append(cumulative_distances[-1] + distance)
        
        # Выборка точек каждые step_km километров
        current_distance = 0
        sampled_indices = [0]
        
        while current_distance < cumulative_distances[-1]:
            current_distance += step_km
            
            # Находим индекс точки, ближайшей к текущему расстоянию
            closest_idx = min(
                range(len(cumulative_distances)),
                key=lambda i: abs(cumulative_distances[i] - current_distance)
            )
            
            if closest_idx not in sampled_indices and closest_idx < len(polyline_points):
                sampled_indices.append(closest_idx)
                sampled_points.append(polyline_points[closest_idx])
        
        # Добавляем последнюю точку, если ее еще нет
        if len(polyline_points) - 1 not in sampled_indices:
            sampled_indices.append(len(polyline_points) - 1)
            sampled_points.append(polyline_points[-1])
        
        # Обратное геокодирование выбранных точек
        regions = await self.batch_reverse_geocode(sampled_points)
        
        # Формирование результата с дедупликацией
        result = []
        seen_regions = set()
        
        for idx, (lat, lon) in zip(sampled_indices, sampled_points):
            region_name = regions[idx] if idx < len(regions) else None
            
            if region_name and region_name not in seen_regions:
                seen_regions.add(region_name)
                result.append({
                    "region": region_name,
                    "point": {"lat": lat, "lon": lon}
                })
        
        logger.info(f"Извлечено регионов из полилинии: {len(result)}")
        return result


# Создаем глобальный экземпляр геокодера
geocoder = YandexGeocoder()
