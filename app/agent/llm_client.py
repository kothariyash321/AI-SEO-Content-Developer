"""LLM client wrapper for OpenAI."""
import json
import asyncio
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings


class LLMClient:
    """Client for interacting with OpenAI API."""
    
    def __init__(self):
        # Bypass host proxy environment variables for OpenAI calls.
        # Local proxy processes can return 403 and surface as APIConnectionError.
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=httpx.AsyncClient(trust_env=False, timeout=60.0),
        )
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: type[BaseModel] | None = None,
        max_retries: int = 3,
    ) -> str | BaseModel:
        """
        Generate a response from the LLM.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            response_format: Optional Pydantic model to parse response into
            max_retries: Maximum number of retries on failure
        
        Returns:
            Raw string response or parsed Pydantic model
        """
        for attempt in range(max_retries):
            try:
                response = await self._call_api(system_prompt, user_prompt)
                
                if response_format:
                    return self._parse_json_response(response, response_format)
                return response
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
                continue
    
    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Make API call to OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        
        # Extract text from response
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        raise ValueError("Empty response from LLM")
    
    def _parse_json_response(self, response: str, model: type[BaseModel]) -> BaseModel:
        """Parse JSON response into Pydantic model."""
        # Try to extract JSON from response (might be wrapped in markdown)
        text = response.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            data = json.loads(text)
            return model(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            # Try to find JSON object in the text
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return model(**data)
                except (json.JSONDecodeError, ValidationError):
                    pass
            
            raise ValueError(f"Failed to parse LLM response as {model.__name__}: {e}")
