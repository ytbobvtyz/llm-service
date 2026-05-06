import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config import config

logger = logging.getLogger(__name__)


class RAGSearch:
    """Поиск по RAG-базе документов."""
    
    def __init__(self, chroma_db_path: Optional[str] = None):
        self.chroma_db_path = chroma_db_path or config.chroma_db_path
        
        # Инициализация ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Получение коллекции
        try:
            self.collection = self.chroma_client.get_collection(name="resolutions")
        except Exception as e:
            logger.error(f"Ошибка при получении коллекции resolutions: {e}")
            raise ValueError(f"Коллекция resolutions не найдена. Запустите индексацию документов.")
        
        # Инициализация модели для эмбеддингов
        try:
            self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели эмбеддингов: {e}")
            raise
    
    def _extract_numeric_values(self, text: str) -> Dict[str, Any]:
        """Извлечение числовых значений из текста."""
        import re
        
        result = {}
        
        # Поиск нагрузки на ось (в тоннах)
        axle_patterns = [
            r'нагрузк[аи]\s*на\s*ось\s*(\d+[.,]?\d*)\s*т',
            r'(\d+[.,]?\d*)\s*т\s*на\s*ось',
            r'осев[ая]\s*нагрузк[аи]\s*(\d+[.,]?\d*)\s*т',
            r'ограничени[ея]\s*(\d+[.,]?\d*)\s*т'
        ]
        
        for pattern in axle_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    value = float(matches[0].replace(',', '.'))
                    result["axle_weight_tons"] = value
                    break
                except ValueError:
                    continue
        
        # Поиск дат периода
        date_patterns = [
            r'(\d{2}[./]\d{2}[./]\d{4})\s*[-—]\s*(\d{2}[./]\d{2}[./]\d{4})',
            r'с\s*(\d{2}[./]\d{2}[./]\d{4})\s*по\s*(\d{2}[./]\d{2}[./]\d{4})',
            r'период\s*(\d{2}[./]\d{2}[./]\d{4})\s*[-—]\s*(\d{2}[./]\d{2}[./]\d{4})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                start_date, end_date = matches[0]
                result["period"] = f"{start_date} - {end_date}"
                break
        
        return result
    
    async def search_restrictions(
        self,
        regions: List[str],
        query_template: str = "ограничения на просушку дорог весенние ограничения нагрузка на ось",
        year: Optional[int] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Поиск ограничений по регионам.
        
        Args:
            regions: Список регионов для поиска
            query_template: Шаблон запроса
            year: Год документов (опционально)
            top_k: Количество результатов на регион
            
        Returns:
            Словарь с найденными ограничениями
        """
        if not regions:
            return {"restrictions": [], "total_documents_found": 0}
        
        all_results = []
        total_documents = 0
        
        for region in regions:
            try:
                # Подготовка запроса с регионом
                query = f"{region} {query_template}"
                
                # Подготовка фильтров
                where_filter = {"region": {"$in": [region]}}
                if year is not None:
                    where_filter["year"] = str(year)
                
                # Поиск в ChromaDB
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"]
                )
                
                # Обработка результатов
                documents_found = []
                
                if results["ids"] and results["ids"][0]:
                    for i in range(len(results["ids"][0])):
                        doc_id = results["ids"][0][i]
                        text = results["documents"][0][i]
                        metadata = results["metadatas"][0][i]
                        distance = results["distances"][0][i]
                        
                        # Извлечение числовых значений
                        extracted_limits = self._extract_numeric_values(text)
                        
                        documents_found.append({
                            "source": metadata.get("source", ""),
                            "doc_type": metadata.get("doc_type", "unknown"),
                            "year": int(metadata.get("year", 0)) if metadata.get("year", "0").isdigit() else 0,
                            "relevant_chunks": [{
                                "text": text,
                                "distance": float(distance)
                            }],
                            "extracted_limits": extracted_limits
                        })
                        total_documents += 1
                
                if documents_found:
                    all_results.append({
                        "region": region,
                        "documents": documents_found
                    })
                    
            except Exception as e:
                logger.error(f"Ошибка при поиске ограничений для региона {region}: {e}")
                continue
        
        return {
            "restrictions": all_results,
            "total_documents_found": total_documents
        }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Получение статистики коллекции."""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": "resolutions",
                "database_path": self.chroma_db_path
            }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики коллекции: {e}")
            return {"error": str(e)}


# Создаем глобальный экземпляр поиска
rag_search = RAGSearch()
