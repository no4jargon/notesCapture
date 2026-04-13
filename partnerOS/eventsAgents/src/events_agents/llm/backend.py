from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any


class OpenAIChatBackend:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout_seconds: int = 60):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        self.timeout_seconds = timeout_seconds

    def available(self) -> bool:
        return bool(self.api_key)

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("OpenAI response content was not a string")
        return json.loads(content)


def load_prompt(relative_name: str) -> str:
    return (Path(__file__).resolve().parent / "prompts" / relative_name).read_text(encoding="utf-8")


def default_backend() -> OpenAIChatBackend:
    return OpenAIChatBackend()
