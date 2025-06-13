# app/services/llm_connector.py
# Author: Shibo Li & Gemini
# Date: 2025-06-11
# Version: 0.1.0

from openai import OpenAI, APIError
from typing import List, Optional, Dict, Any
from app.core.config import get_settings
from app.models.common import Message
from app.utils.logger import console

settings = get_settings()

_clients = {
    "CHATGPT": OpenAI(
        api_key=settings.CHATGPT_API_KEY,
        base_url=settings.CHATGPT_BASE_URL,
    ),
    "DEEPSEEK_CHAT": OpenAI(
        api_key=settings.DEEPSEEK_CHAT_API_KEY,
        base_url=settings.DEEPSEEK_CHAT_BASE_URL,
    ),
    "DEEPSEEK_REASONER": OpenAI(
        api_key=settings.DEEPSEEK_REASONER_API_KEY,
        base_url=settings.DEEPSEEK_REASONER_BASE_URL,
    ),
    "CLAUDE": OpenAI(
        api_key=settings.CLAUDE_API_KEY,
        base_url=settings.CLAUDE_BASE_URL,
    ),
    "GEMINI": OpenAI(
        api_key=settings.GEMINI_API_KEY,
        base_url=settings.GEMINI_BASE_URL,
    ),
}


_models = {
    "CHATGPT": settings.CHATGPT_MODEL,
    "DEEPSEEK_CHAT": settings.DEEPSEEK_CHAT_MODEL,
    "DEEPSEEK_REASONER": settings.DEEPSEEK_REASONER_MODEL,
    "CLAUDE": settings.CLAUDE_MODEL,
    "GEMINI": settings.GEMINI_MODEL,
}


def get_llm_client_and_model() -> tuple[OpenAI, str]:
    """
    Acts as a factory to get the currently configured LLM client and model name.
    
    This function reads the LLM_PROVIDER from the settings and returns the
    corresponding pre-initialized client instance and model string.
    
    Raises:
        ValueError: If the configured LLM_PROVIDER is not supported.
        
    Returns:
        A tuple containing the active OpenAI client and the model name.
    """
    provider = settings.LLM_PROVIDER
    client = _clients.get(provider)
    model = _models.get(provider)
    
    if not client or not model:
        raise ValueError(f"Unsupported or misconfigured LLM provider: {provider}")
        
    return client, model

async def call_llm(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Message:
    try:
        client, model = get_llm_client_and_model()

        request_params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"

        response = client.chat.completions.create(**request_params, temperature=0.0)
        
        response_message = response.choices[0].message
        
        return Message.model_validate(response_message.model_dump())
        
    except APIError as e:
        message = str(e.body) if e.body is not None else 'Unknown API Error'
        if isinstance(e.body, dict):
            message = e.body.get('message', 'Unknown API Error')
        
        # 使用 console.error
        console.error(f"An API error occurred: {message}")
        error_content = f"Error from LLM provider: {message}"
        return Message(role="assistant", content=error_content)
    except Exception as e:
        console.exception("An unexpected error occurred while calling the LLM.")
        return Message(role="assistant", content=f"An unexpected error occurred: {e}")
