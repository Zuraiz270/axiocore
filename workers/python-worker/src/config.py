from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    worker_name: str = "axiocore-worker-1"
    redis_url: str = "redis://localhost:6379"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "password"
    
    class Config:
        env_file = ".env"

settings = Settings()
