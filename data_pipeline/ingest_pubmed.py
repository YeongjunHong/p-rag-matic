# data_pipeline/ingest_pubmed.py
import os
import sys
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가하여 src 모듈 임포트 허용
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from Bio import Entrez

from src.common.config import settings
from src.pgdb.schema import SourceResearchPaper

# 보안 적용: .env에서 이메일 가져오기 (NCBI 규정 준수)
Entrez.email = settings.ncbi_email 

def fetch_pubmed_papers(query: str, max_results: int = 10):
    """PubMed API를 검색하여 논문 메타데이터와 초록을 가져온다."""
    print(f" 검색어 '{query}'로 PubMed 검색 중... (최대 {max_results}건)")
    
    # 1. 검색 (Search)
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()
    
    id_list = record["IdList"]
    if not id_list:
        print(" 검색 결과가 없습니다.")
        return []

    print(f" {len(id_list)}건의 논문 ID를 찾았습니다. 상세 데이터 추출 시작...")
    
    # 2. 상세 정보 추출 (Fetch)
    handle = Entrez.efetch(db="pubmed", id=id_list, retmode="xml")
    papers = Entrez.read(handle)
    handle.close()
    
    results = []
    for paper in papers['PubmedArticle']:
        medline = paper['MedlineCitation']
        article = medline['Article']
        
        # 초록(Abstract) 추출 (초록이 없는 논문은 스킵하여 데이터 품질 유지)
        if 'Abstract' not in article or 'AbstractText' not in article['Abstract']:
            continue
            
        abstract_texts = article['Abstract']['AbstractText']
        content = " ".join([str(text) for text in abstract_texts])
        
        # 메타데이터 추출
        title = article.get('ArticleTitle', 'No Title')
        journal = article.get('Journal', {}).get('Title', 'Unknown Journal')
        
        # DOI 추출
        doi = "Unknown"
        if 'ELocationID' in article:
            for eloc in article['ELocationID']:
                if eloc.attributes.get('EIdType') == 'doi':
                    doi = str(eloc)
                    break
        
        # 저자 추출 (최대 3명만)
        authors_list = []
        if 'AuthorList' in article:
            for author in article['AuthorList'][:3]:
                if 'LastName' in author and 'Initials' in author:
                    authors_list.append(f"{author['LastName']} {author['Initials']}")
        authors_str = ", ".join(authors_list) + (" et al." if len(article.get('AuthorList', [])) > 3 else "")

        results.append({
            "title": title,
            "doi": doi,
            "authors": authors_str,
            "journal": journal,
            "publication_date": datetime.now().strftime("%Y-%m"), # 단순화를 위해 수집 시점으로 대체
            "language": "en",
            "content": content,
            "process": "fetched"
        })
        
    return results

def ingest_to_db(papers_data: list):
    """추출한 데이터를 DB에 적재한다."""
    if not papers_data:
        return

    engine = create_engine(settings.database_url)
    
    with Session(engine) as session:
        inserted_count = 0
        for data in papers_data:
            # 중복 DOI 방지 (멱등성 보장)
            exists = session.query(SourceResearchPaper).filter_by(doi=data['doi']).first()
            if exists or data['doi'] == "Unknown":
                continue
                
            new_paper = SourceResearchPaper(
                title=data['title'],
                doi=data['doi'],
                authors=data['authors'],
                journal=data['journal'],
                publication_date=data['publication_date'],
                language=data['language'],
                content=data['content'],
                process=data['process']
            )
            session.add(new_paper)
            inserted_count += 1
            
        session.commit()
        print(f" 성공적으로 {inserted_count}건의 논문이 DB에 적재되었습니다!\n")

if __name__ == "__main__":
    # 스포츠 부상 통계 기반 타겟 쿼리 리스트 (각 부위별 핵심 키워드 + 재활)
    target_queries = [
        # 무릎 (Knee)
        '"anterior cruciate ligament"[Title/Abstract] AND rehabilitation[Title/Abstract]',
        '"meniscus tear"[Title/Abstract] AND physical therapy[Title/Abstract]',
        # 발목 (Ankle)
        '"lateral ankle sprain"[Title/Abstract] AND exercise therapy[Title/Abstract]',
        # 어깨 (Shoulder)
        '"rotator cuff tear"[Title/Abstract] AND return to sport[Title/Abstract]',
        # 햄스트링 (Hamstring)
        '"hamstring strain"[Title/Abstract] AND sports medicine[Title/Abstract]'
    ]
    
    total_fetched = 0
    for query in target_queries:
        # 쿼리당 10개씩 최대 50건 수집
        fetched_data = fetch_pubmed_papers(query, max_results=10) 
        ingest_to_db(fetched_data)
        total_fetched += len(fetched_data)
        
    print(f"모든 쿼리 실행 완료. 총 {total_fetched}건의 논문 데이터 확보 시도.")