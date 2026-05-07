import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from docx import Document
import chardet
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Индексатор документов для RAG-системы."""
    
    def __init__(
        self,
        resolutions_path: str,
        chroma_db_path: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 100
    ):
        self.resolutions_path = Path(resolutions_path)
        self.chroma_db_path = Path(chroma_db_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Инициализация ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Создание или получение коллекции
        self.collection = self.chroma_client.get_or_create_collection(
            name="resolutions",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Инициализация сплиттера
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def extract_metadata_from_filename(self, filepath: Path) -> Dict[str, str]:
        """Извлечение метаданных из имени файла."""
        filename = filepath.stem  # Без расширения
        parts = filename.split('_')
        
        if len(parts) >= 2:
            region = parts[0]
            doc_type = parts[1]
        elif len(parts) == 1:
            region = parts[0]
            doc_type = "unknown"
        else:
            region = filename
            doc_type = "unknown"
        
        # Год из родительской папки
        year = filepath.parent.name if filepath.parent.name.isdigit() else "unknown"
        
        # Полный путь относительно resolutions_path
        try:
            source = str(filepath.relative_to(self.resolutions_path))
        except ValueError:
            source = str(filepath)
        
        return {
            "region": region,
            "doc_type": doc_type,
            "year": year,
            "source": source,
            "filename": filepath.name
        }
    
    def extract_text_from_pdf(self, filepath: Path) -> str:
        """Извлечение текста из PDF файла с улучшенной обработкой ошибок."""
        text = ""
        try:
            # Проверка существования файла
            if not filepath.exists():
                logger.error(f"PDF файл не существует: {filepath}")
                return ""
            
            # Проверка размера файла
            file_size = filepath.stat().st_size
            if file_size == 0:
                logger.error(f"PDF файл пустой: {filepath}")
                return ""
            
            logger.debug(f"Открытие PDF файла: {filepath} (размер: {file_size} байт)")
            
            # Открытие PDF с обработкой различных ошибок
            try:
                doc = fitz.open(filepath)
            except Exception as e:
                logger.error(f"Не удалось открыть PDF файл {filepath}: {e}")
                return ""
            
            # Проверка количества страниц
            page_count = doc.page_count
            logger.debug(f"PDF содержит {page_count} страниц")
            
            if page_count == 0:
                logger.warning(f"PDF файл не содержит страниц: {filepath}")
                doc.close()
                return ""
            
            # Извлечение текста со всех страниц
            for page_num in range(page_count):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    if page_text:
                        text += page_text + "\n"
                    else:
                        logger.debug(f"Страница {page_num + 1} не содержит текста")
                except Exception as e:
                    logger.warning(f"Ошибка при чтении страницы {page_num + 1}: {e}")
            
            doc.close()
            
            if not text.strip():
                logger.warning(f"PDF файл не содержит извлекаемого текста: {filepath}")
                # Попробуем альтернативный метод извлечения текста
                try:
                    doc = fitz.open(filepath)
                    text = ""
                    for page_num in range(doc.page_count):
                        page = doc.load_page(page_num)
                        text += page.get_text("text") + "\n"
                    doc.close()
                except Exception as e:
                    logger.error(f"Альтернативный метод также не сработал: {e}")
            
            logger.debug(f"Извлечено {len(text)} символов из PDF: {filepath}")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при обработке PDF {filepath}: {e}")
        
        return text
    
    def extract_text_from_docx(self, filepath: Path) -> str:
        """Извлечение текста из DOCX файла."""
        text = ""
        try:
            doc = Document(filepath)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"Ошибка при чтении DOCX {filepath}: {e}")
        return text
    
    def extract_text_from_txt(self, filepath: Path) -> str:
        """Извлечение текста из TXT файла с автоопределением кодировки."""
        try:
            # Определение кодировки
            with open(filepath, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
            
            # Чтение файла
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                text = f.read()
        except Exception as e:
            logger.error(f"Ошибка при чтении TXT {filepath}: {e}")
            text = ""
        return text
    
    def extract_text(self, filepath: Path) -> str:
        """Извлечение текста из файла в зависимости от расширения."""
        ext = filepath.suffix.lower()
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(filepath)
        elif ext == '.docx':
            return self.extract_text_from_docx(filepath)
        elif ext == '.txt':
            return self.extract_text_from_txt(filepath)
        else:
            logger.warning(f"Неподдерживаемый формат файла: {filepath}")
            return ""
    
    def calculate_file_hash(self, filepath: Path) -> str:
        """Вычисление MD5 хэша файла."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def index_document(self, filepath: Path) -> bool:
        """Индексация одного документа."""
        try:
            # Проверка существования файла
            if not filepath.exists():
                logger.error(f"Файл не существует: {filepath}")
                return False
            
            # Вычисление хэша файла
            file_hash = self.calculate_file_hash(filepath)
            
            # Проверка, не был ли уже проиндексирован этот файл
            existing = self.collection.get(
                where={"source_hash": file_hash},
                limit=1
            )
            
            if existing['ids']:
                logger.info(f"Файл уже проиндексирован: {filepath}")
                return True
            
            # Извлечение текста
            text = self.extract_text(filepath)
            if not text:
                logger.warning(f"Не удалось извлечь текст из файла: {filepath}")
                return False
            
            # Извлечение метаданных
            metadata = self.extract_metadata_from_filename(filepath)
            metadata["source_hash"] = file_hash
            
            # Разбивка на чанки
            chunks = self.text_splitter.split_text(text)
            
            # Добавление чанков в ChromaDB
            ids = []
            metadatas = []
            documents = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_hash}_{i}"
                chunk_metadata = metadata.copy()
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(chunks)
                
                ids.append(chunk_id)
                metadatas.append(chunk_metadata)
                documents.append(chunk)
            
            if ids:
                self.collection.add(
                    ids=ids,
                    metadatas=metadatas,
                    documents=documents
                )
                logger.info(f"Проиндексирован файл: {filepath} ({len(chunks)} чанков)")
                return True
            
        except Exception as e:
            logger.error(f"Ошибка при индексации файла {filepath}: {e}")
        
        return False
    
    def index_directory(self, directory: Optional[Path] = None) -> Dict[str, Any]:
        """Рекурсивная индексация всех документов в директории."""
        if directory is None:
            directory = self.resolutions_path
        
        if not directory.exists():
            logger.error(f"Директория не существует: {directory}")
            return {"success": False, "error": "Directory not found"}
        
        supported_extensions = {'.pdf', '.docx', '.txt'}
        stats = {
            "total_files": 0,
            "indexed_files": 0,
            "failed_files": 0,
            "skipped_files": 0
        }
        
        # Рекурсивный обход директории
        for root, dirs, files in os.walk(directory):
            for file in files:
                filepath = Path(root) / file
                stats["total_files"] += 1
                
                # Проверка расширения файла
                if filepath.suffix.lower() not in supported_extensions:
                    stats["skipped_files"] += 1
                    continue
                
                # Индексация файла
                if self.index_document(filepath):
                    stats["indexed_files"] += 1
                else:
                    stats["failed_files"] += 1
        
        logger.info(f"Индексация завершена. Статистика: {stats}")
        return {"success": True, "stats": stats}
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Получение статистики коллекции."""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": "resolutions",
                "database_path": str(self.chroma_db_path)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики коллекции: {e}")
            return {"error": str(e)}


def main():
    """Основная функция для запуска индексации из командной строки."""
    import argparse
    from app.config import config
    
    parser = argparse.ArgumentParser(description="Индексатор документов для RAG-системы")
    parser.add_argument("--path", type=str, default=config.resolutions_path,
                       help="Путь к директории с документами")
    parser.add_argument("--db", type=str, default=config.chroma_db_path,
                       help="Путь к ChromaDB")
    parser.add_argument("--verbose", action="store_true",
                       help="Подробный вывод")
    
    args = parser.parse_args()
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создание индексатора
    indexer = DocumentIndexer(
        resolutions_path=args.path,
        chroma_db_path=args.db
    )
    
    # Запуск индексации
    print(f"Начало индексации документов из: {args.path}")
    result = indexer.index_directory()
    
    if result["success"]:
        print(f"Индексация завершена успешно!")
        stats = result["stats"]
        print(f"Всего файлов: {stats['total_files']}")
        print(f"Проиндексировано: {stats['indexed_files']}")
        print(f"Пропущено: {stats['skipped_files']}")
        print(f"Ошибок: {stats['failed_files']}")
        
        # Вывод статистики коллекции
        collection_stats = indexer.get_collection_stats()
        print(f"Всего чанков в коллекции: {collection_stats.get('total_chunks', 0)}")
    else:
        print(f"Ошибка при индексации: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
