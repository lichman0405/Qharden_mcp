# The module is to define the API endpoints for session management.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0


from fastapi import APIRouter
from app.core.orchestrator import get_new_session_id
from app.utils.logger import console
from app.models.api_models import NewSessionResponse

router = APIRouter()

@router.post("/new", 
          response_model=NewSessionResponse)
def create_new_session():
    """
    Initializes a new session and returns a unique session ID.
    """
    session_id = get_new_session_id()
    console.info(f"New session created: {session_id}")
    return NewSessionResponse(
        session_id=session_id, 
        message="New session created successfully."
    )