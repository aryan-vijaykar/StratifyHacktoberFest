"""
Ollama client helper used by the AI router.

Keeps the HTTP details in one place so the backend can talk to a local
Ollama daemon without duplicating request formatting across endpoints.
"""

import json
import logging
from typing import Any, Dict, List, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    @staticmethod
    def _chat_url() -> str:
        return f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"

    @staticmethod
    def _tags_url() -> str:
        return f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"

    @staticmethod
    def _build_messages(prompt: str) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are the Core Intelligence System for a small-to-medium enterprise business operating system (SME-OS).\n"
                    "Your role is to advise the business owner with professional, data-driven, and highly structured guidance.\n"
                    "Focus directly on answering the user's specific question. Only address topics and metrics relevant to what is asked.\n"
                    "Always format your response using a structured, professional layout:\n"
                    "- Use sections starting with '###' headers (do not use '#' or '##').\n"
                    "- Present the relevant figures, metrics, or parameters in clean Markdown tables (with columns like Metric, Value, Status/Action) for high readability.\n"
                    "- Include a concise, bulleted list of recommended action items directly addressing the question.\n"
                    "- Use bold markdown (**text**) to highlight key numbers, thresholds, and metrics.\n"
                    "Do NOT output tables, sections, or recommendations for unrelated business areas (e.g. do not show inventory details if the user asked about taxes, and vice-versa)."
                ),
            },
            {"role": "user", "content": prompt},
        ]

    @classmethod
    async def _chat_with_model(cls, prompt: str, model: str) -> str:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": cls._build_messages(prompt),
            "stream": False,
            "options": {
                "temperature": settings.OLLAMA_TEMPERATURE,
            },
        }

        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            response = await client.post(cls._chat_url(), json=payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        return str(data.get("response", "")).strip()

    @classmethod
    async def chat(cls, prompt: str) -> Tuple[str, str]:
        import asyncio
        max_retries = 2
        for attempt in range(max_retries):
            try:
                res = await cls._chat_with_model(prompt, settings.OLLAMA_MODEL)
                return res, settings.OLLAMA_MODEL
            except Exception as exc:
                if attempt < max_retries - 1:
                    logger.warning(
                        "Main Ollama model %s failed (attempt %d/%d): %s. Retrying in 5 seconds...",
                        settings.OLLAMA_MODEL, attempt + 1, max_retries, exc
                    )
                    await asyncio.sleep(5)
                else:
                    logger.warning(
                        "Main Ollama model %s failed after %d attempts: %s. Attempting fallback model %s.",
                        settings.OLLAMA_MODEL, max_retries, exc, settings.OLLAMA_FALLBACK_MODEL
                    )
                    try:
                        res = await cls._chat_with_model(prompt, settings.OLLAMA_FALLBACK_MODEL)
                        return res, settings.OLLAMA_FALLBACK_MODEL
                    except Exception as fallback_exc:
                        logger.error(
                            "Fallback Ollama model %s also failed: %s.",
                            settings.OLLAMA_FALLBACK_MODEL, fallback_exc
                        )
                        raise fallback_exc

    @classmethod
    async def chat_json(cls, prompt: str) -> Dict[str, Any]:
        raw, model_used = await cls.chat(prompt)
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                data["model_used"] = model_used
            return data
        except json.JSONDecodeError:
            return {"raw": raw, "model_used": model_used}

    @classmethod
    async def status(cls) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                response = await client.get(cls._tags_url())
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            return {
                "status": "offline",
                "base_url": settings.OLLAMA_BASE_URL,
                "error": str(exc)
            }

        models = data.get("models", [])
        available_models = []
        for model in models:
            name = model.get("name")
            if isinstance(name, str) and name:
                available_models.append(name)

        configured_model = settings.OLLAMA_MODEL
        fallback_model = settings.OLLAMA_FALLBACK_MODEL

        def is_available(m: str) -> bool:
            if m in available_models:
                return True
            if ":" not in m and f"{m}:latest" in available_models:
                return True
            if m.endswith(":latest") and m[:-7] in available_models:
                return True
            return False

        return {
            "status": "online",
            "base_url": settings.OLLAMA_BASE_URL,
            "configured_model": configured_model,
            "configured_model_available": is_available(configured_model),
            "fallback_model": fallback_model,
            "fallback_model_available": is_available(fallback_model),
            "available_models": available_models,
        }
