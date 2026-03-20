from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import uuid

from fastapi import Request
from api.routes import router as extraction_router
from api.auth_routes import router as auth_router
from core.logging import setup_logging
from core.logging import set_correlation_id

from core.redis import redis_manager
from memory.graph_memory import graph_memory
from core.error_handler import global_exception_handler
from loguru import logger

# setup_logging() # We'll replace this with loguru

async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing system...")
    await redis_manager.connect()
    await graph_memory.connect()
    
    from worker import _get_redis_pool
    app.state.redis_pool = await _get_redis_pool()
    
    yield
    
    # Shutdown
    if app.state.redis_pool:
        await app.state.redis_pool.close()
    await redis_manager.disconnect()
    await graph_memory.close()
    logger.info("System shutdown complete.")

app = FastAPI(
    title="Structured Extraction Engine",
    description="Engine for generating structured extraction using LLMs",
    version="0.1.0",
    lifespan=lifespan
)

app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extraction_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    set_correlation_id(cid)
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = cid
        return response
    finally:
        # No explicit reset needed; ContextVar is per-context.
        pass

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)