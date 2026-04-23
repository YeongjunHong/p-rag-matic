from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # Database Configurations
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: str = Field(default="5432")
    POSTGRES_DB: str = Field(default="rag_db")

    # API Keys
    OPENROUTER_API_KEY: str = Field(default="")
    
    # Application Configurations
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # NCBI Email 추가
    ncbi_email: str = "yjayhong37@gmail.com"  

    # .env 파일에서 우선적으로 값을 읽어옴
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """SQLAlchemy에 주입할 DB URL을 동적으로 생성"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()