#!/usr/bin/env python3
"""
Модуль Support RAG для поддержки пользователей.
Расширяет существующий RAG для работы с FAQ, документацией продукта и контекстом пользователя.
"""

import os
import sqlite3
import json
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.crm import CRMManager, crm_manager


class SupportRAG:
    """RAG система для поддержки пользователей"""
    
    def __init__(self, 
                 faq_path: str = "data/faq",
                 docs_path: str = "docs/product",
                 db_path: str = "data/support_rag.db"):
        self.faq_path = faq_path
        self.docs_path = docs_path
        self.db_path = db_path
        self.crm_manager = crm_manager
        
        # Создаём директории если их нет
        os.makedirs(faq_path, exist_ok=True)
        os.makedirs(docs_path, exist_ok=True)
        
        self.chunks = []
        self._load_or_index()
    
    def _load_or_index(self):
        """Загружает существующий индекс или создаёт новый"""
        if os.path.exists(self.db_path):
            self._load_from_db()
        else:
            self._index_support_docs()
    
    def _load_from_db(self):
        """Загружает чанки из SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, source_type, source_name, metadata 
                FROM support_chunks
            """)
            
            for row in cursor.fetchall():
                self.chunks.append({
                    'id': row[0],
                    'text': row[1],
                    'source_type': row[2],  # 'faq', 'docs', 'ticket_history'
                    'source_name': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {}
                })
            
            conn.close()
            print(f"✅ Загружено {len(self.chunks)} чанков поддержки из {self.db_path}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки БД поддержки: {e}")
            self._index_support_docs()
    
    def _index_support_docs(self):
        """Индексирует FAQ и документацию продукта"""
        self.chunks = []
        
        # Индексация FAQ
        self._index_faq()
        
        # Индексация документации продукта
        self._index_product_docs()
        
        # Сохраняем в БД
        self._save_to_db()
    
    def _index_faq(self):
        """Индексирует FAQ файлы"""
        if not os.path.exists(self.faq_path):
            print(f"⚠️ Папка FAQ {self.faq_path} не найдена")
            return
        
        # Создаём пример FAQ если нет файлов
        if not os.listdir(self.faq_path):
            self._create_sample_faq()
        
        for filename in os.listdir(self.faq_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.faq_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        faq_data = json.load(f)
                    
                    for item in faq_data:
                        question = item.get('question', '')
                        answer = item.get('answer', '')
                        tags = item.get('tags', [])
                        
                        # Создаём чанк из вопроса и ответа
                        chunk_text = f"Вопрос: {question}\nОтвет: {answer}"
                        
                        self.chunks.append({
                            'id': f"faq_{len(self.chunks)}",
                            'text': chunk_text,
                            'source_type': 'faq',
                            'source_name': filename,
                            'metadata': {
                                'question': question,
                                'tags': tags,
                                'source': 'faq'
                            }
                        })
                        
                        # Также добавляем отдельно вопрос для лучшего поиска
                        self.chunks.append({
                            'id': f"faq_q_{len(self.chunks)}",
                            'text': question,
                            'source_type': 'faq',
                            'source_name': filename,
                            'metadata': {
                                'type': 'question_only',
                                'tags': tags,
                                'source': 'faq'
                            }
                        })
                
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки FAQ файла {filename}: {e}")
    
    def _create_sample_faq(self):
        """Создаёт пример FAQ файла"""
        sample_faq = [
            {
                "question": "Почему не работает авторизация?",
                "answer": "Проверьте: 1) Правильность логина/пароля 2) Подключение к интернету 3) Статус сервера в статусной панели. Если проблема persists, сбросьте пароль через 'Забыли пароль?'",
                "tags": ["авторизация", "логин", "пароль", "ошибка"]
            },
            {
                "question": "Как восстановить доступ к аккаунту?",
                "answer": "Используйте функцию 'Забыли пароль?' на странице входа. Вам придёт письмо со ссылкой для сброса. Если не получаете письмо, проверьте папку 'Спам'.",
                "tags": ["восстановление", "пароль", "аккаунт", "доступ"]
            },
            {
                "question": "Как обновить тарифный план?",
                "answer": "Зайдите в Настройки → Подписка → Выберите новый тариф → Оплатите. Изменения вступят в силу после успешной оплаты.",
                "tags": ["тариф", "подписка", "оплата", "обновление"]
            },
            {
                "question": "Почему медленно работает приложение?",
                "answer": "Возможные причины: 1) Медленный интернет 2) Высокая нагрузка на сервер 3) Устаревшая версия приложения. Попробуйте: обновить приложение, очистить кэш, перезагрузить устройство.",
                "tags": ["производительность", "скорость", "оптимизация"]
            }
        ]
        
        faq_file = os.path.join(self.faq_path, "general_faq.json")
        with open(faq_file, 'w', encoding='utf-8') as f:
            json.dump(sample_faq, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Создан пример FAQ файла: {faq_file}")
    
    def _index_product_docs(self):
        """Индексирует документацию продукта"""
        if not os.path.exists(self.docs_path):
            print(f"⚠️ Папка документации продукта {self.docs_path} не найдена")
            return
        
        # Создаём пример документации если нет файлов
        if not os.listdir(self.docs_path):
            self._create_sample_docs()
        
        for filename in os.listdir(self.docs_path):
            if filename.endswith('.md'):
                filepath = os.path.join(self.docs_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Разбиваем на чанки по разделам
                    sections = content.split('\n## ')
                    for i, section in enumerate(sections):
                        if not section.strip():
                            continue
                        
                        # Первый раздел может не иметь заголовка ##
                        if i == 0:
                            lines = section.strip().split('\n')
                            if lines:
                                title = lines[0].replace('# ', '')
                                text = '\n'.join(lines[1:]) if len(lines) > 1 else ''
                            else:
                                continue
                        else:
                            lines = section.strip().split('\n')
                            if lines:
                                title = lines[0]
                                text = '\n'.join(lines[1:]) if len(lines) > 1 else ''
                            else:
                                continue
                        
                        chunk_text = f"Раздел: {title}\n{text}"
                        
                        self.chunks.append({
                            'id': f"docs_{len(self.chunks)}",
                            'text': chunk_text[:1000],  # Ограничиваем длину
                            'source_type': 'docs',
                            'source_name': filename,
                            'metadata': {
                                'title': title,
                                'filename': filename,
                                'source': 'product_docs'
                            }
                        })
                
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки документации {filename}: {e}")
    
    def _create_sample_docs(self):
        """Создаёт пример документации продукта"""
        sample_docs = """# Руководство пользователя

## Авторизация и безопасность

### Вход в систему
Для входа используйте email и пароль, указанные при регистрации.

### Восстановление пароля
Если забыли пароль, нажмите "Забыли пароль?" на странице входа.

### Двухфакторная аутентификация
Доступна в настройках безопасности для премиум-аккаунтов.

## Основные функции

### Управление проектами
Создавайте, редактируйте и удаляйте проекты через интерфейс.

### Совместная работа
Приглашайте коллег к проектам и назначайте роли.

### Экспорт данных
Данные можно экспортировать в CSV, JSON и PDF форматах.

## Подписка и тарифы

### Бесплатный тариф
Включает: 3 проекта, 1GB хранилища, базовую поддержку.

### Про тариф
Включает: 10 проектов, 10GB хранилища, приоритетную поддержку.

### Бизнес тариф
Включает: неограниченные проекты, 100GB хранилища, 24/7 поддержку.

## Техническая поддержка

### Часы работы
Поддержка доступна с 9:00 до 18:00 по московскому времени.

### Способы связи
Email: support@example.com
Телефон: +7 (XXX) XXX-XX-XX
Чат в приложении

### Время ответа
Бесплатный тариф: до 48 часов
Про тариф: до 24 часов
Бизнес тариф: до 4 часов"""
        
        docs_file = os.path.join(self.docs_path, "user_guide.md")
        with open(docs_file, 'w', encoding='utf-8') as f:
            f.write(sample_docs)
        
        print(f"✅ Создана пример документации: {docs_file}")
    
    def _save_to_db(self):
        """Сохраняет чанки в БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаём таблицу если её нет
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS support_chunks (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Очищаем старые данные
            cursor.execute("DELETE FROM support_chunks")
            
            # Вставляем новые данные
            for chunk in self.chunks:
                metadata_json = json.dumps(chunk['metadata'], ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO support_chunks (id, text, source_type, source_name, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    chunk['id'],
                    chunk['text'],
                    chunk['source_type'],
                    chunk['source_name'],
                    metadata_json
                ))
            
            conn.commit()
            conn.close()
            print(f"✅ Сохранено {len(self.chunks)} чанков поддержки в {self.db_path}")
        
        except Exception as e:
            print(f"⚠️ Ошибка сохранения в БД: {e}")
    
    def search(self, query: str, user_id: Optional[str] = None, 
               ticket_id: Optional[str] = None, top_k: int = 5) -> List[Dict]:
        """Поиск по поддержке с учётом контекста пользователя"""
        if not self.chunks:
            return []
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_chunks = []
        
        for chunk in self.chunks:
            text = chunk.get('text', '').lower()
            metadata = chunk.get('metadata', {})
            source_type = chunk.get('source_type', '')
            
            # Базовый скоринг по ключевым словам
            score = sum(1 for word in query_words if word in text)
            
            # Увеличиваем вес для FAQ если запрос похож на вопрос
            if source_type == 'faq' and any(word in query_lower for word in ['почему', 'как', 'что', 'где', 'когда']):
                score += 2
            
            # Учитываем теги в FAQ
            tags = metadata.get('tags', [])
            tag_matches = sum(1 for tag in tags if any(tag_word in query_lower for tag_word in tag.lower().split()))
            score += tag_matches
            
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Сортируем по score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Получаем контекст пользователя если указан user_id
        user_context = ""
        if user_id:
            user_context_data = self.crm_manager.get_user_context(user_id)
            if user_context_data:
                user_context = f"\nКонтекст пользователя: {json.dumps(user_context_data, ensure_ascii=False, indent=2)}"
        
        # Получаем контекст тикета если указан ticket_id
        ticket_context = ""
        if ticket_id:
            ticket_context_data = self.crm_manager.get_ticket_context(ticket_id)
            if ticket_context_data:
                ticket_context = f"\nКонтекст тикета: {json.dumps(ticket_context_data, ensure_ascii=False, indent=2)}"
        
        # Формируем результаты с контекстом
        results = []
        for score, chunk in scored_chunks[:top_k]:
            result = {
                'text': chunk['text'],
                'source_type': chunk['source_type'],
                'source_name': chunk['source_name'],
                'metadata': chunk['metadata'],
                'score': score
            }
            
            # Добавляем контекст если есть
            if user_context:
                result['user_context'] = user_context
            if ticket_context:
                result['ticket_context'] = ticket_context
            
            results.append(result)
        
        return results
    
    def get_context_for_prompt(self, query: str, user_id: Optional[str] = None,
                               ticket_id: Optional[str] = None) -> str:
        """Получить контекст для включения в промпт"""
        search_results = self.search(query, user_id, ticket_id, top_k=3)
        
        if not search_results:
            return ""
        
        context_parts = ["📚 Релевантная информация из базы знаний:"]
        
        for i, result in enumerate(search_results, 1):
            source_type = result['source_type']
            source_name = result['source_name']
            text = result['text'][:500]  # Ограничиваем длину
            
            if source_type == 'faq':
                context_parts.append(f"{i}. [FAQ/{source_name}] {text}")
            elif source_type == 'docs':
                context_parts.append(f"{i}. [Документация/{source_name}] {text}")
            else:
                context_parts.append(f"{i}. [{source_type}/{source_name}] {text}")
        
        # Добавляем контекст пользователя если есть
        if user_id:
            user_context = self.crm_manager.get_user_context(user_id)
            if user_context:
                context_parts.append("\n👤 Контекст пользователя:")
                context_parts.append(f"Имя: {user_context['user']['name']}")
                context_parts.append(f"Email: {user_context['user']['email']}")
                context_parts.append(f"Тариф: {user_context['user']['subscription_plan']}")
                
                if user_context['recent_tickets']:
                    context_parts.append("\nНедавние тикеты:")
                    for ticket in user_context['recent_tickets'][:3]:
                        context_parts.append(f"- {ticket['title']} ({ticket['status']})")
        
        # Добавляем контекст тикета если есть
        if ticket_id:
            ticket_context = self.crm_manager.get_ticket_context(ticket_id)
            if ticket_context:
                context_parts.append("\n🎫 Контекст тикета:")
                context_parts.append(f"Заголовок: {ticket_context['ticket']['title']}")
                context_parts.append(f"Описание: {ticket_context['ticket']['description'][:200]}...")
                context_parts.append(f"Статус: {ticket_context['ticket']['status']}")
                context_parts.append(f"Приоритет: {ticket_context['ticket']['priority']}")
        
        return "\n".join(context_parts)


# Глобальный экземпляр Support RAG
support_rag = SupportRAG()
