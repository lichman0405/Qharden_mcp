# The module is to define the tool registry for the application.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

import pkgutil
import inspect
from typing import Dict, List, Any
from app import tools as tools_package
from app.tools.base_tool import BaseTool
from app.utils.logger import console

class ToolRegistry:
    """
    A class to automatically discover, register, and manage tools.
    It scans the 'app.tools' package for any classes that inherit from BaseTool.
    Attributes:
        tools (Dict[str, BaseTool]): A dictionary mapping tool names to their instances.
    Methods:
        __init__: Initializes the ToolRegistry and discovers tools.
        _discover_tools: Scans the tools package and registers all BaseTool subclasses.
        get_definitions: Returns a list of tool definitions for the LLM.
        execute: Executes a tool by its name with the provided arguments.
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
        # Use pkgutil to iterate through all modules in the tools package
        for _, modname, _ in pkgutil.iter_modules(tools_package.__path__, f"{tools_package.__name__}."):
            try:
                module = __import__(modname, fromlist="dummy")
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                        # Create an instance of the tool and register it
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

    async def execute(self, tool_name: str, kwargs: Dict[str, Any]) -> Any:
        """
        Executes a tool by its name with the given arguments.
        Args:
            tool_name (str): The name of the tool to execute.
            kwargs (Dict[str, Any]): The keyword arguments to pass to the tool
        Returns:
            Any: The result of the tool execution.
        """
        if tool_name in self.tools:
            return await self.tools[tool_name].execute(**kwargs)
        else:
            console.error(f"Attempted to execute unknown tool: {tool_name}")
            raise ValueError(f"Tool '{tool_name}' not found.")

tool_registry = ToolRegistry()