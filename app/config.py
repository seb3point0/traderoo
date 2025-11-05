"""
Configuration management using pydantic-settings
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    
    # Trading Configuration
    paper_trading: bool = True
    max_position_size: float = 1000.0
    risk_per_trade: float = 0.02
    max_daily_loss: float = 500.0
    max_open_positions: int = 5
    
    # Exchange API Keys
    binance_api_key: str = ""
    binance_api_secret: str = ""
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./trading.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # AI/LLM Configuration
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    use_ai_analysis: bool = False
    ai_confidence_threshold: int = 60  # Minimum confidence (0-100) to execute trades
    ai_cache_ttl: int = 14400  # Cache TTL in seconds (4 hours)
    
    # Data Sources - News & Sentiment
    cryptopanic_api_key: str = "free"  # Free tier available
    lunarcrush_api_key: Optional[str] = None  # Optional paid API
    glassnode_api_key: Optional[str] = None  # Optional paid API
    coingecko_api_key: Optional[str] = None
    dex_screener_api_key: Optional[str] = None
    defillama_api_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trading_bot.log"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

