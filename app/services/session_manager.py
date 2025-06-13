# This module handles the persistence of conversation state using Redis.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 0.1.0

from redis.asyncio import Redis, from_url
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import get_settings
from app.models.common import Conversation
from app.utils.logger import console

class SessionManager:
    """
    Manages the lifecycle of a conversation session by persisting it in Redis asynchronously.
    """
    _redis_client: Redis
    _session_ttl: int = 86400 

    def __init__(self):
        """Initializes the async Redis client from the application settings."""
        try:
            settings = get_settings()
            self._redis_client = from_url(settings.REDIS_URL, decode_responses=True)
            console.info("Async Redis client for session management initialized.")
        except Exception as e:
            console.error(f"Failed to initialize Redis client: {e}")
            raise

    async def save_conversation(self, session_id: str, conversation: Conversation):
        """
        Asynchronously saves a Conversation object to Redis.
        """
        try:
            conversation_json = conversation.model_dump_json()
            await self._redis_client.set(session_id, conversation_json, ex=self._session_ttl)
            console.info(f"Session '{session_id}' saved to Redis.")
        except Exception as e:
            console.exception(f"Failed to save session '{session_id}' to Redis.")

    async def get_conversation(self, session_id: str) -> Conversation:
        """
        Asynchronously retrieves and deserializes a Conversation object from Redis.
        """
        try:
            # First, check if the client was initialized correctly
            if not hasattr(self, '_redis_client'):
                 raise RuntimeError("Redis client is not initialized.")
                 
            conversation_json = await self._redis_client.get(session_id)
            if conversation_json:
                console.info(f"Session '{session_id}' retrieved from Redis.")
                return Conversation.model_validate_json(conversation_json)
            else:
                console.info(f"Session '{session_id}' not found in Redis. Creating a new one.")
                return Conversation()
        except RedisConnectionError as e:
            console.exception(f"Could not connect to Redis when getting session '{session_id}'. Please ensure Redis is running and accessible.")

            return Conversation()
        except Exception as e:
            console.exception(f"Failed to retrieve session '{session_id}' from Redis. Returning a new conversation.")
            return Conversation()

session_manager = SessionManager()