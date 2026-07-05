"""
Application configuration.

All values are overridable via environment variables (or a `.env` file in
the backend/ directory). See `.env.example` for the full list.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "VisionGuard AI"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api"

    # --- Security / Auth ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_super_secret_key_visionguard"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- Database ---
    # Defaults to a local SQLite file for zero-config demo mode.
    # For production, set e.g. postgresql://user:pass@host:5432/visionguard
    DATABASE_URL: str = "sqlite:///./visionguard.db"

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # --- ML Model ---
    # "demo"       -> ImageNet-pretrained EfficientNet-B4 backbone with a
    #                 freshly-initialized classification head. The pipeline
    #                 is fully functional end-to-end but predictions are NOT
    #                 clinically meaningful yet.
    # "production" -> loads the fine-tuned checkpoint at MODEL_CHECKPOINT_PATH
    #                 (a timm efficientnet_b4 checkpoint trained on APTOS 2019).
    #                 To use a newer checkpoint later, just overwrite that
    #                 file -- no code changes needed.
    MODEL_MODE: str = "production"
    MODEL_CHECKPOINT_PATH: str = "app/ml/weights/best_model.pth"
    MODEL_IMG_SIZE: int = 380
    MODEL_SEED: int = 42

    # --- File uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
