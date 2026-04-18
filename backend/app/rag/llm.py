"""
Groq LLM — language model for RAG answer generation.

Uses Groq API with llama-3.1-8b-versatile model.
Fast inference with multilingual capabilities.
"""

import logging
from typing import List, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)


class GroqLLM:
    """
    Language model interface to Groq API.
    
    Uses llama-3.1-8b-versatile model for fast, accurate responses.
    """
    
    def __init__(
        self,
        api_key: str = settings.GROQ_API_KEY,
        model: str = settings.GROQ_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ):
        """
        Initialize Groq LLM.
        
        Parameters
        ----------
        api_key : str
            Groq API key
        model : str
            Model name (default: llama-3.1-8b-versatile)
        temperature : float
            Temperature for generation (0.0 = deterministic, 1.0 = creative)
        max_tokens : int
            Maximum tokens in response
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
    
    async def generate(
        self,
        prompt: str,
        language: str = "en",
    ) -> str:
        """
        Generate answer using Groq LLM.
        
        Parameters
        ----------
        prompt : str
            Full prompt with context and query
        language : str
            Language code for response
        
        Returns
        -------
        str
            Generated answer text
        
        Raises
        ------
        ExternalServiceError
            If API call fails
        ValueError
            If API key not configured
        """
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured")
        
        if not prompt or not prompt.strip():
            raise ValueError("prompt cannot be empty")
        
        try:
            logger.debug("Calling Groq LLM | model=%s | tokens=%d", self.model, self.max_tokens)
            
            response = await self._call_api(prompt, language)
            
            logger.info("Groq generation success | length=%d", len(response))
            return response
        
        except Exception as e:
            logger.exception("Groq LLM generation failed")
            raise ExternalServiceError(f"Groq LLM failed: {e}") from e
    
    async def _call_api(self, prompt: str, language: str) -> str:
        """Call Groq API."""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._build_system_prompt(language),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            
            # Extract text from response
            return data["choices"][0]["message"]["content"].strip()
        
        except httpx.HTTPError as e:
            logger.exception("Groq API HTTP error")
            raise ExternalServiceError(f"Groq API error: {e}") from e
        except (KeyError, IndexError) as e:
            logger.exception("Unexpected Groq response format")
            raise ExternalServiceError(f"Unexpected response format: {e}") from e
    
    @staticmethod
    def _build_system_prompt(language: str) -> str:
        """Build system prompt for the LLM."""
        lang_name = {
            "en": "English",
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "mr": "Marathi",
            "bn": "Bengali",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "pa": "Punjabi",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "zh": "Chinese",
            "ar": "Arabic",
            "pt": "Portuguese",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
        }.get(language, "English")
        
        return (
            f"You are a helpful agricultural expert RAG assistant. "
            f"Answer ONLY based on the provided context. "
            f"If the answer is not in the context, say 'I don't have information about this in the provided documents.' "
            f"Always respond in {lang_name}. "
            f"Be concise, practical, and suitable for farmers. "
            f"Do not hallucinate or make up information."
        )


def get_groq_llm(
    api_key: str = settings.GROQ_API_KEY,
    model: str = settings.GROQ_MODEL,
) -> GroqLLM:
    """Get Groq LLM instance."""
    return GroqLLM(api_key=api_key, model=model)
