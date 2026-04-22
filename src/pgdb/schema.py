from datetime import datetime
import enum
from typing import Any, Optional
from sqlalchemy import BigInteger, Integer, String, Text, DateTime, Enum, ForeignKey, UniqueConstraint, Index, Computed, Boolean, text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from pgvector.sqlalchemy import Vector

def set_unique_constraint(table_name: str, columns: list[str]|None=None):
    if not columns:
        raise ValueError("columns must not be empty")
    name = f"uq_{table_name}_{'_'.join(columns)}"
    return UniqueConstraint(*columns, name=name)

class Base(DeclarativeBase):
    pass

class TableBase(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @declared_attr.directive
    def __table_args__(cls):
        return {
            "comment": f"{cls.__tablename__} table"
        }

# ==========================================
# Core RAG Engine Tables
# ==========================================

class SourceChunk(TableBase):
    __tablename__ = "source_chunk"

    content: Mapped[str] = mapped_column(Text, comment="청크 텍스트")
    content_hash: Mapped[str] = mapped_column(String(64), Computed("encode(digest(coalesce(content,''), 'sha256'), 'hex')", persisted=True), comment="자동 생성 SHA256")
    
    # ParadeDB(pg_search)를 사용할 예정이므로 native TSVECTOR는 보조 수단으로 유지하거나, 향후 ParadeDB 인덱스로 완전 대체 가능
    chunk_tsv: Mapped[Any] = mapped_column(TSVECTOR, Computed("to_tsvector('simple', coalesce(content,''))", persisted=True), comment="Native FTS용 TSVECTOR")
    
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chunk_version: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), default=True, index=True, comment="증분 업데이트용 Soft Delete 플래그")

    __table_args__ = (
        set_unique_constraint(__tablename__, ["content_hash", "chunk_index", "chunk_version"]),
        Index("ix_source_chunk_chunk_tsv_gin", "chunk_tsv", postgresql_using="gin"),
    )

class SourceChunkVec(TableBase):
    __tablename__ = "source_chunk_vec"

    chunk_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("source_chunk.id", ondelete="CASCADE"))
    
    # BGE-m3 다국어 모델에 맞춘 1024 차원
    chunk_vec: Mapped[Any] = mapped_column(Vector(1024))
    vec_model_name: Mapped[str] = mapped_column(String(50))

    __table_args__ = (
        set_unique_constraint(__tablename__, ["chunk_id", "vec_model_name"]),
        Index("ix_source_chunk_vec_chunk_id", "chunk_id"),
        Index("ix_source_chunk_vec_chunk_vec_hnsw", "chunk_vec", postgresql_using="hnsw", postgresql_ops={"chunk_vec": "vector_cosine_ops"}),
    )

# ==========================================
# Domain Specific Source Tables
# ==========================================

class SourceName(str, enum.Enum):
    clinical_guideline = "clinical_guideline"
    research_paper = "research_paper"

class MapSourceChunk(TableBase):
    __tablename__ = "map_source_chunk"

    chunk_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("source_chunk.id", ondelete="CASCADE"))
    source_id: Mapped[int] = mapped_column(BigInteger)
    source_name: Mapped[SourceName] = mapped_column(Enum(SourceName, name="source_name_enum", native_enum=True))

    __table_args__ = (
        set_unique_constraint(__tablename__, ["chunk_id", "source_id", "source_name"]),
        Index("ix_map_source_chunk_chunk_id", "chunk_id"),
        Index("ix_map_source_chunk_source_id_source_name", "source_id", "source_name"),
    )

class SourceTableBase(TableBase):
    __abstract__ = True

    content: Mapped[str] = mapped_column(Text, comment="원본 텍스트 전체")
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True, comment="원본 텍스트 sha256 해시")
    process: Mapped[str] = mapped_column(String(20), comment="전처리 단계 (예: parsed, chunked)")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), default=True)

class SourceClinicalGuideline(SourceTableBase):
    __tablename__ = "source_clinical_guideline"

    title: Mapped[str] = mapped_column(String(255))
    issuing_body: Mapped[str] = mapped_column(String(100), comment="발행 기관 (예: ACSM, 대한의학회)")
    publication_year: Mapped[int] = mapped_column(Integer)
    reliability_tier: Mapped[str] = mapped_column(String(20), default="gold_standard", comment="신뢰도 등급")
    disease_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

class SourceResearchPaper(SourceTableBase):
    __tablename__ = "source_research_paper"

    title: Mapped[str] = mapped_column(String(255))
    doi: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    journal: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publication_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[str] = mapped_column(String(10), comment="문서 언어 (en, fr, ko)")

# ==========================================
# Execution & Monitoring
# ==========================================

class RagExecutionLog(TableBase):
    __tablename__ = "rag_execution_log"

    trace_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="Langfuse Trace ID와 매핑")
    user_query: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(50))
    raw_generation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_valid: Mapped[Optional[bool]] = mapped_column(nullable=True, comment="Guardrails/PostCheck 통과 여부")
    error_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnostics: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True, comment="소요 시간, 검색된 청크 ID 등 메타데이터")
    
    is_security_alert: Mapped[bool] = mapped_column(default=False, server_default="false")