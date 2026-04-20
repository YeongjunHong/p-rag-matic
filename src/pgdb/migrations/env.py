# src/pgdb/migrations/env.py

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# --- [추가/수정 구역 시작] ---
import sys
import os

# 프로젝트 루트(p-rag-matic)를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.config import settings
# from src.pgdb.schema import Base  # <- 이 부분은 다음 단계에서 스키마 작성 후 주석 해제

config = context.config

# 하드코딩된 URL 대신 config.py에서 동적으로 생성된 DB URL 주입
config.set_main_option("sqlalchemy.url", settings.database_url)
# --- [추가/수정 구역 끝] ---

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata = Base.metadata  # <- 스키마 작성 후 주석 해제
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
