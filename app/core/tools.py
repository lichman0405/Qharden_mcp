# app/core/tools.py
# This file acts as a registry for all available tools that the MCP can use.

available_tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Searches the web for a given query to find up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web.",
                    },
                },
                "required": ["query"],
            },
        },
    }
    # NOTE: You can add more tool definitions here in the future.
]

# A registry that maps tool names to their actual callable endpoints.
# This is used internally by the orchestrator to execute the tool call.
tool_registry = {
    "search_web": {
        "url": "http://localhost:8001/search",
        "method": "POST"
    }
}