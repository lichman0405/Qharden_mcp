# This module defines all the background tasks that are run by Celery workers.
# Author: Shibo Li 
# Date: 2025-06-13
# Version: 0.1.0

import asyncio
from app.worker import celery_app
from app.services.session_manager import session_manager
from app.core.tool_registry import tool_registry
from app.utils.logger import console
from app.models.common import Message

@celery_app.task(name="app.tasks.execute_tool_task")
def execute_tool_task(session_id: str, tool_name: str, tool_args: dict) -> str:
    """
    A Celery task to execute a tool asynchronously.
    This function is run by a Celery worker process, not the main FastAPI app.
    Args:
        session_id (str): The ID of the session where the tool is being executed.
        tool_name (str): The name of the tool to execute.
        tool_args (dict): Arguments to pass to the tool.
    Returns:
        str: The result of the tool execution.
    Raises:
        Exception: If the tool execution fails.
    """
    console.info(f"[Celery Task {execute_tool_task.request.id}] Started for tool '{tool_name}' in session '{session_id}'.")
    
    try:
        conversation = asyncio.run(session_manager.get_conversation(session_id))
        
        tool_result_message = asyncio.run(
            tool_registry.execute(
                tool_name=tool_name,
                conversation=conversation,
                kwargs=tool_args
            )
        )

        tool_message = Message(
            role="tool",
            content=tool_result_message
        )
        conversation.messages.append(tool_message)
        
        asyncio.run(session_manager.save_conversation(session_id, conversation))
        
        console.success(f"[Celery Task {execute_tool_task.request.id}] Completed successfully.")
        return tool_result_message
        
    except Exception as e:
        console.exception(f"[Celery Task {execute_tool_task.request.id}] Failed.")
        raise e