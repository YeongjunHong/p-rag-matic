from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
import uuid

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    source_uri = Column(String(512), nullable=True, comment="파일 경로 또는 URL")
    
    # 원본 텍스트 및 메타데이터
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, default={}, comment="저자, 출판일, 카테고리 등 유연한 데이터")
    
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=text("now()"))

    # Chunk와의 1:N 관계
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    chunk_index = Column(Integer, nullable=False, comment="문서 내 청크 순서")
    content = Column(Text, nullable=False)
    
    # Vector 컬럼 (pgvector) - 차원(dimension)은 임베딩 모델에 따라 변경 필요
    embedding = Column(Vector(1024), nullable=True) 
    
    metadata_ = Column("metadata", JSONB, default={}, comment="페이지 번호, 헤딩 정보 등 청크 특화 데이터")

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    document = relationship("Document", back_populates="chunks")