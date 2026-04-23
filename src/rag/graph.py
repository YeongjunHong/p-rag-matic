# src/rag/graph.py
import os
import sys
from typing import TypedDict

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from src.common.config import settings
from src.pgdb.schema import SourceChunk, SourceChunkVec

# ---------------------------------------------------------
# 0. 전역 리소스 로드 (서버 기동 시 1회만 로드되어야 함)
# ---------------------------------------------------------
print("모델 로딩 중...")
embedder = SentenceTransformer('BAAI/bge-m3')

# LLM 클라이언트 셋팅 
# src/rag/graph.py 상단 수정

# OpenRouter 전용 셋팅으로 오버라이드
llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
    model="openai/gpt-4o-mini", # 테스트용. 향후 Llama3 등으로 쉽게 교체 가능
    default_headers={
        "HTTP-Referer": "http://localhost:8000", # OpenRouter 권장 헤더
        "X-Title": "P-RAG-matic"
    }
)

# ---------------------------------------------------------
# 1. State 정의 (노드 간 주고받을 데이터 컨테이너)
# ---------------------------------------------------------
class RAGState(TypedDict):
    question: str
    context: str
    prompt: str
    answer: str

# ---------------------------------------------------------
# 2. Nodes (각 스테이지 로직)
# ---------------------------------------------------------
def retrieval_node(state: RAGState):
    """VDB에서 질문과 가장 유사한 청크를 검색 (HNSW 인덱스 활용)"""
    question = state["question"]
    
    # 1. 질문을 1024차원 벡터로 변환
    query_vec = embedder.encode(question).tolist()
    
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        # 2. pgvector 코사인 유사도 연산 (기호: <=>)
        # HNSW 인덱스가 걸려있어 매우 빠르게 작동함
        stmt = select(SourceChunk.content).join(
            SourceChunkVec, SourceChunk.id == SourceChunkVec.chunk_id
        ).order_by(
            SourceChunkVec.chunk_vec.cosine_distance(query_vec)
        ).limit(3)
        
        results = session.execute(stmt).scalars().all()
        
    context_str = "\n\n---\n\n".join(results)
    print(f"\n[Retrieval] {len(results)}개의 관련 논문 청크를 찾았습니다.")
    return {"context": context_str}

def prompt_maker_node(state: RAGState):
    """검색된 컨텍스트와 질문을 결합하여 LLM 프롬프트 조립"""
    question = state["question"]
    context = state["context"]
    
    # 시스템 지시어와 데이터를 명확히 분리
    prompt = f"""당신은 전문적인 스포츠 의학 AI 어시스턴트입니다.
아래 제공된 [의학 논문 초록]만을 기반으로 사용자의 질문에 답하세요.
논문에 없는 내용은 "제공된 문서에서 찾을 수 없습니다"라고 답하세요.

[의학 논문 초록]
{context}

[사용자 질문]
{question}
"""
    print("[Prompt] 프롬프트 조립 완료.")
    return {"prompt": prompt}

def generator_node(state: RAGState):
    """LLM을 호출하여 최종 답변 생성"""
    prompt = state["prompt"]
    
    response = llm.invoke(prompt)
    print("[Generator] LLM 답변 생성 완료.")
    return {"answer": response.content}

# ---------------------------------------------------------
# 3. LangGraph 오케스트레이션 (배관 연결)
# ---------------------------------------------------------
workflow = StateGraph(RAGState)

# 노드 등록
workflow.add_node("retrieval", retrieval_node)
workflow.add_node("prompt_maker", prompt_maker_node)
workflow.add_node("generator", generator_node)

# 엣지(흐름) 연결 (Query -> Retrieval -> Prompt -> Generation)
workflow.add_edge(START, "retrieval")
workflow.add_edge("retrieval", "prompt_maker")
workflow.add_edge("prompt_maker", "generator")
workflow.add_edge("generator", END)

# 그래프 컴파일 (실행 가능한 앱으로 빌드)
rag_app = workflow.compile()

# ---------------------------------------------------------
# 4. 테스트 실행부
# ---------------------------------------------------------
if __name__ == "__main__":
    # 테스트 쿼리 (우리가 수집했던 전방십자인대 관련)
    test_question = "전방십자인대(ACL) 수술 후 재활 시, 근력 회복이 왜 중요한가요?"
    
    print(f"\nQ: {test_question}")
    
    # 그래프 실행
    result = rag_app.invoke({"question": test_question})
    
    print("\n" + "="*50)
    print("🤖 RAG Final Answer:")
    print("="*50)
    print(result["answer"])