# data_pipeline/embedder.py
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

from src.common.config import settings
from src.pgdb.schema import SourceChunk, SourceChunkVec

def embed_and_store_chunks():
    engine = create_engine(settings.database_url)
    
    # BGE-m3 모델 로드 (다국어 지원, 1024차원)
    print("임베딩 모델(BAAI/bge-m3) 로딩 중... (최초 실행 시 가중치 다운로드에 수 분이 소요될 수 있음)")
    model = SentenceTransformer('BAAI/bge-m3')
    
    with Session(engine) as session:
        # 아직 임베딩 벡터가 생성되지 않은 청크들만 선별 (Left Outer Join 후 IS NULL 필터링)
        unprocessed_chunks = session.query(SourceChunk).outerjoin(
            SourceChunkVec, SourceChunk.id == SourceChunkVec.chunk_id
        ).filter(
            SourceChunkVec.chunk_id == None
        ).all()
        
        if not unprocessed_chunks:
            print("새로 임베딩할 청크가 없습니다.")
            return
            
        print(f"총 {len(unprocessed_chunks)}개의 청크 임베딩 연산 시작...")
        
        # 텍스트 리스트 추출
        texts = [chunk.content for chunk in unprocessed_chunks]
        
        # 임베딩 생성 (로컬 CPU/GPU 리소스 활용)
        embeddings = model.encode(texts, show_progress_bar=True)
        
        # 생성된 벡터를 DB에 적재
        inserted_count = 0
        for chunk, vec in zip(unprocessed_chunks, embeddings):
            new_vec = SourceChunkVec(
                chunk_id=chunk.id,
                chunk_vec=vec.tolist(), # pgvector가 인식할 수 있도록 리스트 형태로 변환
                vec_model_name="BAAI/bge-m3"
            )
            session.add(new_vec)
            inserted_count += 1
            
        session.commit()
        print(f"완료: {inserted_count}개의 벡터가 source_chunk_vec 테이블에 적재되었습니다.")

if __name__ == "__main__":
    embed_and_store_chunks()