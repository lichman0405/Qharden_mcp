# The module is to define the API router for the application.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

from fastapi import APIRouter
from app.api.v1.endpoints import session, chat, tasks

api_router = APIRouter()

# Include the session router with a '/session' prefix
api_router.include_router(session.router, prefix="/session", tags=["Session Management"])

# Include the chat router with a '/chat' prefix
api_router.include_router(chat.router, prefix="/chat", tags=["Conversation"])

# Include the tasks router with a '/tasks' prefix
api_router.include_router(tasks.router, prefix="/tasks", tags=["Task Management"])
