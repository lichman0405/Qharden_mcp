# The module is to define the common model for the application.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0


from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict

# The Role literal type remains unchanged.
Role = Literal["system", "user", 
               "assistant", "tool"]


class ToolCall(BaseModel):
    """
    Represents a tool call made by the assistant, including the function name and arguments.
    Attributes:
        id (str): The unique ID for the tool call.
        function (dict): The function name and arguments.
        type (str): The type of the tool call, e.g., 'function'.
    """
    id: str = Field(..., description="The unique ID for the tool call.")
    function: dict = Field(..., description="The function name and arguments.")
    type: str = Field(default="function", description="The type of the tool call, e.g., 'function'.")


class Message(BaseModel):
    """
    Represents a message in the conversation, which can be from the system, user, assistant, or tool.
    Attributes:
        role (Role): The role of the message sender (system, user, assistant, or tool).
        content (Optional[str]): The content of the message.
        tool_calls (Optional[List[ToolCall]]): A list of tool calls requested by the assistant.
        tool_call_id (Optional[str]): The ID of the tool call this message is a result of.
    """
    role: Role = Field(..., description="The role of the message sender.")
    content: Optional[str] = Field(default=None, description="The content of the message.")
    tool_calls: Optional[List[ToolCall]] = Field(default=None, description="A list of tool calls requested by the assistant.")
    tool_call_id: Optional[str] = Field(default=None, description="The ID of the tool call this message is a result of.")


class Conversation(BaseModel):
    """
    Represents a complete conversation session, including message history
    and an in-memory workspace for file artifacts generated during the session.
    """
    session_id: Optional[str] = None
    messages: List[Message] = Field(default_factory=list, description="The history of messages in the conversation.")
    workspace: Dict[str, str] = Field(default_factory=dict, description="A temporary workspace to store and pass files between tool calls.")
