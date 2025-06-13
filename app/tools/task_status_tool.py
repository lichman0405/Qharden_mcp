# A tool to check the status and result of a Celery background task.
# Author: Shibo Li 
# Date: 2025-06-13
# Version: 1.0.0

from pydantic import BaseModel, Field
from typing import Type, TYPE_CHECKING
from .base_tool import BaseTool
from app.utils.logger import console
from app.worker import celery_app
from celery.result import AsyncResult

if TYPE_CHECKING:
    from app.models.common import Conversation

class CheckTaskStatusInput(BaseModel):
    """Input model for the Check Task Status tool."""
    task_id: str = Field(..., description="The ID of the background task to check.")

class CheckTaskStatusTool(BaseTool):
    """
    Checks the status of a previously submitted long-running background task.
    Returns the current status (e.g., PENDING, SUCCESS, FAILURE) and the result if available.
    """
    name: str = "check_task_status"
    description: str = "Checks the status and retrieves the result of a background task using its task ID."
    args_schema: Type[BaseModel] = CheckTaskStatusInput

    async def execute(self, conversation: "Conversation", task_id: str):
        """
        Executes the tool by querying the Celery result backend (Redis).
        """
        console.info(f"Executing tool '{self.name}' for task_id: '{task_id}'")
        
        try:
            # Create an AsyncResult instance to query the task's state
            task_result = AsyncResult(task_id, app=celery_app)
            
            status = task_result.state
            
            if task_result.ready():
                # The task has completed (either successfully or with failure).
                if task_result.successful():
                    result_data = task_result.get()
                    console.success(f"Task '{task_id}' completed successfully.")
                    return f"Task {task_id} has status SUCCESS. The result is: {result_data}"
                else:
                    # The task failed.
                    console.error(f"Task '{task_id}' failed.")
                    try:
                        task_result.get()
                    except Exception as e:
                        return f"Task {task_id} has status FAILURE. The error was: {e}"
            else:
                # The task is still pending or running.
                console.info(f"Task '{task_id}' is still in progress with status: {status}")
                return f"Task {task_id} is not yet complete. Its current status is {status}."

        except Exception as e:
            console.exception(f"An unexpected error occurred while checking task status for '{task_id}'.")
            return f"An error occurred while checking task status: {e}"