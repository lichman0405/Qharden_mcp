# app/core/orchestrator.py
# The orchestrator module, refactored to implement a more robust ReAct agent loop.
# Author: Shibo Li 
# Date: 2025-06-13
# Version: 2.1.0

import json
import re
from typing import Dict, Any, Tuple, Optional
from uuid import uuid4
from app.models.common import Conversation, Message
from app.services.llm_connector import call_llm
from app.utils.logger import console
from app.core.tool_registry import tool_registry
from app.services.session_manager import session_manager
from app.tasks import execute_tool_task

SYSTEM_PROMPT = """You are an expert AI assistant for scientific computing. You must follow a strict format to complete tasks.

**Your operational loop is: Thought -> Action -> Observation.**

1.  **Thought**: Reason about the user's request and your next step. Be concise.
2.  **Action**: Choose ONE tool from the list below to execute. The action format MUST be a single line: `Action: tool_name(arg1="value", arg2=123)`
3.  You will then receive an **Observation** with the result of your action.
4.  Repeat this loop until you have the final answer for the user.
5.  When you are ready to give the final answer, you MUST use the format: `Final Answer: [Your complete response]`

**Available Tools:**
{tool_definitions}

**Constraint Checklist & Confidence Score:**
1. Did I double-check the tool's description for input format requirements (e.g., .cif vs .xyz)? Yes.
2. Is my `Action:` a single line with the exact format `Action: tool_name(key="value")`? Yes.
3. Am I confident I can proceed? Yes.

Begin now.
"""


ASYNC_TOOLS = [
    "optimize_structure_with_mace",
    "optimize_structure_with_xtb",
]

# --- MODIFICATION 2: A more robust Action Parser ---
def _parse_action(response_text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Parses the Action string from the LLM's response using a more flexible regex."""
    action_pattern = re.compile(r"Action:\s*(\w+)\((.*?)\)", re.DOTALL)
    match = action_pattern.search(response_text)
    
    if not match:
        return None
        
    tool_name = match.group(1).strip()
    tool_args_str = match.group(2).strip()
    
    try:
        if not tool_args_str:
            return tool_name, {}
        args = {}
        arg_pattern = re.compile(r'(\w+)\s*=\s*(".*?"|\'.*?\'|[^,]+(?=\s*,\s*\w+\s*=|$))')
        for key, value in arg_pattern.findall(tool_args_str):
            try:
                args[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                args[key] = value.strip().strip("'\"")
        return tool_name, args
    except Exception as e:
        console.error(f"Failed to parse action arguments: '{tool_args_str}'. Error: {e}")
        return None


async def _execute_action(action: Tuple[str, Dict[str, Any]], conversation: Conversation) -> str:
    """Executes a parsed action, either synchronously or asynchronously."""
    tool_name, tool_args = action
    
    if tool_name in ASYNC_TOOLS:
        console.info(f"Dispatching async tool '{tool_name}' to Celery worker.")
        task = execute_tool_task.delay(
            session_id=conversation.session_id,
            tool_name=tool_name,
            tool_args=tool_args
        )
        return f"Task '{tool_name}' submitted with ID: {task.id}. Use 'check_task_status' to get the result."
    else:
        console.info(f"Executing sync tool '{tool_name}' directly.")
        try:
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
    """Runs the main ReAct conversation loop."""
    MAX_TURNS = 10
    
    conversation = await session_manager.get_conversation(session_id)
    if not conversation.session_id:
        conversation.session_id = session_id
    
    if not conversation.messages:
        console.info(f"New conversation. Prepending ReAct system prompt for session_id: {session_id}")
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
        llm_response = await call_llm(messages=messages_for_llm)
        
        assistant_response_text = llm_response.content or ""
        conversation.messages.append(Message(role="assistant", content=assistant_response_text))
        
        if "Final Answer:" in assistant_response_text:
            final_answer = assistant_response_text.split("Final Answer:")[-1].strip()
            console.success(f"LLM provided Final Answer for session_id: {session_id}")
            await session_manager.save_conversation(session_id, conversation)
            return Message(role="assistant", content=final_answer)

        action = _parse_action(assistant_response_text)
        if action:
            observation = await _execute_action(action, conversation)
            observation_message = Message(role="user", content=f"Observation: {observation}")
            conversation.messages.append(observation_message)
        else:

            console.warning("LLM did not produce a valid action or final answer. Ending loop.")
            return Message(role="assistant", content="I seem to be stuck. Could you please clarify or rephrase your request?")

    timeout_message = "I have reached the maximum number of steps without finding a final answer. Please try reformulating your request."
    console.warning(timeout_message)
    return Message(role="assistant", content=timeout_message)


def get_new_session_id() -> str:
    """Generates a new, unique session ID."""
    return str(uuid4())