# src/rag/core/types.py
from pydantic import BaseModel, Field
from typing import Dict, Any, List

class SourceChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RagRequest(BaseModel):
    user_query: str
    safety_level: str = "default"

class RagContext(BaseModel):
    plan_id: str = "default"
    plan: Dict[str, Any] = Field(default_factory=dict)
    retrieved_chunks: List[SourceChunk] = Field(default_factory=list)

class RagResponse(BaseModel):
    answer: str
    source_nodes: List[SourceChunk] = Field(default_factory=list)