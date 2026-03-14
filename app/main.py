from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Structured Extraction Engine",
    description="Convert unstructured documents into structured JSON using LLMs",
    version="0.1.0",
)

app.include_router(router)