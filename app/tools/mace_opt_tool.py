# app/tools/mace_opt_tool.py
# Contains a suite of tools for interacting with the MACEOPT API service.
# Author: Shibo Li & Gemini
# Date: 2025-06-13
# Version: 1.0.0

import httpx
import base64
import json
from pydantic import BaseModel, Field
from typing import Type, Optional, TYPE_CHECKING
from .base_tool import BaseTool
from app.utils.logger import console
from app.core.config import get_settings

if TYPE_CHECKING:
    from app.models.common import Conversation

# --- Tool 1: Submit Optimization Job ---

class MaceOptimizeInput(BaseModel):
    """Input model for the MACE Optimize tool."""
    source_filename: str = Field(..., description="The filename of the structure in .xyz format from the workspace.")
    fmax: Optional[float] = Field(default=0.1, description="The maximum force tolerance for the geometry optimization.")
    device: Optional[str] = Field(default="cpu", description="The device to run the calculation on, e.g., 'cpu' or 'cuda'.")

class MaceOptimizeTool(BaseTool):
    """
    Submits a structure in XYZ format for geometry optimization using MACE.
    IMPORTANT: This tool does NOT return the final structure. It returns a JSON object 
    containing the final energy and links to download the optimized files.
    """
    name: str = "optimize_structure_with_mace"
    description: str = "Performs geometry optimization on a structure from the workspace. The input file MUST be in .xyz format."
    args_schema: Type[BaseModel] = MaceOptimizeInput
    
    _service_url: str

    def __init__(self):
        super().__init__()
        settings = get_settings()
        if not settings.MACEOPT_API_BASE_URL:
            raise ValueError("MACEOPT_API_BASE_URL is not set in the .env file.")
        self._service_url = f"{settings.MACEOPT_API_BASE_URL.rstrip('/')}/optimize"

    async def execute(self, conversation: "Conversation", source_filename: str, fmax: float = 0.1, device: str = "cpu") -> str:
        console.info(f"Executing tool '{self.name}' for file: '{source_filename}'")
        
        structure_content_base64 = conversation.workspace.get(source_filename)
        if not structure_content_base64:
            return f"Error: File '{source_filename}' not found in the workspace."
        
        try:
            decoded_content = base64.b64decode(structure_content_base64)
            files = {"structure_file": (source_filename, decoded_content, "application/octet-stream")}
            data = {"fmax": str(fmax), "device": device}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self._service_url, data=data, files=files, timeout=300.0)
                response.raise_for_status()
                result_data = response.json()
                
                console.success(f"Tool '{self.name}' executed successfully.")
                return json.dumps(result_data, indent=2)
        except Exception as e:
            console.exception(f"An error occurred while calling MACEOPT API for tool '{self.name}'.")
            return f"An error occurred: {e}"


class DownloadStructureInput(BaseModel):
    """Input model for the Download Structure tool."""
    path: str = Field(..., description="The relative path to the file to download, e.g., 'session_xyz/optimized.xyz', provided by the 'optimize_structure_with_mace' tool.")

class DownloadOptimizedStructureTool(BaseTool):
    """
    Downloads an optimized structure file (.xyz or .extxyz) using a path obtained
    from the result of the 'optimize_structure_with_mace' tool, and saves it to the workspace.
    """
    name: str = "download_optimized_structure"
    description: str = "Downloads a structure file from the MACEOPT service and saves it to the session workspace."
    args_schema: Type[BaseModel] = DownloadStructureInput

    _service_url: str

    def __init__(self):
        super().__init__()
        settings = get_settings()
        if not settings.MACEOPT_API_BASE_URL:
            raise ValueError("MACEOPT_API_BASE_URL is not set in the .env file.")
        self._service_url = f"{settings.MACEOPT_API_BASE_URL.rstrip('/')}/download"

    async def execute(self, conversation: "Conversation", path: str) -> str:
        console.info(f"Executing tool '{self.name}' for path: '{path}'")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._service_url, params={"path": path}, timeout=60.0)
                response.raise_for_status()
                
                file_content_bytes = response.content
                file_content_base64 = base64.b64encode(file_content_bytes).decode('utf-8')
                filename = path.split('/')[-1]

                # Save the downloaded file to the workspace
                conversation.workspace[filename] = file_content_base64
                
                success_message = f"Successfully downloaded '{filename}' and saved it to the workspace."
                console.success(success_message)
                return success_message
        except Exception as e:
            console.exception(f"An error occurred while calling download API for tool '{self.name}'.")
            return f"An error occurred: {e}"