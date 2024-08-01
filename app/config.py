from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    MONGO_INITDB_DATABASE: str
    JWT_PUBLIC_KEY: str
    JWT_PRIVATE_KEY: str
    REFRESH_TOKEN_EXPIRES_IN: int
    ACCESS_TOKEN_EXPIRES_IN: int
    ALGORITHM: str
    CLIENT_ORIGIN: str
    RABBITMQ_URL: str
    FIREBASE_CREDENTIALS_PATH: str
    CELERY_RESULT_BACKEND: str
    REDIS_URL: str

    class Config:
        env_file = "./.env"


settings = Settings()
