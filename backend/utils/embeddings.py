import os
from typing import List
import google.generativeai as genai
from core.config import settings

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

async def get_embedding(text: str) -> List[float]:
    """
    Get embedding from Gemini.
    """
    if not text:
        return []
    
    try:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document",
            title="Semantic Memory Entry"
        )
        return result['embedding']
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Batch get embeddings for multiple strings.
    """
    if not texts:
        return []
        
    try:
        result = genai.embed_content(
            model="models/embedding-001",
            content=texts,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception:
        return [[] for _ in texts]
