
# Discovers and manages all available tools automatically.
# Version 1.1.0: Updated execute method to accept conversation context.

import pkgutil
import inspect
from typing import Dict, List, Any, TYPE_CHECKING
from app import tools as tools_package
from app.tools.base_tool import BaseTool
from app.utils.logger import console

# Use a forward reference for the Conversation type
if TYPE_CHECKING:
    from app.models.common import Conversation

class ToolRegistry:
    """
    A class to automatically discover, register, and manage tools.
    """
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._discover_tools()
        console.success(f"Tool discovery complete. Found {len(self.tools)} tools: {list(self.tools.keys())}")

    def _discover_tools(self):
        """
        Scans the app.tools package, imports all modules, finds classes that
        inherit from BaseTool, and creates an instance of each to register.
        """
        # --- This discovery logic remains the same ---
        for _, modname, _ in pkgutil.iter_modules(tools_package.__path__, f"{tools_package.__name__}."):
            try:
                if not modname.startswith(f"{tools_package.__name__}.base_tool"):
                    module = __import__(modname, fromlist="dummy")
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                            instance = obj()
                            self.tools[instance.name] = instance
                            console.info(f"Successfully registered tool: '{instance.name}'")
            except Exception as e:
                console.error(f"Failed to load or register tool from module {modname}: {e}")

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Returns the list of all tool definitions for the LLM."""
        if not self.tools:
            return []
        return [tool.get_definition() for tool in self.tools.values()]

    # --- MODIFICATION: The execute method now accepts the 'conversation' object ---
    async def execute(self, tool_name: str, conversation: "Conversation", kwargs: Dict[str, Any]) -> Any:
        """
        Executes a tool by its name, passing the full conversation context to it.
        """
        if tool_name in self.tools:
            # And passes the conversation object down to the tool's own execute method.
            return await self.tools[tool_name].execute(conversation=conversation, **kwargs)
        else:
            console.error(f"Attempted to execute unknown tool: {tool_name}")
            raise ValueError(f"Tool '{tool_name}' not found.")

# Create a singleton instance for global use throughout the application.
tool_registry = ToolRegistry()