import os

class Settings:
    PROJECT_NAME: str = "Viagem Otimizada API"
    PROJECT_VERSION: str = "1.0.0"

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-it")
    ALGORITHM: str = "HS256"
    # Default session length: 7 days (in minutes)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    AMADEUS_API_KEY: str = os.getenv("AMADEUS_API_KEY", "")
    AMADEUS_API_SECRET: str = os.getenv("AMADEUS_API_SECRET", "")

settings = Settings()
