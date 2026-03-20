from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    model_name: str = "gemini-1.5-flash"

    # Platform persistence
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/structured_extraction_engine"

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24h
    refresh_token_expire_days: int = 7

    # Cache (Redis)
    redis_url: str = "redis://localhost:6379/0"

    # Neo4j relationship memory
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Ollama (local LLM fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_name: str = "qwen2.5:3b"

    class Config:
        env_file = ".env"

settings = Settings()
