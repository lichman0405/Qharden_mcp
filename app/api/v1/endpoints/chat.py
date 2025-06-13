# The module is to define the API endpoints for chat interactions.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

from fastapi import APIRouter
from app.core.orchestrator import run_conversation_step
from app.utils.logger import console
from app.models.api_models import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/", 
          response_model=ChatResponse)
async def chat_with_mcp(request: ChatRequest):
    """
    Handles a single turn in a conversation.
    """
    console.info(f"Received chat request for session_id: {request.session_id}")
    
    assistant_message = await run_conversation_step(
        session_id=request.session_id,
        user_input=request.user_input
    )
    
    console.success(f"Sending response for session_id: {request.session_id}")
    
    return ChatResponse(
        session_id=request.session_id,
        role=assistant_message.role,
        content=str(assistant_message.content)
    )