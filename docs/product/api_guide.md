# Руководство по API

## Общая информация

### Базовый URL
```
https://api.example.com/v1
```

### Аутентификация
Используйте API ключ в заголовке:
```
Authorization: Bearer YOUR_API_KEY
```

## Основные эндпоинты

### Получение данных пользователя
```
GET /users/{user_id}
```

**Параметры:**
- `user_id` - ID пользователя

**Ответ:**
```json
{
  "id": "123",
  "name": "Иван Иванов",
  "email": "ivan@example.com",
  "subscription_plan": "pro",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Создание проекта
```
POST /projects
```

**Тело запроса:**
```json
{
  "name": "Мой проект",
  "description": "Описание проекта",
  "settings": {
    "visibility": "private"
  }
}
```

## Ограничения

### Rate limiting
- Бесплатный тариф: 100 запросов/час
- Про тариф: 1000 запросов/час
- Бизнес тариф: 10000 запросов/час

### Коды ошибок
- 400: Неверный запрос
- 401: Неавторизован
- 403: Доступ запрещен
- 404: Не найдено
- 429: Слишком много запросов
- 500: Внутренняя ошибка сервера

## Примеры использования

### Python
```python
import requests

headers = {"Authorization": "Bearer YOUR_API_KEY"}
response = requests.get("https://api.example.com/v1/users/me", headers=headers)
print(response.json())
```

### JavaScript
```javascript
fetch('https://api.example.com/v1/users/me', {
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```
