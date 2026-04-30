#!/usr/bin/env python3
"""
Модуль CRM для работы с данными пользователей и тикетов.
Поддерживает JSON файлы и потенциальную интеграцию с внешними CRM через MCP.
"""

import os
import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class TicketStatus(str, Enum):
    """Статусы тикетов поддержки"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    """Приоритеты тикетов"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class User:
    """Модель пользователя"""
    id: str
    name: str
    email: str
    subscription_plan: str = "free"
    created_at: str = None
    last_contact_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.last_contact_at is None:
            self.last_contact_at = datetime.now().isoformat()


@dataclass
class Ticket:
    """Модель тикета поддержки"""
    id: str
    user_id: str
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM
    created_at: str = None
    updated_at: str = None
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


@dataclass
class SupportHistory:
    """История обращений пользователя"""
    id: str
    user_id: str
    ticket_id: Optional[str] = None
    question: str = ""
    answer: str = ""
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class CRMProvider:
    """Абстрактный класс провайдера CRM"""
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        raise NotImplementedError
    
    def get_user_tickets(self, user_id: str, limit: int = 10) -> List[Ticket]:
        """Получить тикеты пользователя"""
        raise NotImplementedError
    
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Получить тикет по ID"""
        raise NotImplementedError
    
    def add_support_history(self, history: SupportHistory) -> bool:
        """Добавить запись в историю поддержки"""
        raise NotImplementedError
    
    def search_users(self, query: str) -> List[User]:
        """Поиск пользователей"""
        raise NotImplementedError


class JSONCRMProvider(CRMProvider):
    """CRM провайдер на основе JSON файлов"""
    
    def __init__(self, data_dir: str = "data/crm"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Инициализация файлов если их нет
        self._init_json_file("users.json", [])
        self._init_json_file("tickets.json", [])
        self._init_json_file("support_history.json", [])
    
    def _init_json_file(self, filename: str, default_data: Any):
        """Инициализировать JSON файл если его нет"""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
    
    def _read_json(self, filename: str) -> Any:
        """Прочитать JSON файл"""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_json(self, filename: str, data: Any):
        """Записать JSON файл"""
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user(self, user_id: str) -> Optional[User]:
        users_data = self._read_json("users.json")
        for user_data in users_data:
            if user_data.get("id") == user_id:
                return User(**user_data)
        return None
    
    def get_user_tickets(self, user_id: str, limit: int = 10) -> List[Ticket]:
        tickets_data = self._read_json("tickets.json")
        user_tickets = []
        
        for ticket_data in tickets_data:
            if ticket_data.get("user_id") == user_id:
                # Конвертируем строковые статусы в enum
                ticket_data["status"] = TicketStatus(ticket_data["status"])
                ticket_data["priority"] = TicketPriority(ticket_data["priority"])
                user_tickets.append(Ticket(**ticket_data))
        
        return sorted(user_tickets, key=lambda x: x.created_at, reverse=True)[:limit]
    
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        tickets_data = self._read_json("tickets.json")
        for ticket_data in tickets_data:
            if ticket_data.get("id") == ticket_id:
                ticket_data["status"] = TicketStatus(ticket_data["status"])
                ticket_data["priority"] = TicketPriority(ticket_data["priority"])
                return Ticket(**ticket_data)
        return None
    
    def add_support_history(self, history: SupportHistory) -> bool:
        try:
            history_data = self._read_json("support_history.json")
            history_dict = asdict(history)
            history_data.append(history_dict)
            self._write_json("support_history.json", history_data)
            return True
        except Exception as e:
            print(f"Ошибка при добавлении истории: {e}")
            return False
    
    def search_users(self, query: str) -> List[User]:
        users_data = self._read_json("users.json")
        results = []
        query_lower = query.lower()
        
        for user_data in users_data:
            if (query_lower in user_data.get("name", "").lower() or
                query_lower in user_data.get("email", "").lower()):
                results.append(User(**user_data))
        
        return results


class SQLiteCRMProvider(CRMProvider):
    """CRM провайдер на основе SQLite"""
    
    def __init__(self, db_path: str = "data/support.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализировать базу данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subscription_plan TEXT DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_contact_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица тикетов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_to TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Таблица истории поддержки
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                ticket_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0],
                name=row[1],
                email=row[2],
                subscription_plan=row[3],
                created_at=row[4],
                last_contact_at=row[5]
            )
        return None
    
    def get_user_tickets(self, user_id: str, limit: int = 10) -> List[Ticket]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        tickets = []
        for row in rows:
            tickets.append(Ticket(
                id=row[0],
                user_id=row[1],
                title=row[2],
                description=row[3],
                status=TicketStatus(row[4]),
                priority=TicketPriority(row[5]),
                created_at=row[6],
                updated_at=row[7],
                assigned_to=row[8]
            ))
        
        return tickets
    
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Ticket(
                id=row[0],
                user_id=row[1],
                title=row[2],
                description=row[3],
                status=TicketStatus(row[4]),
                priority=TicketPriority(row[5]),
                created_at=row[6],
                updated_at=row[7],
                assigned_to=row[8]
            )
        return None
    
    def add_support_history(self, history: SupportHistory) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO support_history (id, user_id, ticket_id, question, answer, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                history.id,
                history.user_id,
                history.ticket_id,
                history.question,
                history.answer,
                history.timestamp
            ))
            
            # Обновляем last_contact_at у пользователя
            cursor.execute(
                "UPDATE users SET last_contact_at = ? WHERE id = ?",
                (history.timestamp, history.user_id)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении истории: {e}")
            return False
    
    def search_users(self, query: str) -> List[User]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users 
            WHERE name LIKE ? OR email LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append(User(
                id=row[0],
                name=row[1],
                email=row[2],
                subscription_plan=row[3],
                created_at=row[4],
                last_contact_at=row[5]
            ))
        
        return users


class CRMManager:
    """Менеджер CRM для работы с разными провайдерами"""
    
    def __init__(self, provider_type: str = "sqlite", **kwargs):
        if provider_type == "sqlite":
            self.provider = SQLiteCRMProvider(**kwargs)
        elif provider_type == "json":
            self.provider = JSONCRMProvider(**kwargs)
        else:
            raise ValueError(f"Неизвестный тип провайдера: {provider_type}")
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Получить контекст пользователя для включения в промпт"""
        user = self.provider.get_user(user_id)
        if not user:
            return {}
        
        tickets = self.provider.get_user_tickets(user_id, limit=5)
        
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "subscription_plan": user.subscription_plan,
                "created_at": user.created_at,
                "last_contact_at": user.last_contact_at
            },
            "recent_tickets": [
                {
                    "id": ticket.id,
                    "title": ticket.title,
                    "status": ticket.status.value,
                    "priority": ticket.priority.value,
                    "created_at": ticket.created_at
                }
                for ticket in tickets
            ]
        }
    
    def get_ticket_context(self, ticket_id: str) -> Dict[str, Any]:
        """Получить контекст тикета"""
        ticket = self.provider.get_ticket(ticket_id)
        if not ticket:
            return {}
        
        user = self.provider.get_user(ticket.user_id)
        
        return {
            "ticket": {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at
            },
            "user": {
                "id": user.id if user else ticket.user_id,
                "name": user.name if user else "Неизвестный пользователь",
                "email": user.email if user else "Нет email"
            }
        }


# Глобальный экземпляр CRM менеджера
crm_manager = CRMManager(provider_type="sqlite", db_path="data/support.db")
