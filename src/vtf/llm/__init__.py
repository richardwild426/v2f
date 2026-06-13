"""LLM integration module for direct API calls."""
from __future__ import annotations

from typing import Any, Protocol
from pathlib import Path


class LlmProvider(Protocol):
    """Protocol for LLM providers."""
    
    def generate(self, image_path: Path, prompt: str, **kwargs: Any) -> str:
        """Generate a response from an image and prompt."""
        ...


class OpenAIProvider:
    """OpenAI vision model provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-vision-preview", base_url: str = "", max_tokens: int = 300):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self.max_tokens = max_tokens
    
    def generate(self, image_path: Path, prompt: str, **kwargs: Any) -> str:
        """Generate description using OpenAI vision API."""
        import base64
        import httpx
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": self.max_tokens,
        }
        
        # Make request
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


class AnthropicProvider:
    """Anthropic Claude vision model provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229", max_tokens: int = 300):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
    
    def generate(self, image_path: Path, prompt: str, **kwargs: Any) -> str:
        """Generate description using Anthropic Claude API."""
        import base64
        import httpx
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Prepare request
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        
        # Make request
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        
        result = response.json()
        return result["content"][0]["text"]


def create_llm_provider(
    provider: str,
    api_key: str,
    model: str = "",
    base_url: str = "",
    max_tokens: int = 300,
) -> LlmProvider:
    """Create an LLM provider instance.
    
    Args:
        provider: Provider name (openai, anthropic)
        api_key: API key
        model: Model name (optional, uses defaults)
        base_url: Custom base URL (optional)
        max_tokens: Maximum tokens for response
    
    Returns:
        LlmProvider instance
    
    Raises:
        ValueError: If provider is not supported
    """
    if provider == "openai":
        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-4-vision-preview",
            base_url=base_url,
            max_tokens=max_tokens,
        )
    elif provider == "anthropic":
        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-3-opus-20240229",
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


__all__ = ["LlmProvider", "OpenAIProvider", "AnthropicProvider", "create_llm_provider"]
