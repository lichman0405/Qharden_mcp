# app/core/orchestrator.py
# Final version implementing a robust Hybrid ReAct agent loop with file pre-processing.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 3.1.0

import json
import re
from uuid import uuid4
from app.models.common import Conversation, Message, ToolCall
from app.services.llm_connector import call_llm
from app.utils.logger import console
from app.core.tool_registry import tool_registry
from app.services.session_manager import session_manager
from app.tasks import execute_tool_task

# --- System Prompt for Hybrid ReAct ---
SYSTEM_PROMPT = """You are an expert AI assistant for scientific computing. You must follow a strict process to complete tasks.

1.  **Thought**: First, you MUST write down your reasoning and plan in a 'Thought' block. Explain your next step.
2.  **Tool Use**: After your thought, if you need to use a tool, call ONE tool to perform the action using the structured tool_calls format.
3.  You will then receive an **Observation** with the result of your action.
4.  Repeat this process until you have the final answer for the user.
5.  When you have the final answer, you MUST start your response with `Final Answer:`.

**Available Tools:**
{tool_definitions}

Begin now.
"""

# --- List of tools to be run asynchronously ---
ASYNC_TOOLS = [
    "optimize_structure_with_mace",
    "optimize_structure_with_xtb",
]

# --- NEW: Helper function to pre-process user input for files ---
def _extract_and_save_files(user_input: str, conversation: Conversation) -> str:
    """
    Scans user input for a filename and a base64 string, saves it to the workspace,
    and replaces the base64 content with a placeholder.
    """
    # Regex to find a filename, e.g., '名为 "test.cif"' or 'filename is test.cif'
    filename_pattern = re.compile(r"(?:名为|filename is)\s*['\"](.*?)['\"]")
    # A simple regex to find long base64-like strings
    base64_pattern = re.compile(r"([a-zA-Z0-9+/=\n]{50,})")

    filenames = filename_pattern.findall(user_input)
    base64_contents = base64_pattern.findall(user_input)

    # Clean the found base64 string by removing newlines
    cleaned_content_b64 = ""
    if base64_contents:
        cleaned_content_b64 = "".join(base64_contents[0].split())

    if filenames and cleaned_content_b64:
        filename = filenames[0]
        
        # Save the file content to the workspace
        conversation.workspace[filename] = cleaned_content_b64
        console.info(f"Auto-detected and saved file '{filename}' to workspace from user input.")

        # Replace the long base64 string with a simple placeholder for the LLM
        cleaned_input = user_input.replace(base64_contents[0], f"<content of file '{filename}' is now in workspace>")
        return cleaned_input
        
    return user_input # No files found, return original input

async def _execute_tool(tool_name: str, tool_args: dict, conversation: Conversation) -> str:
    """Helper function to execute a single synchronous tool."""
    try:
        console.info(f"Executing sync tool '{tool_name}' directly.")
        result = await tool_registry.execute(
            tool_name=tool_name, 
            conversation=conversation,
            kwargs=tool_args
        )
        return str(result)
    except Exception as e:
        console.exception(f"Error executing sync tool '{tool_name}'")
        return f"Error: {e}"

async def run_conversation_step(session_id: str, user_input: str) -> Message:
    """
    Runs the main Hybrid ReAct conversation loop.
    """
    MAX_TURNS = 10
    
    conversation = await session_manager.get_conversation(session_id)
    if not conversation.session_id:
        conversation.session_id = session_id
    
    if not conversation.messages:
        console.info(f"New conversation. Prepending Hybrid ReAct system prompt.")
        tool_defs_string = "\n".join([f"  - `{tool.name}`: {tool.description}" for tool in tool_registry.tools.values()])
        formatted_prompt = SYSTEM_PROMPT.format(tool_definitions=tool_defs_string)
        system_message = Message(role="system", content=formatted_prompt)
        conversation.messages.append(system_message)
    
    conversation.messages.append(Message(role="user", content=user_input))
    
    for turn in range(MAX_TURNS):
        console.rule(f"ReAct Turn {turn + 1}")
        
        await session_manager.save_conversation(session_id, conversation)
        messages_for_llm = [msg.model_dump(exclude_none=True) for msg in conversation.messages]
        
        console.info(f"Calling LLM for session_id: {session_id}...")
        
        llm_response = await call_llm(
            messages=messages_for_llm,
            tools=tool_registry.get_definitions()
        )
        
        conversation.messages.append(llm_response)

        if llm_response.content:
            console.info(llm_response.content)
        
        if llm_response.content and "Final Answer:" in llm_response.content:
            final_answer = llm_response.content.split("Final Answer:")[-1].strip()
            console.success(f"LLM provided Final Answer for session_id: {session_id}")
            await session_manager.save_conversation(session_id, conversation)
            return Message(role="assistant", content=final_answer, raw_assistant_response=llm_response.content)

        if llm_response.tool_calls:
            tool_call = llm_response.tool_calls[0]
            tool_name = tool_call.function.get("name")
            tool_args = json.loads(tool_call.function.get("arguments", "{}"))
            
            observation = ""
            if tool_name in ASYNC_TOOLS:
                console.info(f"Dispatching async tool '{tool_name}' to Celery worker.")
                task = execute_tool_task.delay(session_id, tool_name, tool_args)
                observation = f"Task '{tool_name}' submitted with ID: {task.id}. You MUST use the 'check_task_status' tool to get the result before proceeding."
                # This is a final action for this turn, so we create a response and return
                final_assistant_message = Message(role="assistant", content=observation, raw_assistant_response=f"Thought: I have submitted the asynchronous task '{tool_name}'. I need to inform the user and wait for them to check the status.\n{observation}")
                conversation.messages.append(final_assistant_message)
                await session_manager.save_conversation(session_id, conversation)
                return final_assistant_message
            else:
                observation = await _execute_tool(tool_name, tool_args, conversation)
            
            observation_message = Message(role="tool", tool_call_id=tool_call.id, content=observation)
            conversation.messages.append(observation_message)
        else:
            # --- THE CRITICAL FIX IS HERE ---
            # If the LLM has a thought but calls no tool, it might be stuck.
            # We add a new "user" message to force it to proceed.
            console.warning("LLM provided a thought but no action. Forcing continuation.")
            force_continue_message = Message(role="user", content="Continue with the next action based on your plan.")
            conversation.messages.append(force_continue_message)


    timeout_message = "I have reached the maximum number of steps without finding a final answer. Please try reformulating your request."
    return Message(role="assistant", content=timeout_message)

def get_new_session_id() -> str:
    """Generates a new, unique session ID."""
    return str(uuid4())