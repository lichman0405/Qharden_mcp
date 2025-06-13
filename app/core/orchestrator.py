# app/core/orchestrator.py
# Final version with structured observations to guide the ReAct loop.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 3.2.0

import json
from typing import Dict, Any, Tuple
from uuid import uuid4
from app.models.common import Conversation, Message
from app.services.llm_connector import call_llm
from app.utils.logger import console
from rich.panel import Panel
from app.core.tool_registry import tool_registry
from app.services.session_manager import session_manager
from app.tasks import execute_tool_task

# The System Prompt remains the same as the last version.
SYSTEM_PROMPT = """You are an expert AI assistant for scientific computing. You must follow a strict process to complete tasks.

1.  **Thought**: First, you MUST write down your reasoning and plan in a 'Thought' block. Explain your next step.
2.  **Tool Use**: After your thought, if you need to use a tool, call ONE tool to perform the action.
3.  You will then receive an **Observation** with the result.
4.  Repeat this process until you have the final answer for the user.
5.  When you have the final answer, you MUST start your response with `Final Answer:`.

**Available Tools:**
{tool_definitions}

Begin now.
"""
ASYNC_TOOLS = ["optimize_structure_with_mace", "optimize_structure_with_xtb"]

def _create_observation_message(tool_name: str, status: str, output: Any) -> str:
    """Helper function to create a structured observation string."""
    return (
        f"Observation:\n"
        f"Tool '{tool_name}' completed with status: {status}.\n"
        f"Output: {str(output)}"
    )

async def _execute_tool(tool_name: str, tool_args: dict, conversation: Conversation) -> str:
    """Helper function to execute a single synchronous tool."""
    try:
        console.info(f"Executing sync tool '{tool_name}' directly.")
        result = await tool_registry.execute(tool_name, conversation, tool_args)
        return _create_observation_message(tool_name, "Success", result)
    except Exception as e:
        console.exception(f"Error executing sync tool '{tool_name}'")
        return _create_observation_message(tool_name, "Failure", str(e))

async def run_conversation_step(session_id: str, user_input: str) -> Message:
    MAX_TURNS = 15
    conversation = await session_manager.get_conversation(session_id)
    if not conversation.session_id:
        conversation.session_id = session_id
    
    if not conversation.messages:
        console.info(f"New conversation. Prepending Hybrid ReAct system prompt.")
        tool_defs_string = "\n".join([f"  - `{tool.name}`: {tool.description}" for tool in tool_registry.tools.values()])
        formatted_prompt = SYSTEM_PROMPT.format(tool_definitions=tool_defs_string)
        conversation.messages.append(Message(role="system", content=formatted_prompt))
    
    # Pre-processing of user input is now handled by the file converter tool if needed.
    conversation.messages.append(Message(role="user", content=user_input))
    
    for turn in range(MAX_TURNS):
        console.rule(f"ReAct Turn {turn + 1}")
        await session_manager.save_conversation(session_id, conversation)
        messages_for_llm = [msg.model_dump(exclude_none=True) for msg in conversation.messages]
        
        console.info(f"Calling LLM for session_id: {session_id}...")
        llm_response = await call_llm(messages=messages_for_llm, tools=tool_registry.get_definitions())
        conversation.messages.append(llm_response)
        if llm_response.content:
            console.info(f"Agent's Thought: {llm_response.content}")
        
        if llm_response.content and "Final Answer:" in llm_response.content:
            final_answer = llm_response.content.split("Final Answer:")[-1].strip()
            console.success(f"LLM provided Final Answer for session_id: {session_id}")
            await session_manager.save_conversation(session_id, conversation)
            return Message(role="assistant", content=final_answer, raw_assistant_response=llm_response.content)

        if llm_response.tool_calls:
            tool_call = llm_response.tool_calls[0]
            tool_name = tool_call.function.get("name")
            tool_args = json.loads(tool_call.function.get("arguments", "{}"))
            
            if tool_name is None:
                observation = _create_observation_message("unknown", "Failure", "Tool name is missing")
            else:
                observation = ""
                if tool_name in ASYNC_TOOLS:
                    console.info(f"Dispatching async tool '{tool_name}' to Celery worker.")
                    task = execute_tool_task.delay(session_id, tool_name, tool_args)
                    observation = f"Task '{tool_name}' submitted with ID: {task.id}. You MUST use the 'check_task_status' tool to get the result before proceeding."
                    final_assistant_message = Message(role="assistant", content=observation, raw_assistant_response=f"Thought: I have submitted the asynchronous task '{tool_name}'. I need to inform the user and wait for them to check the status.\n{observation}")
                    conversation.messages.append(final_assistant_message)
                    await session_manager.save_conversation(session_id, conversation)
                    return final_assistant_message
                else:
                    observation = await _execute_tool(tool_name, tool_args, conversation)
            
            observation_message = Message(role="tool", tool_call_id=tool_call.id, content=observation)
            conversation.messages.append(observation_message)
        else:
            console.warning("LLM provided a thought but no tool call. Forcing continuation.")
            force_continue_message = Message(role="user", content="Your thought process is good. Please proceed with the next action based on your plan.")
            conversation.messages.append(force_continue_message)
    
    timeout_message = "I have reached the maximum number of steps without finding a final answer."
    return Message(role="assistant", content=timeout_message)

def get_new_session_id() -> str:
    return str(uuid4())