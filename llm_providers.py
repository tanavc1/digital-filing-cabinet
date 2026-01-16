"""
LLM Providers Module
====================

Provider-agnostic LLM interface that supports:
1. OpenAI API (cloud)
2. Ollama (local)

Allows seamless switching between cloud and local LLMs via environment variable.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, List, Dict, Any

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def complete(
        self, 
        prompt: str, 
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """Generate a completion for the given prompt."""
        pass
    
    @abstractmethod
    async def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Generate a JSON completion."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        pass


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider.
    Uses the standard OpenAI Python SDK.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info(f"OpenAI provider initialized with model: {self._model}")
    
    @property
    def model_name(self) -> str:
        return self._model
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        resp = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()
    
    async def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        resp = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)
    
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        stream = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider.
    Connects to Ollama server running on localhost.
    """
    
    def __init__(
        self, 
        host: Optional[str] = None, 
        model: Optional[str] = None,
        timeout: float = 120.0
    ):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._model = model or os.getenv("OLLAMA_MODEL", "phi4-mini")
        self.timeout = timeout
        
        logger.info(f"Ollama provider initialized: {self.host} with model: {self._model}")
    
    @property
    def model_name(self) -> str:
        return self._model
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            if system:
                payload["system"] = system
            
            try:
                resp = await client.post(
                    f"{self.host}/api/generate",
                    json=payload
                )
                resp.raise_for_status()
                return resp.json()["response"].strip()
            except httpx.HTTPError as e:
                logger.error(f"Ollama request failed: {e}")
                raise RuntimeError(f"Ollama API error: {e}")
    
    async def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        # Ollama doesn't have native JSON mode, so we instruct + parse
        json_system = (system or "") + "\n\nYou MUST respond with valid JSON only. No other text."
        
        raw = await self.complete(
            prompt=prompt,
            system=json_system,
            temperature=temperature
        )
        
        # Clean up common JSON wrapper issues
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        
        return json.loads(raw.strip())
    
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature
                }
            }
            if system:
                payload["system"] = system
            
            async with client.stream(
                "POST",
                f"{self.host}/api/generate",
                json=payload
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue


def is_offline_mode() -> bool:
    """Check if the system is running in offline mode."""
    return os.getenv("OFFLINE_MODE", "false").lower() in ("true", "1", "yes")


def get_llm_provider(
    provider_type: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    Factory function to create an LLM provider.
    
    In OFFLINE_MODE, always uses Ollama regardless of provider_type.
    
    Args:
        provider_type: "openai" or "ollama" (defaults to LLM_PROVIDER env var)
        **kwargs: Provider-specific arguments
        
    Returns:
        LLMProvider instance
    """
    # OFFLINE_MODE enforces local Ollama
    if is_offline_mode():
        logger.info("OFFLINE_MODE enabled - using local Ollama")
        return OllamaProvider(**kwargs)
    
    provider_type = provider_type or os.getenv("LLM_PROVIDER", "openai")
    provider_type = provider_type.lower().strip()
    
    if provider_type == "ollama":
        return OllamaProvider(**kwargs)
    elif provider_type == "openai":
        return OpenAIProvider(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}. Use 'openai' or 'ollama'.")



async def check_ollama_available() -> bool:
    """Check if Ollama server is running and accessible."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{host}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def list_ollama_models() -> List[str]:
    """List available models in Ollama."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{host}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m["name"] for m in models]
    except Exception as e:
        logger.warning(f"Failed to list Ollama models: {e}")
    return []
