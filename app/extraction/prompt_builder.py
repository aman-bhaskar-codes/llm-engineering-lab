class PromptBuilder:
    @staticmethod
    def build_extraction_prompt(text: str) -> str:
        return f"Extract the requested structured information from the following text:\n\n{text}"