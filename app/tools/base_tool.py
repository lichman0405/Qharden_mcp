# The module is to define the base class for all tools in the application.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Dict, Any, Type
from app.models.common import Conversation


class BaseTool(ABC):
    """
    Abstract Base Class for all tools.
    
    This class defines a standard interface that all tools must implement.
    Attributes:
        name (str): The name of the tool, used for identification.
        description (str): A brief description of what the tool does.
        args_schema (Type[BaseModel]): A Pydantic model defining the arguments
            that the tool accepts, which will be validated before execution.
    """
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    async def execute(self, conversation: "Conversation", **kwargs) -> str:
        """
        The core logic of the tool. This method must be implemented by all subclasses.
        It now receives the entire conversation object, allowing it to access the
        session workspace via 'conversation.workspace'.
        
        Args:
            conversation: The current conversation object, including its workspace.
            **kwargs: The arguments for the tool, validated against args_schema.

        Returns:
            A string summarizing the result of the tool's execution.
        """
        pass

    def get_definition(self) -> Dict[str, Any]:
        """
        Returns the tool's definition in a format compliant with OpenAI's
        function-calling specification. This method is inherited by all tools.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema()
            }
        }