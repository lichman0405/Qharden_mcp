# The module is to define the API models for the application.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    """
    Defines the request body for the /v1/chat endpoint.
    Attributes:
        session_id (str): The unique ID for the conversation session.
        user_input (str): The user's text input to be processed by the chat service.
    """
    session_id: str = Field(..., description="The unique ID for the conversation session.")
    user_input: str = Field(..., description="The user's text input.")

class ChatResponse(BaseModel):
    """
    Defines the response body for the /v1/chat endpoint.
    Attributes:
        session_id (str): The unique ID for the conversation session.
        role (str): The role of the message sender, can be 'system', 'user', 'assistant', or 'tool'.
        content (str): The content of the message, which is the response from the chat service.
    """
    session_id: str
    role: str
    content: str
    raw_assistant_response: Optional[str] = None

class NewSessionResponse(BaseModel):
    """
    Defines the response body for the /v1/session/new endpoint.
    Attributes:
        session_id (str): The unique ID for the newly created conversation session.
        message (str): A message indicating the session has been created successfully.
    """
    session_id: str
    message: str