import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Centralized configuration for the entire application."""
    
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///ufc_predictions.db")
    
    AUDIT_HOUR: int = int(os.getenv("AUDIT_HOUR", "15"))
    AUDIT_MINUTE: int = int(os.getenv("AUDIT_MINUTE", "0"))
    
settings = Settings()