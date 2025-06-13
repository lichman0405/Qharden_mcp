# app/tools/file_converter_tool.py
# A tool to interconvert chemical file formats using the ASE library.
# Version 3.0.0: Fully integrated with the workspace and pre-processing workflow.
# Author: Shibo Li
# Date: 2025-06-13

import base64
import io
import json
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

# --- MODIFICATION: The input model is now much simpler ---
class FileConverterInput(BaseModel):
    """Input model for the File Converter tool."""
    source_filename: str = Field(..., description="The filename of the structure in the workspace to be converted.")
    target_format: Literal["xyz", "cif", "pdb", "cssr"] = Field(..., description="The desired output file format.")

class FileConverterTool(BaseTool):
    """
    This tool converts the content of a chemical structure file from the workspace
    into another format (e.g., CIF to XYZ) and saves the result back to the workspace.
    """
    name: str = "convert_structure_file"
    description: str = "Converts a structure file from the workspace to a target format. The result is saved back into the workspace."
    args_schema: Type[BaseModel] = FileConverterInput

    # --- MODIFICATION: The execute method is now much simpler ---
    async def execute(self, conversation: "Conversation", source_filename: str, target_format: str) -> str:
        """
        Executes the file conversion by reading from and writing to the conversation's workspace.
        """
        if ase_io is None:
            return "Error: The 'ase' library is not installed on the server."
            
        console.info(f"Executing tool '{self.name}': Converting '{source_filename}' from workspace to '{target_format}'.")
        
        # Step 1: Retrieve the file content from the workspace.
        input_content_base64 = conversation.workspace.get(source_filename)
        if not input_content_base64:
            return f"Error: Source file '{source_filename}' not found in workspace."

        try:
            # The rest of the logic remains the same: decode, convert, encode.
            decoded_content = base64.b64decode(input_content_base64).decode('utf-8')
            input_file_handle = io.StringIO(decoded_content)
            structure = ase_io.read(input_file_handle)
            
            output_file_handle = io.StringIO()
            ase_io.write(output_file_handle, structure, format=target_format)
            output_content = output_file_handle.getvalue()
            
            output_content_base64 = base64.b64encode(output_content.encode('utf-8')).decode('utf-8')
            
            # Save the new file back to the workspace
            new_filename = f"{source_filename.rsplit('.', 1)[0]}.{target_format}"
            conversation.workspace[new_filename] = output_content_base64
            
            success_message = f"Successfully converted '{source_filename}' to '{new_filename}' and saved it back to the workspace."
            console.success(success_message)
            
            return success_message

        except Exception as e:
            error_message = f"An unexpected error occurred during file conversion: {e}"
            console.exception(error_message)
            return error_message
