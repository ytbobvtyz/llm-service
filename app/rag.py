import os
import sqlite3
import json
from typing import List, Dict


class RAGRetriever:
    """RAG для документов логистики (старый)"""
    
    def __init__(self, db_path: str, index_path: str):
        self.db_path = db_path
        self.index_path = index_path
        self.chunks = []
        self._load()
    
    def _load(self):
        print(f"📚 Загрузка RAG из {self.db_path}")
        
        if not os.path.exists(self.db_path):
            print(f"⚠️ Файл {self.db_path} не найден")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, text, filename FROM chunks")
        for row in cursor.fetchall():
            self.chunks.append({
                'id': row[0],
                'text': row[1],
                'filename': row[2] if row[2] else "unknown"
            })
        conn.close()
        print(f"✅ Загружено {len(self.chunks)} чанков из БД")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Поиск по ключевым словам (без эмбеддингов для экономии места)"""
        if not self.chunks:
            return []
        
        query_words = set(query.lower().split())
        scored = []
        
        for chunk in self.chunks:
            text = chunk.get('text', '').lower()
            score = sum(1 for word in query_words if word in text)
            if score > 0:
                scored.append((score, chunk))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{'text': c['text'], 'filename': c['filename'], 'score': s} 
                for s, c in scored[:top_k]]


class ProjectDocsRAG:
    """RAG для документации проекта (с автоиндексацией)"""
    
    def __init__(self, docs_path: str = "docs", db_path: str = "data/project_docs.db"):
        self.docs_path = docs_path
        self.db_path = db_path
        self.chunks = []
        self.last_indexed = {}
        self._load_or_index()
    
    def _load_or_index(self):
        """Загружает существующий индекс или создаёт новый"""
        if os.path.exists(self.db_path):
            self._load_from_db()
        else:
            self._index_docs()
    
    def _load_from_db(self):
        """Загружает чанки из SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT text, filename, modified_at FROM chunks")
            for row in cursor.fetchall():
                self.chunks.append({
                    'text': row[0],
                    'filename': row[1],
                    'modified_at': row[2]
                })
            conn.close()
            print(f"✅ Загружено {len(self.chunks)} чанков из {self.db_path}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки БД: {e}")
            self._index_docs()
    
    def _index_docs(self):
        """Индексирует документацию из папки docs/"""
        if not os.path.exists(self.docs_path):
            print(f"⚠️ Папка {self.docs_path} не найдена")
            return
        
        self.chunks = []
        
        for filename in os.listdir(self.docs_path):
            if filename.endswith(('.md', '.txt')):
                filepath = os.path.join(self.docs_path, filename)
                stat = os.stat(filepath)
                modified_at = stat.st_mtime
                
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    chunks = self._chunk_text(content, filename, modified_at)
                    self.chunks.extend(chunks)
        
        self._save_to_db()
        print(f"✅ Проиндексировано {len(self.chunks)} чанков из docs/")
    
    def _chunk_text(self, text: str, filename: str, modified_at: float, chunk_size: int = 1000) -> List[Dict]:
        """Разбивает текст на чанки"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append({
                'text': chunk,
                'filename': filename,
                'modified_at': modified_at,
                'type': 'project_docs'
            })
        
        return chunks
    
    def _save_to_db(self):
        """Сохраняет чанки в SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                filename TEXT,
                modified_at REAL
            )
        ''')
        
        cursor.execute("DELETE FROM chunks")
        
        for chunk in self.chunks:
            cursor.execute(
                "INSERT INTO chunks (text, filename, modified_at) VALUES (?, ?, ?)",
                (chunk['text'], chunk['filename'], chunk.get('modified_at', 0))
            )
        
        conn.commit()
        conn.close()
    
    def check_and_reindex(self):
        """Проверяет изменения в файлах и переиндексирует при необходимости"""
        if not os.path.exists(self.docs_path):
            return False
        
        need_reindex = False
        
        for filename in os.listdir(self.docs_path):
            if filename.endswith(('.md', '.txt')):
                filepath = os.path.join(self.docs_path, filename)
                current_mtime = os.stat(filepath).st_mtime
                
                # Ищем сохранённую метку времени
                for chunk in self.chunks:
                    if chunk['filename'] == filename:
                        if chunk.get('modified_at', 0) != current_mtime:
                            need_reindex = True
                        break
                else:
                    need_reindex = True
        
        if need_reindex:
            print("🔄 Обнаружены изменения в документации, переиндексация...")
            self._index_docs()
            return True
        
        return False
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Поиск по документации проекта"""
        if not self.chunks:
            return []
        
        # Проверяем изменения перед поиском
        self.check_and_reindex()
        
        query_words = set(query.lower().split())
        scored = []
        
        for chunk in self.chunks:
            text = chunk.get('text', '').lower()
            score = sum(1 for word in query_words if word in text)
            if score > 0:
                scored.append((score, chunk))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{'text': c['text'], 'filename': c['filename'], 'score': s} 
                for s, c in scored[:top_k]]
    
    def get_stats(self) -> Dict:
        """Получить статистику индекса"""
        return {
            "total_chunks": len(self.chunks),
            "db_path": self.db_path,
            "docs_path": self.docs_path
        }