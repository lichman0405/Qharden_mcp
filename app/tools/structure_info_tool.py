# A tool to wrap the Zeo++ structure info analysis (-strinfo) service.
# Author: Shibo Li
# Date: 2025-06-12
# Version: 0.1.0

import httpx
import base64
import binascii
import json
from pydantic import BaseModel, Field
from typing import Type, Optional, TYPE_CHECKING
from .base_tool import BaseTool
from app.utils.logger import console
from app.core.config import get_settings

# Use a forward reference for the Conversation type
if TYPE_CHECKING:
    from app.models.common import Conversation

class StructureInfoInput(BaseModel):
    """Input model for the Structure Info tool."""
    source_filename: str = Field(..., description="The filename of the structure within the session workspace to use as input.")
    output_filename: Optional[str] = Field(default="result.strinfo", description="Custom output filename for the result.")

class StructureInfoTool(BaseTool):
    """
    This tool analyzes general structural information of a material, such as the number
    of frameworks, channels, and pockets. It reads the source file from the session workspace.
    """
    name: str = "analyze_structure_info"
    description: str = "Analyzes a crystalline structure from a file in the workspace to " \
    "get general information like framework count and dimensionality. " \
    "The input file MUST be in .cif format."
    args_schema: Type[BaseModel] = StructureInfoInput
    
    _service_url: str

    def __init__(self):
        """Initializes the tool and sets the service URL from application settings."""
        super().__init__()
        settings = get_settings()
        if not settings.ZEOPP_API_BASE_URL:
            raise ValueError("ZEOPP_API_BASE_URL is not set in the environment file (.env).")
        self._service_url = f"{settings.ZEOPP_API_BASE_URL.rstrip('/')}/api/structure_info"

    async def execute(self, conversation: "Conversation", 
                      source_filename: str,
                      output_filename: str = "result.strinfo") -> str:
        """
        Executes the tool by retrieving the file from the workspace and calling the Zeo++ API.
        """
        console.info(f"Executing tool '{self.name}' using file from workspace: '{source_filename}'")
        
        structure_content_base64 = conversation.workspace.get(source_filename)
        if not structure_content_base64:
            return f"Error: File '{source_filename}' not found in the current session workspace."
        
        try:
            decoded_content = base64.b64decode(structure_content_base64)
            
            files = {"structure_file": (source_filename, decoded_content, "application/octet-stream")}
            data = {"output_filename": output_filename}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self._service_url, data=data, files=files, timeout=120.0)
                response.raise_for_status()
                result_data = response.json()
                
                frameworks_list = result_data.get('frameworks', [])
                framework_details = ", ".join([f"ID {f.get('id', 'N/A')}: dimensionality {f.get('dimensionality', 'N/A')}" for f in frameworks_list]) or "No framework data."

                tool_result = (
                    f"Structure analysis completed successfully for '{source_filename}'. "
                    f"Number of frameworks: {result_data.get('num_frameworks', 'N/A')}. "
                    f"Framework details: [{framework_details}]. "
                    f"Number of channels: {result_data.get('channels', 'N/A')}. "
                    f"Number of pockets: {result_data.get('pockets', 'N/A')}. "
                    f"Nodes assigned: {result_data.get('nodes_assigned', 'N/A')}. "
                    f"Cache used: {result_data.get('cached', 'N/A')}."
                )
                
                console.success(f"Tool '{self.name}' executed and parsed successfully.")
                return tool_result
        
        except binascii.Error as e:
            error_message = f"Error decoding Base64 content for file '{source_filename}': {e}"
            console.error(error_message)
            return error_message
        except httpx.RequestError as e:
            error_message = f"HTTP request failed while processing the tool response: {e}"
            console.error(error_message)
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred while processing the tool response: {e}"
            console.error(error_message)
            return error_message