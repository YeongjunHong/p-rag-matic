# data_pipeline/chunker.py
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.common.config import settings
from src.pgdb.schema import SourceResearchPaper, SourceChunk, MapSourceChunk, SourceName

def chunk_and_store_papers():
    engine = create_engine(settings.database_url)
    
    # LangChain의 텍스트 스플리터 세팅
    # 의학 논문 특성상 문장이 길 수 있으므로 chunk_size를 넉넉히 잡고,
    # 문장 중간이 잘리지 않도록 separators를 정밀하게 설정
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "? ", "! ", " "],
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len
    )

    with Session(engine) as session:
        # 아직 청킹되지 않은 데이터만 가져오기
        unprocessed_papers = session.query(SourceResearchPaper).filter_by(process="fetched").all()
        
        if not unprocessed_papers:
            print("처리할 새로운 논문 데이터가 없습니다.")
            return

        print(f"총 {len(unprocessed_papers)}건의 논문 청킹 시작...")
        
        total_chunks_created = 0
        
        for paper in unprocessed_papers:
            # 텍스트 스플리터로 초록 쪼개기
            chunks = text_splitter.split_text(paper.content)
            
            for index, chunk_text in enumerate(chunks):
                # 1. SourceChunk 생성 (content_hash와 chunk_tsv는 DB의 Computed 컬럼이 자동 생성함)
                new_chunk = SourceChunk(
                    content=chunk_text,
                    chunk_index=index,
                    chunk_version="v1.0"
                )
                session.add(new_chunk)
                session.flush() # id를 받아오기 위해 먼저 DB에 밀어넣음 (commit은 아님)
                
                # 2. MapSourceChunk 맵핑 브릿지 생성
                mapping = MapSourceChunk(
                    chunk_id=new_chunk.id,
                    source_id=paper.id,
                    source_name=SourceName.research_paper
                )
                session.add(mapping)
                total_chunks_created += 1
                
            # 원본 데이터의 상태를 'chunked'로 업데이트하여 중복 처리 방지
            paper.process = "chunked"
            
        # 모든 작업이 정상적으로 끝났을 때만 커밋 (트랜잭션 보장)
        session.commit()
        print(f"완료: {len(unprocessed_papers)}개의 논문에서 총 {total_chunks_created}개의 청크가 생성 및 맵핑되었습니다.")

if __name__ == "__main__":
    chunk_and_store_papers()