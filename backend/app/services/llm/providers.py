import json
import time
import requests
from typing import Generator, Union
from google import genai

from app.core.config import settings
from app.core.logging import logger
from app.services.llm.interfaces import LLMProvider

class OllamaClient(LLMProvider):
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

    def generate(self, prompt: str, system_prompt: str = None, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        system_prompt = system_prompt or settings.system_prompt
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": stream,
        }

        try:
            if stream:
                return self._generate_stream(url, payload)
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.ConnectionError:
            return (
                "❌ Could not connect to Ollama. "
                "Please make sure Ollama is running (`ollama serve`) "
                f"and accessible at {self.base_url}"
            )
        except requests.Timeout:
            return "⏱️ Ollama request timed out. The model may be loading — please try again."
        except Exception as e:
            return f"❌ Ollama error: {str(e)}"

    def _generate_stream(self, url: str, payload: dict) -> Generator[str, None, None]:
        try:
            with requests.post(url, json=payload, timeout=120, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
        except Exception as e:
            yield f"\n[Error streaming from Ollama: {str(e)}]"

    def get_health_status(self) -> dict:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            available_names = [m.get("name", "") for m in models]
            
            model_found = any(self.model in name for name in available_names)
            
            if not model_found:
                model_found = any(name.split(':')[0] == self.model.split(':')[0] for name in available_names)

            return {
                "online": True,
                "model_found": model_found,
                "model_name": self.model,
                "available": available_names,
                "error": None
            }
        except requests.ConnectionError:
            return {"online": False, "model_found": False, "model_name": self.model, "error": "ConnectionError"}
        except Exception as e:
            return {"online": False, "model_found": False, "model_name": self.model, "error": str(e)}

    def is_available(self) -> bool:
        status = self.get_health_status()
        return status["online"] and status["model_found"]


class GeminiClient(LLMProvider):
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.last_request_time = 0
        self.cooldown = settings.gemini_cooldown
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str = None, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        if not self.client:
            return "❌ GEMINI_API_KEY is not set or client failed to initialize."
        
        system_prompt = system_prompt or settings.system_prompt
        
        elapsed = time.time() - self.last_request_time
        if elapsed < self.cooldown:
            logger.info(f"Gemini cooldown active. Sleeping for {self.cooldown - elapsed:.2f}s")
            time.sleep(self.cooldown - elapsed)
        
        self.last_request_time = time.time()

        gemini_config = {"system_instruction": system_prompt}

        try:
            if stream:
                logger.info(f"Gemini generating stream (model={settings.gemini_model})...")
                return self._generate_stream(prompt, gemini_config)
            
            logger.info(f"Gemini generating content (model={settings.gemini_model})...")
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=gemini_config
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini (GenAI) error: {str(e)}")
            return f"❌ Gemini (GenAI) error: {str(e)}"

    def _generate_stream(self, prompt: str, gemini_config: dict) -> Generator[str, None, None]:
        token_count = 0
        try:
            for chunk in self.client.models.generate_content_stream(
                model=settings.gemini_model,
                contents=prompt,
                config=gemini_config
            ):
                if chunk.text:
                    token_count += 1
                    yield chunk.text
            logger.info(f"Gemini stream completed. Sent {token_count} chunks.")
        except Exception as e:
            logger.error(f"Gemini streaming error: {str(e)}")
            yield f"\n[Error streaming from Gemini (GenAI): {str(e)}]"
            
    def get_health_status(self) -> dict:
        is_ready = bool(self.client)
        return {
            "online": is_ready,
            "model_found": is_ready,
            "model_name": settings.gemini_model,
            "error": None if is_ready else "GEMINI_API_KEY not configured"
        }

    def is_available(self) -> bool:
        return bool(self.client)
