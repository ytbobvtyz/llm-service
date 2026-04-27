import time
import httpx
from app.config import config
from app.models import ChatRequest

class OllamaClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(self, request: ChatRequest, context: str) -> tuple[str, int]:
        last_message = request.messages[-1].content if request.messages else ""
        
        prompt = f"""{context}

История диалога:
{self._format_history(request.messages[:-1])}

Пользователь: {last_message}

Ассистент:"""
        
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                        "num_ctx": config.context_length
                    }
                }
            )
            data = response.json()
            latency = int((time.time() - start_time) * 1000)
            return data.get("response", ""), latency
        except Exception as e:
            raise Exception(f"Ollama error: {e}")
    
    def _format_history(self, messages) -> str:
        if not messages:
            return "Нет истории"
        history = []
        for msg in messages[-5:]:
            role = "Пользователь" if msg.role == "user" else "Ассистент"
            history.append(f"{role}: {msg.content}")
        return "\n".join(history)