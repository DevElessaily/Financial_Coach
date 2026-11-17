import json
import os

import httpx
from pydantic import BaseModel


class BaseAgent:
    BASE_URL = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    )

    MODEL = os.getenv(
        "OLLAMA_MODEL",
        "qwen2.5:14b"
    )

    def __init__(self) -> None:
        self.timeout = 120.0

    def instructions(self) -> str:
        raise NotImplementedError

    async def generate(
        self,
        response_model: type[BaseModel],
        user_message: str = "",
    ) -> BaseModel:

        payload = {
            "model": self.MODEL,
            "stream": False,
            "format": response_model.model_json_schema(),
            "messages": [
                {
                    "role": "system",
                    "content": self.instructions(),
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/api/chat",
                json=payload,
            )

            response.raise_for_status()

        result = response.json()

        content = result["message"]["content"]

        return response_model.model_validate_json(content)