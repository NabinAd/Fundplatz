"""Austauschbare LLM-Schnittstelle für Ollamas lokale Chat-API.

Dieses Modul enthält bewusst keine Marketplace-, Router- oder Agentenlogik.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMConnectionError(RuntimeError):
    """Die lokale Modellanbindung ist nicht erreichbar oder liefert keine Antwort."""


class OllamaClient:
    def __init__(
        self,
        model: str | None = None,
        base_url: str = "http://127.0.0.1:11434",
        timeout: int | None = None,
    ) -> None:
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")
        self.base_url = base_url.rstrip("/")
        # Zeitlimit pro HTTP-Aufruf; kein Gesamtzeitlimit der Pipeline.
        # Im Worker beispielsweise OLLAMA_TIMEOUT_SECONDS=45 setzen.
        if timeout is None:
            raw = os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120")
            try:
                timeout = int(raw)
            except ValueError as exc:
                raise ValueError("OLLAMA_TIMEOUT_SECONDS muss eine ganze Zahl sein.") from exc
        if not 5 <= timeout <= 300:
            raise ValueError("Ollama-Timeout muss zwischen 5 und 300 Sekunden liegen.")
        self.timeout = timeout

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | str | None = None,
    ) -> str:
        """Sendet System-/Nutzertext an Ollama und gibt die fertige Antwort zurück."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0,
                "num_ctx": 2048,
                "num_predict": 180,
            },
        }
        if response_format is not None:
            # Unterstützt Ollamas `format`: `json` oder ein JSON-Schema.
            payload["format"] = response_format
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except HTTPError as exc:
            raise LLMConnectionError(
                f"Ollama meldet HTTP {exc.code}. Prüfe Modellname und Ollama-Logs."
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise LLMConnectionError(
                "Ollama ist nicht erreichbar oder die Anfrage hat zu lange gedauert. "
                "Prüfe, ob Ollama unter http://127.0.0.1:11434 läuft."
            ) from exc
        except (ValueError, UnicodeError) as exc:
            raise LLMConnectionError("Ollama hat ungültiges JSON zurückgegeben.") from exc

        try:
            content = result["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMConnectionError("Ollama-Antwort enthält kein message.content.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMConnectionError("Ollama hat einen leeren Antworttext geliefert.")
        return content.strip()
