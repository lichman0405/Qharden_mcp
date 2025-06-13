# The orchestrator module is responsible for managing the conversation flow.
# It now uses an automatic tool registry and a system prompt for behavior guidance.
# Author: Shibo Li
# Date: 2025-06-12
# Version: 0.1.0

import json
import re
from typing import Optional, Tuple, Dict, Any
from uuid import uuid4
from app.models.common import Conversation, Message, ToolCall
from app.services.llm_connector import call_llm
from app.utils.logger import console
from app.core.tool_registry import tool_registry
from app.services.session_manager import session_manager
from app.tasks import execute_tool_task

# System prompt to guide the assistant's behavior
SYSTEM_PROMPT = """
You are a helpful and meticulous AI assistant, an expert in chemistry, materials science, and scientific computation. Your goal is to assist users by answering their questions and performing complex tasks.

To do this, you will operate in a loop of Thought, Action, and Observation. You must always follow this format.

At each step, you must first use a "Thought" to reason about the user's request and your plan. Then, you must output an "Action" to take. After you perform an action, you will be given an "Observation" with the result. You will use this observation to continue your thought process.

You have access to the following tools:
{tool_definitions}

The format for an Action MUST be `tool_name(arg1=value1, arg2="value2", ...)` as a plain string.

Here is an example of a conversation:

User: "Hello, can you tell me about the Python library called 'httpx' and also convert its documentation page URL into a CIF file?"

Thought: The user has two requests. First, to get information about the 'httpx' library, and second, to convert a URL into a CIF file, which is a nonsensical task. I should first perform the valid request, which is searching for 'httpx'. I will use the `tavily_search` tool for that. For the second request, I will point out that it's not a logical operation.
Action: tavily_search(query="python library httpx")

Observation: [tavily_search result with URLs and content snippets]

Thought: I have successfully found information about httpx. I can now answer the user's first question. For the second part of the request, converting a URL to a CIF file is not a valid chemical operation, so I should inform the user about this. I have all the information needed to provide a complete answer.
Final Answer: The Python library 'httpx' is a modern, high-performance HTTP client for Python, designed to be intuitive and support both sync and async operations. It's often considered a successor to the popular 'requests' library.

Regarding your second request, converting a URL into a CIF (Crystallographic Information File) is not a standard or logical operation, as CIF files describe atomic structures.

If you have a structure you'd like me to analyze or convert, please let me know!

You will now begin. Remember to ALWAYS use the Thought and Action format.
"""

# Tasks should be run asynchronously if they are long-running or resource-intensive.
ASYNC_TOOLS = [
    "optimize_structure_with_mace",
    "download_optimized_structure",
    "optimize_structure_with_xtb",
    "download_xtb_optimization_result",
]


def _parse_action(response_text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Parses the Action string from the LLM's response using regex."""
    action_pattern = re.compile(r"Action:\s*(\w+)\((.*)\)")
    match = action_pattern.search(response_text)
    
    if not match:
        return None
        
    tool_name = match.group(1).strip()
    tool_args_str = match.group(2).strip()
    
    try:
        if not tool_args_str:
            return tool_name, {}
        # A simple parser for 'key="value", key2=123' style arguments.
        # This is more robust than the previous suggestion.
        args = {}
        # Use regex to find all key=value pairs
        arg_pattern = re.compile(r'(\w+)\s*=\s*(".*?"|\'.*?\'|[^,]+)')
        for key, value in arg_pattern.findall(tool_args_str):
            # Use json.loads to handle numbers, booleans, and quoted strings correctly
            try:
                args[key] = json.loads(value)
            except json.JSONDecodeError:
                # Fallback for unquoted strings
                args[key] = value.strip("'\"")
        return tool_name, args
    except Exception as e:
        console.error(f"Failed to parse action arguments: {tool_args_str}. Error: {e}")
        return None


async def _execute_tool_call(tool_name: str, tool_args: dict, conversation: Conversation) -> Message:
    """
    Executes a tool call, deciding whether to run it synchronously or
    dispatch it as an asynchronous background task.
    """
    if tool_name in ASYNC_TOOLS:
        console.info(f"Dispatching async tool '{tool_name}' to Celery worker.")
        task = execute_tool_task.delay(
            session_id=conversation.session_id,
            tool_name=tool_name,
            tool_args=tool_args
        )
        response_content = f"The long-running task '{tool_name}' has been submitted successfully. The task ID is {task.id}. Use the 'check_task_status' tool to check for its completion."
        # This now returns a simple string, which will be wrapped in an Observation message.
        return Message(role="tool", content=response_content)
    else:
        console.info(f"Executing sync tool '{tool_name}' directly.")
        tool_result = await tool_registry.execute(
            tool_name=tool_name, 
            conversation=conversation,
            kwargs=tool_args
        )
        return Message(role="tool", content=str(tool_result))


async def run_conversation_step(session_id: str, user_input: str) -> Message:
    """
    Runs the main ReAct conversation loop.
    """
    MAX_TURNS = 10 # Add a safety limit
    
    conversation = await session_manager.get_conversation(session_id)
    if not conversation.session_id:
        conversation.session_id = session_id
        console.info(f"New conversation. Prepending ReAct system prompt for session_id: {session_id}")
        # Format the system prompt with actual tool definitions
        tool_defs_string = "\n".join([f"- {tool.name}: {tool.description}" for tool in tool_registry.tools.values()])
        formatted_prompt = SYSTEM_PROMPT.format(tool_definitions=tool_defs_string)
        system_message = Message(role="system", content=formatted_prompt)
        conversation.messages.append(system_message)
    
    conversation.messages.append(Message(role="user", content=user_input))
    await session_manager.save_conversation(session_id, conversation)

    for turn in range(MAX_TURNS):
        console.rule(f"ReAct Turn {turn + 1}")
        
        messages_for_llm = [msg.model_dump(exclude_none=True) for msg in conversation.messages]
        
        console.info(f"Calling LLM for session_id: {session_id}...")
        
        # --- MODIFICATION: We no longer pass the 'tools' parameter ---
        # This encourages the LLM to generate text in the ReAct format.
        llm_response = await call_llm(messages=messages_for_llm)
        
        assistant_response_text = llm_response.content or ""
        conversation.messages.append(Message(role="assistant", content=assistant_response_text))
        
        # Check if the LLM has finished and provided the final answer.
        if "Final Answer:" in assistant_response_text:
            final_answer = assistant_response_text.split("Final Answer:")[-1].strip()
            console.success(f"LLM provided Final Answer for session_id: {session_id}")
            await session_manager.save_conversation(session_id, conversation)
            # We return the final answer wrapped in a standard Message object
            return Message(role="assistant", content=final_answer)

        # If not finished, parse the action from the response text.
        action = _parse_action(assistant_response_text)
        
        if action:
            tool_name, tool_args = action
            # Execute the action and get the observation
            observation = await _execute_tool_call(tool_name, tool_args, conversation)
            
            # Append the observation to the conversation history for the next loop.
            # We use role 'user' for Observation to follow the standard ReAct prompt flow.
            observation_message = Message(role="user", content=f"Observation: {observation}")
            conversation.messages.append(observation_message)
            await session_manager.save_conversation(session_id, conversation)
        else:
            # If the LLM produces text without a valid Action or Final Answer, we end the loop.
            console.warning("LLM did not produce a valid action or final answer. Ending loop.")
            return Message(role="assistant", content="I seem to be stuck. Could you please clarify or rephrase your request?")

    # If the loop finishes due to MAX_TURNS, return a timeout message.
    timeout_message = "I have reached the maximum number of steps without finding a final answer. Please try reformulating your request."
    console.warning(timeout_message)
    return Message(role="assistant", content=timeout_message)

def get_new_session_id() -> str:
    """Generates a new, unique session ID."""
    console.info("Generating new session ID.")
    return str(uuid4())