import abc
import asyncio
import os

from google import genai
from google.genai import types


class LLMClient(abc.ABC):
    """Abstract interface for an async text-generation client."""

    @abc.abstractmethod
    async def generate(self, prompt: str, system_prompt: str) -> str:
        raise NotImplementedError


class GeminiClient(LLMClient):
    """LLMClient backed by Google Gemini via the google-genai SDK."""
    # UPGRADED TO THE ACTIVE 2026 PRODUCTION ENDPOINT
    MODEL = "gemini-2.5-flash"

    def __init__(self):
        api_key = os.environ["GEMINI_API_KEY"]
        self.client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str, system_prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        return response.text


class LocalOpenVINOClient(LLMClient):
    """Mock local client. Stands in for a future OpenVINO-backed model."""

    async def generate(self, prompt: str, system_prompt: str) -> str:
        await asyncio.sleep(1)
        return "MOCK_LOCAL_RESPONSE"
