# app/tools/pore_size_dist_tool.py
# A tool to wrap the Zeo++ pore size distribution (-psd) calculation service.
# Version 2.0.0: Refactored to read input files from the session workspace.

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


class PoreSizeDistInput(BaseModel):
    """Input model for the Pore Size Distribution tool."""
    source_filename: str = Field(..., description="The filename of the structure within the session workspace to use as input.")
    chan_radius: float = Field(..., description="The radius of the probe used to test for channel accessibility.")
    probe_radius: float = Field(..., description="The radius of the probe used for Monte Carlo sampling.")
    samples: int = Field(..., description="The number of Monte Carlo samples to use.")
    output_filename: Optional[str] = Field(default="result.psd_histo", description="Custom output filename for the result.")
    ha: Optional[bool] = Field(default=True, description="Whether to use high-accuracy mode.")

class PoreSizeDistTool(BaseTool):
    """
    This tool computes the pore size distribution for a crystalline material.
    It reads the source file from the session workspace.
    """
    name: str = "calculate_pore_size_distribution"
    description: str = "Computes the pore size distribution (PSD) of a crystalline material " \
    "from a file in the workspace and returns the raw histogram data as text. " \
    "The input file MUST be in .cif format."
    args_schema: Type[BaseModel] = PoreSizeDistInput
    
    _service_url: str

    def __init__(self):
        """Initializes the tool and sets the service URL from application settings."""
        super().__init__()
        settings = get_settings()
        if not settings.ZEOPP_API_BASE_URL:
            raise ValueError("ZEOPP_API_BASE_URL is not set in the environment file (.env).")
        self._service_url = f"{settings.ZEOPP_API_BASE_URL.rstrip('/')}/api/pore_size_dist"

    async def execute(self, conversation: "Conversation", 
                      source_filename: str,
                      chan_radius: float, 
                      probe_radius: float, 
                      samples: int, 
                      ha: bool = True, 
                      output_filename: str = "result.psd_histo") -> str:
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
                "chan_radius": str(chan_radius),
                "probe_radius": str(probe_radius),
                "samples": str(samples),
                "ha": str(ha).lower(),
                "output_filename": output_filename
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self._service_url, data=data, files=files, timeout=180.0)
                response.raise_for_status()
                result_data = response.json()
                
                raw_content = result_data.get('content', 'No content found in response.')
                tool_result = (
                    f"Pore size distribution calculation completed successfully for '{source_filename}'. "
                    f"The raw histogram data is as follows:\n\n{raw_content}"
                )
                
                console.success(f"Tool '{self.name}' executed successfully.")
                return tool_result
        
        except binascii.Error as e:
            error_message = f"Base64 decoding failed for file '{source_filename}' from workspace. Error: {e}"
            console.error(error_message)
            return error_message
        except httpx.RequestError as e:
            error_message = f"An HTTP error occurred while calling the Zeo++ API at {self._service_url}: {e}"
            console.exception(error_message)
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred while processing the tool response: {e}"
            console.exception(error_message)
            return error_message