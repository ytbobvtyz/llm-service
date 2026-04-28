import os
import sqlite3
import numpy as np
from typing import List, Dict

class RAGRetriever:
    def __init__(self, db_path: str, index_path: str):
        self.db_path = db_path
        self.index_path = index_path
        self.chunks = []
        self.index = None
        self.model = None
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
        print(f"✅ Загружено {len(self.chunks)} чанков")
        
        # Пробуем загрузить FAISS
        try:
            import faiss
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                print(f"✅ FAISS индекс загружен: {self.index.ntotal} векторов")
        except ImportError:
            print("⚠️ FAISS не установлен")
        except Exception as e:
            print(f"⚠️ Ошибка FAISS: {e}")
        
        # Пробуем загрузить модель эмбеддингов
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print(f"✅ Модель эмбеддингов загружена")
        except ImportError:
            print("⚠️ sentence-transformers не установлен")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        if not self.chunks:
            return []
        
        # Semantic search через FAISS
        if self.model and self.index:
            try:
                import faiss
                query_vec = self.model.encode([query])[0]
                query_vec = np.array(query_vec, dtype=np.float32).reshape(1, -1)
                faiss.normalize_L2(query_vec)
                distances, indices = self.index.search(query_vec, top_k)
                
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if 0 <= idx < len(self.chunks):
                        chunk = self.chunks[idx]
                        results.append({
                            'text': chunk['text'],
                            'filename': chunk['filename'],
                            'score': float(dist)
                        })
                return results
            except Exception as e:
                print(f"⚠️ Ошибка FAISS: {e}")
        
        # Fallback: keyword search
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
    """RAG для документации проекта"""
    
    def __init__(self, docs_path: str = "docs", db_path: str = "data/project_docs.db"):
        self.docs_path = docs_path
        self.db_path = db_path
        self.chunks = []
        self._load_docs()
    
    def _load_docs(self):
        """Загружает документацию из папки docs/"""
        if not os.path.exists(self.docs_path):
            print(f"⚠️ Папка {self.docs_path} не найдена")
            return
        
        for filename in os.listdir(self.docs_path):
            if filename.endswith(('.md', '.txt')):
                filepath = os.path.join(self.docs_path, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Разбиваем на чанки
                        chunks = self._chunk_text(content, filename)
                        self.chunks.extend(chunks)
                except Exception as e:
                    print(f"⚠️ Ошибка чтения {filename}: {e}")
        
        print(f"✅ Загружено {len(self.chunks)} чанков из docs/")
    
    def _chunk_text(self, text: str, filename: str, chunk_size: int = 1000) -> List[Dict]:
        """Разбивает текст на чанки"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append({
                'text': chunk,
                'filename': filename,
                'type': 'project_docs'
            })
        
        return chunks
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Поиск по документации"""
        if not self.chunks:
            print(f"[DEBUG ProjectDocsRAG] No chunks loaded")
            return []
        
        query_words = set(query.lower().split())
        print(f"[DEBUG ProjectDocsRAG] Searching for: '{query}'")
        print(f"[DEBUG ProjectDocsRAG] Query words: {query_words}")
        print(f"[DEBUG ProjectDocsRAG] Total chunks: {len(self.chunks)}")
        
        scored = []
        
        for chunk in self.chunks:
            text = chunk.get('text', '').lower()
            score = sum(1 for word in query_words if word in text)
            if score > 0:
                scored.append((score, chunk))
        
        print(f"[DEBUG ProjectDocsRAG] Found matches: {len(scored)}")
        scores = [f"{filename}: {score}" for score, filename in [(s, c['filename']) for s, c in scored]]
        if scores:
            print(f"[DEBUG ProjectDocsRAG] Scores: {scores}")
        
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [{'text': c['text'], 'filename': c['filename'], 'score': s} 
                   for s, c in scored[:top_k]]
        print(f"[DEBUG ProjectDocsRAG] Returning {len(results)} results")
        return results