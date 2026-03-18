from fastapi import FastAPI
from app.api.routes import router as extraction_router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Structured Extraction Engine",
    description="Engine for generating structured extraction using LLMs",
    version="0.1.0",
)

app.include_router(extraction_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy"}