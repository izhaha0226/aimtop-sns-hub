from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/sns_hub"
    REDIS_URL: str = "redis://localhost:6379"
    JWT_SECRET: str = "change-this-secret-min-32-chars-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CORS_ORIGINS: list[str] = ["http://localhost:5000"]
    PORT: int = 5001

    # SNS OAuth - Instagram (Meta)
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""

    # SNS OAuth - YouTube (Google)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # SNS OAuth - X (Twitter)
    X_CLIENT_ID: str = ""
    X_CLIENT_SECRET: str = ""

    # SNS OAuth - Naver Blog
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    # Token encryption key (Fernet)
    TOKEN_ENCRYPT_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    return settings
