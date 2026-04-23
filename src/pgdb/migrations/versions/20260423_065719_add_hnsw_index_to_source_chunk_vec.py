"""Add HNSW index to source_chunk_vec

Revision ID: 060620d4b902
Revises: c3999c6ed0ca
Create Date: 2026-04-23 06:57:19.026994+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '060620d4b902'
down_revision: Union[str, Sequence[str], None] = 'c3999c6ed0ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 코사인 유사도(vector_cosine_ops) 기반의 HNSW 인덱스 생성
    # m: 노드당 최대 연결 수 (기본값 16, 높을수록 정확도 증가/메모리 증가)
    # ef_construction: 인덱스 생성 시 탐색 범위 (기본값 64)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_source_chunk_vec_hnsw 
        ON source_chunk_vec 
        USING hnsw (chunk_vec vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64);
    """)

def downgrade() -> None:
    # 롤백 시 인덱스 삭제
    op.execute("DROP INDEX IF EXISTS ix_source_chunk_vec_hnsw;")
