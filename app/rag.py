#!/usr/bin/env python3
# app/rag.py
import os
import sqlite3
import numpy as np
from typing import List, Dict, Optional

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
        
        # Загружаем чанки из SQLite
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
            print("⚠️ FAISS не установлен, использую поиск по ключевым словам")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки FAISS: {e}")
        
        # Пробуем загрузить модель эмбеддингов
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print(f"✅ Модель эмбеддингов загружена")
        except ImportError:
            print("⚠️ sentence-transformers не установлен")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки модели: {e}")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Поиск релевантных чанков"""
        if not self.chunks:
            return []
        
        # Если есть эмбеддинги и FAISS — используем
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
        
        # Fallback: поиск по ключевым словам
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