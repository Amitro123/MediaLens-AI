"""Application configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from dotenv import load_dotenv
import os

# Explicitly load .env file
# Try loading from current directory or parent directory to handle different runtime contexts
env_path = Path(".env")
if not env_path.exists():
    env_path = Path("backend/.env")
if not env_path.exists():
    env_path = Path("../.env")

# Check if file exists before loading to avoid warnings, though load_dotenv handles missing files gracefully
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback: try loading without path (defaults to .env in cwd)
    load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Google Gemini API
    gemini_api_key: str
    
    # Groq STT API
    groq_api_key: str = ""  # Optional, fallback to Gemini if empty
    
    # Application Settings
    upload_dir: str = "./uploads"
    frame_interval: int = 5  # Extract 1 frame every N seconds
    max_video_length: int = 900  # 15 minutes in seconds
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Acontext Configuration (Flight Recorder)
    # Set to True when running with docker-compose infrastructure
    acontext_url: str = "http://localhost:8029/api/v1"
    acontext_api_key: str = "sk-ac-your-root-api-bearer-token"
    acontext_enabled: bool = False  # Disabled by default for local dev
    
    # Fast STT Configuration
    fast_stt_enabled: bool = True  # Use local Whisper for fast transcription
    fast_stt_model: str = "small"  # "tiny", "base", "small", "medium"
    
    # Gemini Model Configuration
    doc_model_pro_name: str = "gemini-2.5-flash-lite"  # High-quality model for documentation
    doc_model_flash_name: str = "gemini-2.5-flash-lite"  # Fast model for analysis
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def get_upload_path(self) -> Path:
        """Get upload directory as Path object, create if doesn't exist"""
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton instance
settings = Settings()
