from typing import List

class RecursiveCharacterTextSplitter:
    """
    A simple but effective text splitter that tries to split on natural boundaries.
    """
    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        separators: List[str] = ["\n\n", "\n", " ", ""]
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators

    def split_text(self, text: str) -> List[str]:
        final_chunks = []
        
        # Simple implementation of recursive splitting
        def _split(text, separators):
            if len(text) <= self.chunk_size:
                return [text]
            
            separator = separators[0] if separators else ""
            if separator:
                splits = text.split(separator)
            else:
                # No more separators, just slice by size
                splits = [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]
                return splits

            # Re-assemble splits into chunks of chunk_size
            current_chunk = []
            current_length = 0
            chunks = []
            
            for s in splits:
                if current_length + len(s) + len(separator) > self.chunk_size and current_chunk:
                    chunks.append(separator.join(current_chunk))
                    # Overlap logic (simple)
                    overlap_text = separator.join(current_chunk)[-self.chunk_overlap:] if self.chunk_overlap > 0 else ""
                    current_chunk = [overlap_text, s] if overlap_text else [s]
                    current_length = len(separator.join(current_chunk))
                else:
                    current_chunk.append(s)
                    current_length += len(s) + len(separator)
            
            if current_chunk:
                chunks.append(separator.join(current_chunk))
            
            # Recursively split any chunks that are still too large
            new_chunks = []
            for c in chunks:
                if len(c) > self.chunk_size and len(separators) > 1:
                    new_chunks.extend(_split(c, separators[1:]))
                else:
                    new_chunks.append(c)
            return new_chunks

        return _split(text, self.separators)
