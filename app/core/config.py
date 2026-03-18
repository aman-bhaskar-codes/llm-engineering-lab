from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    model_name: str = "gemini-1.5-flash"

    class Config:
        env_file = ".env"

settings = Settings()
