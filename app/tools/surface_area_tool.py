# The module imports necessary libraries and defines the SurfaceAreaTool class, 
# which calculates the accessible and non-accessible surface area of a porous material using the Zeo++ API service.
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
from app.models.common import Conversation


class SurfaceAreaInput(BaseModel):
    """
    Input model for the Surface Area tool, now using a workspace file.
    Attributes:
        source_filename (str): The filename of the structure within the session workspace to use as input.
        chan_radius (float): The radius of the probe used to test for accessibility of the surface area.
        probe_radius (float): The radius of the probe used for the Monte Carlo sampling.
        samples (int): The number of Monte Carlo samples to use per atom.
        output_filename (Optional[str]): Custom output filename for the result.
        ha (Optional[bool]): Whether to use high-accuracy mode.
    """
    source_filename: str = Field(..., description="The filename of the structure within the session workspace to use as input.")
    chan_radius: float = Field(..., description="The radius of the probe used to test for accessibility of the surface area.")
    probe_radius: float = Field(..., description="The radius of the probe used for the Monte Carlo sampling.")
    samples: int = Field(..., description="The number of Monte Carlo samples to use per atom.")
    output_filename: Optional[str] = Field(default="result.sa", description="Custom output filename for the result.")
    ha: Optional[bool] = Field(default=True, description="Whether to use high-accuracy mode.")

class SurfaceAreaTool(BaseTool):
    """
    This tool calculates the accessible and non-accessible surface area of a porous material
    by calling the Zeo++ '-sa' command via an API service. It reads the source file from the session workspace.
    """
    name: str = "calculate_surface_area"
    description: str = "Calculates the accessible surface area (ASA) and " \
    "non-accessible surface area (NASA) of a crystalline material from a file in the workspace." \
    "The input file MUST be in .cif format."
    args_schema: Type[BaseModel] = SurfaceAreaInput
    
    _service_url: str


    def __init__(self):
        """Initializes the tool and sets the service URL from application settings."""
        super().__init__()
        settings = get_settings()
        if not settings.ZEOPP_API_BASE_URL:
            raise ValueError("ZEOPP_API_BASE_URL is not set in the environment file (.env).")
        self._service_url = f"{settings.ZEOPP_API_BASE_URL.rstrip('/')}/api/surface_area"


    async def execute(self, conversation: "Conversation", source_filename: str, chan_radius: float, probe_radius: float, samples: int, ha: bool = True, output_filename: str = "result.sa") -> str:
        """
        Executes the tool by:
        1. Retrieving the file content from the conversation's workspace.
        2. Sending a request to the Zeo++ API.
        3. Parsing the response and returning a formatted string.
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
                
                tool_result = (
                    f"Surface area calculation completed successfully for '{source_filename}'. "
                    f"Accessible Surface Area (ASA): {result_data.get('asa_volume', 'N/A')} m^2/cm^3, {result_data.get('asa_mass', 'N/A')} m^2/g. "
                    f"Non-Accessible Surface Area (NASA): {result_data.get('nasa_volume', 'N/A')} m^2/cm^3, {result_data.get('nasa_mass', 'N/A')} m^2/g. "
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