# The module is to define the SearchWebTool that uses the Tavily AI Search API.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

from pydantic import BaseModel, Field
from typing import Type, Dict
from .base_tool import BaseTool
from app.utils.logger import console
from app.core.config import get_settings
from tavily import TavilyClient

class SearchWebInput(BaseModel):
    """
    Input model for the SearchWebTool.
    Attributes:
        query (str): The search query to look up on the web.
    """
    query: str = Field(..., description="The search query to look up on the web. Be specific and descriptive.")

class SearchWebTool(BaseTool):
    """
    A powerful tool that uses the Tavily AI Search API to perform web searches,
    find up-to-date information, and get concise answers.
    """
    name: str = "tavily_search" 
    description: str = "Searches the web for a given query using the Tavily AI search engine. " \
    "Good for finding real-time or specific information."
    args_schema: Type[BaseModel] = SearchWebInput
    
    _tavily_client: TavilyClient

    def __init__(self):
        """
        Initializes the Tavily client when the tool is created.
        """
        super().__init__()
        settings = get_settings()
        if not settings.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY is not set in the environment.")
        self._tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    async def execute(self, query: str) -> str:
        """
        Executes the web search using the Tavily client and formats the results.
        Args:
            query (str): The search query to look up on the web.
        Returns:
            str: A formatted string containing the search results.
        """
        console.info(f"Executing tool '{self.name}' with query: '{query}'")
        try:
            # .search is a comprehensive method that returns a dictionary.
            # We can specify max_results, include_answer, etc.
            response = self._tavily_client.search(
                query=query, 
                search_depth="advanced",
                max_results=5
            )
            
            formatted_results = self._format_results(response)
            console.success(f"Tool '{self.name}' executed successfully.")
            return formatted_results

        except Exception as e:
            console.exception(f"An error occurred during Tavily search for query: '{query}'")
            return f"An error occurred while executing the search: {e}"

    def _format_results(self, response: Dict) -> str:
        """
        Helper function to format the JSON response from Tavily into a string.
        Args:
            response (Dict): The JSON response from the Tavily search.
        Returns:
            str: A formatted string containing the search results.
        """
        results = response.get("results", [])
        if not results:
            return "No search results found."

        formatted_string = ""
        for result in results:
            formatted_string += f"Title: {result.get('title', 'N/A')}\n"
            formatted_string += f"URL: {result.get('url', 'N/A')}\n"
            formatted_string += f"Content Snippet: {result.get('content', 'N/A')}\n---\n"
        
        return formatted_string.strip()