"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./seo_content.db"
    
    # OpenAI API
    openai_api_key: str
    
    # SERP API (optional - legacy, kept for backward compatibility)
    serp_api_key: str | None = None
    serp_api_provider: str = "serpapi"  # serpapi or valueserp
    
    # TinyFish API (preferred for SERP data)
    tinyfish_api_key: str | None = None
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    
    # LLM Settings
    llm_model: str = "gpt-4o"  # or "gpt-4-turbo" or "gpt-3.5-turbo"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096


settings = Settings()
