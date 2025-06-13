# The module imports necessary libraries and defines a tool for calculating pore diameters 
# in crystalline materials using the Zeo++ API service.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0


import httpx
import base64
import binascii
from pydantic import BaseModel, Field
from typing import Type, Optional, TYPE_CHECKING
from .base_tool import BaseTool
from app.utils.logger import console
from app.core.config import get_settings
from app.models.common import Conversation

class PoreDiameterInput(BaseModel):
    """
    Input model for the Pore Diameter tool, now using a workspace file.
    Attributes:
        source_filename (str): The filename of the structure within the session workspace to be analyzed.
        ha (Optional[bool]): Whether to use high-accuracy mode.
        output_filename (Optional[str]): Custom output filename for the result.
    """
    source_filename: str = Field(..., description="The filename of the structure within the session workspace to be analyzed.")
    ha: Optional[bool] = Field(default=True, description="Whether to use high-accuracy mode.")
    output_filename: Optional[str] = Field(default="result.res", description="Custom output filename for the result.")

class PoreDiameterTool(BaseTool):
    """
    This tool calculates the largest free and included sphere diameters for a porous material
    by calling the Zeo++ API service. It reads the source file from the session workspace.
    """
    name: str = "calculate_pore_diameter"
    description: str = "Calculates the pore diameters of a crystalline material from a file in the workspace. The input file MUST be in .cif format."
    args_schema: Type[BaseModel] = PoreDiameterInput
    
    _service_url: str

    def __init__(self):
        """Initializes the tool and sets the service URL from application settings."""
        super().__init__()
        settings = get_settings()
        if not settings.ZEOPP_API_BASE_URL:
            raise ValueError("ZEOPP_API_BASE_URL is not set in the environment file (.env).")
        self._service_url = f"{settings.ZEOPP_API_BASE_URL.rstrip('/')}/api/pore_diameter"


    async def execute(self, conversation: "Conversation", 
                      source_filename: str, ha: bool = True, 
                      output_filename: str = "result.res") -> str:
        """
        Executes the tool by:
        1. Retrieving the file content from the conversation's workspace.
        2. Sending a request to the Zeo++ API.
        3. Parsing the response and returning a formatted string.
        """
        console.info(f"Executing tool '{self.name}' using file from workspace: '{source_filename}'")
        
        # Step 1: Retrieve the file content from the workspace.
        structure_content_base64 = conversation.workspace.get(source_filename)
        if not structure_content_base64:
            error_message = f"Error: File '{source_filename}' not found in the current session workspace."
            console.error(error_message)
            return error_message
        
        try:
            # Step 2: Decode the Base64 content.
            decoded_content = base64.b64decode(structure_content_base64)
            
            # Step 3: Prepare the multipart/form-data payload.
            files = {"structure_file": (source_filename, decoded_content, "application/octet-stream")}
            data = {"ha": str(ha).lower(), "output_filename": output_filename}
            
            # Step 4: Make the async HTTP request.
            async with httpx.AsyncClient() as client:
                response = await client.post(self._service_url, data=data, files=files, timeout=60.0)
                response.raise_for_status()
                result_data = response.json()
                
                tool_result = (
                    f"Pore diameter calculation completed successfully for '{source_filename}'. "
                    f"Included Sphere Diameter: {result_data.get('included_diameter', 'N/A')} Å, "
                    f"Free Sphere Diameter: {result_data.get('free_diameter', 'N/A')} Å, "
                    f"Included Sphere Along Free Sphere Path: {result_data.get('included_along_free', 'N/A')} Å. "
                    f"Cache used: {result_data.get('cached', 'N/A')}."
                )
                
                console.success(f"Tool '{self.name}' executed and parsed successfully.")
                return tool_result
        
        except binascii.Error as e:
            # This error can happen if the content in the workspace is not valid Base64
            error_message = f"Base64 decoding failed for file '{source_filename}' from workspace. Error: {e}"
            console.error(error_message)
            return error_message
        except httpx.RequestError as e:
            error_message = f"An HTTP error occurred while calling the Zeo++ API: {e}"
            console.exception(error_message)
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred while processing the tool response: {e}"
            console.exception(error_message)
            return error_message