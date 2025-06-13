# A tool to calculate accessible volume, refactored to use the session workspace.
# Author: Shibo Li & Gemini
# Date: 2025-06-13
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


class AccessibleVolumeInput(BaseModel):
    """Input model for the accessible volume tool, now using a workspace file."""
    source_filename: str = Field(..., description="The filename of the structure within the session workspace to use as input.")
    chan_radius: float = Field(..., description="The radius of the probe used to test for accessibility.")
    probe_radius: float = Field(..., description="The radius of the probe used for the Monte Carlo sampling to measure volume.")
    samples: int = Field(..., description="The number of Monte Carlo samples to use per unit cell.")
    output_filename: Optional[str] = Field(default="result.vol", description="Custom output filename for the result.")
    ha: Optional[bool] = Field(default=True, description="Whether to use high-accuracy mode.")


class AccessibleVolumeTool(BaseTool):
    """
    This tool calculates the accessible volume of a crystalline material
    by calling the Zeo++ '-vol' command. It reads the source file from the session workspace.
    """
    name: str = "calculate_accessible_volume"
    description: str = "Calculates the accessible volume (AV) and " \
    "non-accessible volume (NAV) of a crystalline material from a file in the workspace." \
    "The input file MUST be in .cif format."
    args_schema: Type[BaseModel] = AccessibleVolumeInput

    _service_url: str

    def __init__(self):
        """Initializes the tool and sets the service URL from application settings."""
        super().__init__()
        settings = get_settings()
        if not settings.ZEOPP_API_BASE_URL:
            raise ValueError("ZEOPP_API_BASE_URL is not set in the environment file (.env).")
        self._service_url = f"{settings.ZEOPP_API_BASE_URL.rstrip('/')}/api/accessible_volume"

    async def execute(self, conversation: "Conversation", 
                      source_filename: str,
                      chan_radius: float, 
                      probe_radius: float, 
                      samples: int, 
                      ha: bool = True, 
                      output_filename: str = "result.vol") -> str:
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
                response = await client.post(self._service_url, data=data, files=files, timeout=120.0)
                response.raise_for_status()
                result_data = response.json()
                
                av_data = result_data.get('av', {})
                nav_data = result_data.get('nav', {})
                av_details = json.dumps(av_data) if av_data else "Not available"
                nav_details = json.dumps(nav_data) if nav_data else "Not available"

                tool_result = (
                    f"Accessible Volume calculation completed successfully for '{source_filename}'. "
                    f"Unitcell Volume: {result_data.get('unitcell_volume', 'N/A')} Å^3, "
                    f"Density: {result_data.get('density', 'N/A')} g/cm^3. "
                    f"Accessible Volume (AV) details: {av_details}. "
                    f"Non-Accessible Volume (NAV) details: {nav_details}. "
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
            console.exception(error_message)
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred while processing the tool response: {e}"
            console.exception(error_message)
            return error_message