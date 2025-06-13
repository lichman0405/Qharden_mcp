# app/tasks.py
# This module defines background tasks, now with proper asyncio event loop management.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 2.0.0

import asyncio
from app.worker import celery_app
from app.services.session_manager import session_manager
from app.core.tool_registry import tool_registry
from app.utils.logger import console
from app.models.common import Message

async def _async_execute_and_save(session_id: str, tool_name: str, tool_args: dict):
    """
    An async helper function that runs the entire task logic within a single
    event loop context.
    """
    # 1. Retrieve the conversation state from Redis
    conversation = await session_manager.get_conversation(session_id)
    if not conversation.session_id:
        conversation.session_id = session_id

    # 2. Execute the tool
    tool_result_str = await tool_registry.execute(
        tool_name=tool_name,
        conversation=conversation,
        kwargs=tool_args
    )
    
    # 3. Append the tool result to the conversation history
    # We create a simple message here, as the full tool_call context is in the main thread.
    tool_message = Message(role="tool", content=tool_result_str)
    conversation.messages.append(tool_message)
    
    # 4. Save the updated conversation state back to Redis
    await session_manager.save_conversation(session_id, conversation)
    
    return tool_result_str

@celery_app.task(name="app.tasks.execute_tool_task")
def execute_tool_task(session_id: str, tool_name: str, tool_args: dict) -> str:
    """
    A Celery task to execute a tool asynchronously.
    It now uses a single asyncio.run() call to manage the entire async workflow.
    """
    console.info(f"[Celery Task {execute_tool_task.request.id}] Started for tool '{tool_name}' in session '{session_id}'.")
    
    try:
        # --- THE CRITICAL FIX ---
        # Run the entire async logic within a single, managed event loop.
        result = asyncio.run(_async_execute_and_save(session_id, tool_name, tool_args))
        
        console.success(f"[Celery Task {execute_tool_task.request.id}] Completed successfully.")
        return result
        
    except Exception as e:
        console.exception(f"[Celery Task {execute_tool_task.request.id}] Failed.")
        raise e