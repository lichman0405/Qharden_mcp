# A tool to wrap the Zeo++ channel analysis (-chan) service.
# Author: Shibo Li
# Date: 2025-06-12
# Version: 0.1.0

import httpx
import base64
import binascii
from pydantic import BaseModel, Field
from typing import Type, Optional, TYPE_CHECKING
from .base_tool import BaseTool
from app.utils.logger import console
from app.core.config import get_settings

# Use a forward reference for the Conversation type
if TYPE_CHECKING:
    from app.models.common import Conversation

class ChannelAnalysisInput(BaseModel):
    """Input model for the Channel Analysis tool."""
    source_filename: str = Field(..., description="The filename of the structure within the session workspace to use as input.")
    probe_radius: float = Field(..., description="The radius of the spherical probe used for channel analysis.")
    output_filename: Optional[str] = Field(default="result.chan", description="Custom output filename for the result.")
    ha: Optional[bool] = Field(default=True, description="Whether to use high-accuracy mode.")

class ChannelAnalysisTool(BaseTool):
    """
    This tool analyzes the dimensionality and diameters of channels within a
    crystalline material. It reads the source file from the session workspace.
    """
    name: str = "calculate_channel_analysis"
    description: str = "Analyzes the channel system of a porous material " \
    "from a file in the workspace to determine its dimensionality and diameters." \
    "The input file MUST be in .cif format."
    args_schema: Type[BaseModel] = ChannelAnalysisInput
    
    _service_url: str

    def __init__(self):
        """Initializes the tool and sets the service URL from application settings."""
        super().__init__()
        settings = get_settings()
        if not settings.ZEOPP_API_BASE_URL:
            raise ValueError("ZEOPP_API_BASE_URL is not set in the environment file (.env).")
        self._service_url = f"{settings.ZEOPP_API_BASE_URL.rstrip('/')}/api/channel_analysis"

    async def execute(self, conversation: "Conversation", 
                      source_filename: str,
                      probe_radius: float, 
                      ha: bool = True, 
                      output_filename: str = "result.chan") -> str:
        """
        Executes the tool by retrieving the file from the workspace and calling the Zeo++ API.
        """
        console.info(f"Executing tool '{self.name}' using file from workspace: '{source_filename}'")
        
        structure_content_base64 = conversation.workspace.get(source_filename)
        if not structure_content_base64:
            error_message = f"Error: File '{source_filename}' not found in the current session workspace."
            console.error(error_message)
            return error_message

        try:
            decoded_content = base64.b64decode(structure_content_base64)
            
            files = {"structure_file": (source_filename, decoded_content, "application/octet-stream")}
            data = {
                "probe_radius": str(probe_radius),
                "ha": str(ha).lower(),
                "output_filename": output_filename
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self._service_url, data=data, files=files, timeout=120.0)
                response.raise_for_status()
                result_data = response.json()
                
                tool_result = (
                    f"Channel analysis completed successfully for '{source_filename}'. "
                    f"Channel Dimensionality: {result_data.get('dimension', 'N/A')}. "
                    f"Largest Included Sphere: {result_data.get('included_diameter', 'N/A')} Å, "
                    f"Largest Free Sphere: {result_data.get('free_diameter', 'N/A')} Å, "
                    f"Largest Included Sphere Along Free Sphere Path: {result_data.get('included_along_free', 'N/A')} Å. "
                    f"Cache used: {result_data.get('cached', 'N/A')}."
                )
                
                console.success(f"Tool '{self.name}' executed and parsed successfully.")
                return tool_result
        
        except binascii.Error as e:
            error_message = f"Base64 decoding failed for file '{source_filename}' from workspace. Error: {e}"
            console.error(error_message)
            return error_message
        except httpx.RequestError as e:
            error_message = f"An HTTP error occurred while calling the Zeo++ API at {self._service_url}: {e}"
            console.error(error_message)
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred while executing the tool '{self.name}': {e}"
            console.exception(error_message)
            return error_message
