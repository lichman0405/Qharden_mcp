# app/tools/xtb_opt_tool.py
# Contains a suite of tools for interacting with the xTB Optimization API service.
# Version 2.0.0: Refactored to allow specifying output filenames for downloaded results.
# Author: Shibo Li
# Date: 2025-06-13

import httpx
import base64
import json
import io
import zipfile
from pydantic import BaseModel, Field
from typing import Type, Optional, TYPE_CHECKING
from .base_tool import BaseTool
from app.utils.logger import console
from app.core.config import get_settings

if TYPE_CHECKING:
    from app.models.common import Conversation

# --- Tool 1: Submit xTB Optimization Job (No changes needed here) ---
class XtbOptimizeInput(BaseModel):
    """Input model for the xTB Optimize tool."""
    source_filename: str = Field(..., description="The filename of the structure in .xyz format from the workspace.")
    charge: Optional[int] = Field(default=0, description="The total charge of the molecule.")
    uhf: Optional[int] = Field(default=0, description="The number of unpaired electrons.")
    gfn: Optional[int] = Field(default=1, description="The GFN-xTB model version to use.")

class XtbOptimizeTool(BaseTool):
    """
    Submits a structure in XYZ format for geometry optimization using GFN1-xTB.
    Returns a JSON object with the final energy, job ID, and download URLs.
    """
    name: str = "optimize_structure_with_xtb"
    description: str = "Performs geometry optimization on a structure from the workspace using GFN1-xTB. The input file MUST be in .xyz format."
    args_schema: Type[BaseModel] = XtbOptimizeInput
    _service_url: str
    def __init__(self):
        super().__init__()
        settings = get_settings()
        if not settings.XTBOPT_API_BASE_URL:
            raise ValueError("XTBOPT_API_BASE_URL is not set in the .env file.")
        self._service_url = f"{settings.XTBOPT_API_BASE_URL.rstrip('/')}/optimize"
    async def execute(self, conversation: "Conversation", source_filename: str, charge: int = 0, uhf: int = 0, gfn: int = 1) -> str:
        console.info(f"Executing tool '{self.name}' for file: '{source_filename}'")
        structure_content_base64 = conversation.workspace.get(source_filename)
        if not structure_content_base64: return f"Error: File '{source_filename}' not found in the workspace."
        try:
            decoded_content = base64.b64decode(structure_content_base64)
            files = {"file": (source_filename, decoded_content, "application/octet-stream")}
            data = {"charge": str(charge), "uhf": str(uhf), "gfn": str(gfn)}
            async with httpx.AsyncClient() as client:
                response = await client.post(self._service_url, data=data, files=files, timeout=300.0)
                response.raise_for_status()
                result_data = response.json()
                console.success(f"Tool '{self.name}' executed successfully.")
                return json.dumps(result_data, indent=2)
        except Exception as e:
            console.exception(f"An error occurred while calling xTB Opt API for tool '{self.name}'.")
            return f"An error occurred: {e}"

# --- Tool 2: Download and Unpack xTB Result (With Modifications) ---
class DownloadXtbResultInput(BaseModel):
    """Input model for the Download xTB Result tool."""
    job_id: str = Field(..., description="The job_id provided by the 'optimize_structure_with_xtb' tool.")
    # --- NEW: Added parameter to allow specifying the output filename ---
    output_filename: str = Field(..., description="The desired filename for the extracted 'xtbopt.xyz' file to be saved in the workspace.")

class DownloadXtbResultTool(BaseTool):
    """
    Downloads the ZIP archive for a given job_id, automatically extracts the primary
    optimized structure file ('xtbopt.xyz'), and saves it to the workspace with a new name.
    """
    name: str = "download_xtb_optimization_result"
    # --- MODIFICATION: Updated description to reflect the new parameter ---
    description: str = "Downloads and unpacks an xTB optimization result ZIP, extracts the 'xtbopt.xyz' file, and saves it to the workspace with a specified output filename."
    args_schema: Type[BaseModel] = DownloadXtbResultInput
    _service_url_template: str
    def __init__(self):
        super().__init__()
        settings = get_settings()
        if not settings.XTBOPT_API_BASE_URL:
            raise ValueError("XTBOPT_API_BASE_URL is not set in the .env file.")
        self._service_url_template = f"{settings.XTBOPT_API_BASE_URL.rstrip('/')}/download/{{job_id}}"

    # --- MODIFICATION: Updated execute method signature ---
    async def execute(self, conversation: "Conversation", job_id: str, output_filename: str) -> str:
        console.info(f"Executing tool '{self.name}' for job_id: '{job_id}'")
        service_url = self._service_url_template.format(job_id=job_id)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(service_url, timeout=60.0, follow_redirects=True)
                response.raise_for_status()
                zip_content_bytes = response.content
                with zipfile.ZipFile(io.BytesIO(zip_content_bytes)) as zip_file:
                    target_file = 'xtbopt.xyz'
                    if target_file not in zip_file.namelist():
                        return f"Error: '{target_file}' not found in the downloaded ZIP archive."
                    optimized_content_bytes = zip_file.read(target_file)
                optimized_content_base64 = base64.b64encode(optimized_content_bytes).decode('utf-8')
                # --- MODIFICATION: Use the provided output_filename ---
                conversation.workspace[output_filename] = optimized_content_base64
                success_message = f"Successfully downloaded and extracted '{target_file}'. Saved to workspace as '{output_filename}'."
                console.success(success_message)
                return success_message
        except Exception as e:
            console.exception(f"An error occurred while calling download API for tool '{self.name}'.")
            return f"An error occurred: {e}"
