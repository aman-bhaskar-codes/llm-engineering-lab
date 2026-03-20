import logging
from typing import List

logger = logging.getLogger(__name__)

class Chunker:
    def __init__(self, chunk_size: int = 4000, overlap: int = 500):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        if not text:
            return []
            
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += (self.chunk_size - self.overlap)
            
        logger.info(f"Chunker: Split text into {len(chunks)} chunks.")
        return chunks