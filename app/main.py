# The module provides a FastAPI application that serves as the main entry point for the MCP server.
# Author: Shibo Li
# Date: 2025-06-11
# Version: 0.1.0

from fastapi import FastAPI
from app.api.v1.api import api_router
from app.utils.logger import console

app = FastAPI(
    title="MCP Server",
    version="1.0.0",
    description="A modular and extensible Multi-Capability Platform server.",
)

@app.get("/", summary="Health Check", tags=["Status"])
def read_root():
    """Root endpoint to check if the service is alive."""
    console.info("Health check endpoint was hit.")
    return {"message": "MCP Server is alive and running!"}

# Include the v1 router with a global '/v1' prefix
app.include_router(api_router, prefix="/v1")