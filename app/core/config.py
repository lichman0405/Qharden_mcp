# The module is to define the configuration settings for the application.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """
    The Settings class is used to define the configuration settings for the application.
    It inherits from BaseSettings, which allows it to load environment variables
    and provides type validation for the settings.
    Attributes:
        LLM_PROVIDER (str): The name of the LLM provider to use.
        CHATGPT_API_KEY (str): API key for ChatGPT.
        CHATGPT_MODEL (str): Model name for ChatGPT.
        CHATGPT_BASE_URL (str): Base URL for ChatGPT API.
        CLAUDE_API_KEY (str): API key for Claude.
        CLAUDE_MODEL (str): Model name for Claude.
        CLAUDE_BASE_URL (str): Base URL for Claude API.
        GEMINI_API_KEY (str): API key for Gemini.
        GEMINI_MODEL (str): Model name for Gemini.
        GEMINI_BASE_URL (str): Base URL for Gemini API.
        DEEPSEEK_CHAT_API_KEY (str): API key for DeepSeek Chat.
        DEEPSEEK_CHAT_MODEL (str): Model name for DeepSeek Chat.
        DEEPSEEK_CHAT_BASE_URL (str): Base URL for DeepSeek Chat API.
        DEEPSEEK_REASONER_API_KEY (str): API key for DeepSeek Reasoner.
        DEEPSEEK_REASONER_MODEL (str): Model name for DeepSeek Reasoner.
        DEEPSEEK_REASONER_BASE_URL (str): Base URL for DeepSeek Reasoner API.
    """
    # LLM Provider Switch
    LLM_PROVIDER: str = "DEEPSEEK_CHAT"

    # CHATGPT
    CHATGPT_API_KEY: str
    CHATGPT_MODEL: str
    CHATGPT_BASE_URL: str

    # Claude
    CLAUDE_API_KEY: str
    CLAUDE_MODEL: str
    CLAUDE_BASE_URL: str

    # Gemini 
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    GEMINI_BASE_URL: str

    # DEEPSEEK_CHAT
    DEEPSEEK_CHAT_API_KEY: str
    DEEPSEEK_CHAT_MODEL: str
    DEEPSEEK_CHAT_BASE_URL: str

    # DEEPSEEK_REASONER
    DEEPSEEK_REASONER_API_KEY: str
    DEEPSEEK_REASONER_MODEL: str
    DEEPSEEK_REASONER_BASE_URL: str

    # TAVILY_SEARCH
    TAVILY_API_KEY: Optional[str] = None

    # ZEOPP_SERVICE
    ZEOPP_API_BASE_URL: Optional[str] = None

    # MACEOPT_SERVICE
    MACEOPT_API_BASE_URL: Optional[str] = None

    # XTB_OPTIMIZER_SERVICE
    XTBOPT_API_BASE_URL: Optional[str] = None

    # REDIS
    REDIS_URL: str


    class Config:
        # 
        env_file = ".env"
        env_file_encoding = 'utf-8'

# lru_cache to cache the settings instance.
@lru_cache
def get_settings():
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print(settings.model_dump_json(indent=4))