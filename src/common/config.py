# src/common/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Database Configurations
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_host: str = Field(default="localhost")
    postgres_port: str = Field(default="5432")
    postgres_db: str = Field(default="rag_db")

    # API Keys
    openrouter_api_key: str = Field(default="")
    
    # Application Configurations
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)

    # NCBI Email (.env에서 주입받도록 하드코딩 제거)
    ncbi_email: str = Field(default="")

    # .env 파일에서 우선적으로 값을 읽어옴 (대소문자 구분 없이 자동 매핑)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """SQLAlchemy에 주입할 DB URL을 동적으로 생성 (psycopg2 드라이버 명시)"""
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

settings = Settings()