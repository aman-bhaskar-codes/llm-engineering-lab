from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger
import traceback

async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to ensure consistent error responses.
    """
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "success": False}
        )
    
    # Unexpected errors
    logger.error(f"Unexpected error: {exc}\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please contact support.",
            "success": False
        }
    )
