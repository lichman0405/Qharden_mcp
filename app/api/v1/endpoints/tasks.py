# This module provides API endpoints for interacting with background tasks.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 0.1.0

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional
from app.worker import celery_app
from celery.result import AsyncResult

router = APIRouter()

class TaskStatusResponse(BaseModel):
    """Defines the response body for the task status endpoint."""
    task_id: str
    status: str
    result: Optional[Any] = None

@router.get("/status/{task_id}", 
            response_model=TaskStatusResponse,
            summary="Check Task Status",
            tags=["Task Management"])
def get_task_status(task_id: str):
    """
    Retrieves the status and result of a background task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    result = None
    if task_result.ready():
        if task_result.successful():
            result = task_result.get()
        else:
            # Task failed, result is the exception
            try:
                task_result.get()
            except Exception as e:
                result = str(e)

    return TaskStatusResponse(
        task_id=task_id,
        status=task_result.state,
        result=result
    )