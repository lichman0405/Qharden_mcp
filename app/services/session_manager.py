# This module handles the persistence of conversation state using Redis.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 0.1.0

import redis.asyncio as redis
import redis.exceptions

from app.core.config import get_settings
from app.models.common import Conversation
from app.utils.logger import console

class SessionManager:
    """
    Manages the lifecycle of a conversation session by persisting it in Redis asynchronously.
    Attributes:
        _redis_client (redis.Redis): The Redis client for asynchronous operations.
        _session_ttl (int): Time-to-live for session data in seconds, default is 86400 seconds (1 day).
    Methods:
        __init__: Initializes the Redis client.
        save_conversation: Asynchronously saves a Conversation object to Redis.
        get_conversation: Asynchronously retrieves a Conversation object from Redis, creating a new one if not found.
    """
    _redis_client: redis.Redis
    _session_ttl: int = 86400 

    def __init__(self):
        """
        Initializes the async Redis client from the application settings.
        """
        try:
            settings = get_settings()
            self._redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            console.info("Async Redis client for session management initialized.")
        except Exception as e:
            console.error(f"Failed to initialize Redis client: {e}")
            raise

    async def save_conversation(self, session_id: str, conversation: Conversation):
        """
        Asynchronously saves a Conversation object to Redis.
        Args:
            session_id (str): Unique identifier for the conversation session.
            conversation (Conversation): The Conversation object to be saved.
        """
        try:
            conversation_json = conversation.model_dump_json()
            # Use 'await' with the async client's methods
            await self._redis_client.set(session_id, conversation_json, ex=self._session_ttl)
            console.info(f"Session '{session_id}' saved to Redis.")
        except Exception as e:
            console.exception(f"Failed to save session '{session_id}' to Redis.")

    async def get_conversation(self, session_id: str) -> Conversation:
        """
        Asynchronously retrieves and deserializes a Conversation object from Redis.
        Args:
            session_id (str): Unique identifier for the conversation session.
        Returns:
            Conversation: The retrieved Conversation object, or a new one if not found.
        """
        try:
            conversation_json = await self._redis_client.get(session_id)
            if conversation_json:
                console.info(f"Session '{session_id}' retrieved from Redis.")
                return Conversation.model_validate_json(conversation_json)
            else:
                console.info(f"Session '{session_id}' not found in Redis. Creating a new one.")
                return Conversation()
        except Exception as e:
            console.exception(f"Failed to retrieve session '{session_id}' from Redis. Returning a new conversation.")
            return Conversation()


session_manager = SessionManager()