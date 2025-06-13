# A tool to interconvert between different chemical file formats using the ASE library.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 0.1.0

import base64
import io
from pydantic import BaseModel, Field
from typing import Type, Literal, TYPE_CHECKING
from .base_tool import BaseTool
from app.utils.logger import console

# Use a forward reference for the Conversation type
if TYPE_CHECKING:
    from app.models.common import Conversation

# Import the necessary components from the Atomic Simulation Environment (ASE) library
try:
    from ase import io as ase_io
except ImportError:
    console.error("ASE library not found. Please install it using 'pip install ase'")
    ase_io = None

class FileConverterInput(BaseModel):
    """Input model for the File Converter tool."""
    input_filename: str = Field(..., description="The original filename of the input structure, e.g., 'MOF-1.cif'.")
    input_content_base64: str = Field(..., description="The Base64 encoded string of the source file's content.")
    target_format: Literal["xyz", "cif", "pdb", "cssr"] = Field(..., description="The desired output file format.")

class FileConverterTool(BaseTool):
    """
    This tool converts the content of a chemical structure file from one format
    to another (e.g., CIF to XYZ) and saves the result to the session workspace.
    """
    name: str = "convert_structure_file"
    description: str = "Converts a structure file's content to a target format. The result is saved in the session workspace."
    args_schema: Type[BaseModel] = FileConverterInput

    async def execute(self, conversation: "Conversation", input_filename: str, input_content_base64: str, target_format: str) -> str:
        """
        Executes the file conversion in memory and saves the output to the
        conversation's workspace.
        """
        if ase_io is None:
            return "Error: The 'ase' library is not installed on the server."
            
        console.info(f"Executing tool '{self.name}': Converting '{input_filename}' to '{target_format}' format.")
        
        try:
            decoded_content = base64.b64decode(input_content_base64).decode('utf-8')
            input_file_handle = io.StringIO(decoded_content)
            structure = ase_io.read(input_file_handle)
            output_file_handle = io.StringIO()
            ase_io.write(output_file_handle, structure, format=target_format)
            output_content = output_file_handle.getvalue()
            output_content_base64 = base64.b64encode(output_content.encode('utf-8')).decode('utf-8')
            new_filename = f"{input_filename.rsplit('.', 1)[0]}.{target_format}"
            console.info(f"Converted '{input_filename}' to '{new_filename}' in '{target_format}' format.")
            conversation.workspace[new_filename] = output_content_base64
            success_message = f"Successfully converted '{input_filename}' to '{new_filename}' and saved it to the workspace under the name '{new_filename}'."
            console.success(success_message)
            return success_message

        except Exception as e:
            error_message = f"An unexpected error occurred during file conversion: {e}"
            console.exception(error_message)
            return error_message