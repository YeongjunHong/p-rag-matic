# src/rag/graph.py
import os
import sys
from typing import TypedDict, Literal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from src.common.config import settings
from src.pgdb.schema import SourceChunk, SourceChunkVec

# ---------------------------------------------------------
# 0. 전역 리소스 로드
# ---------------------------------------------------------
print("모델 로딩 중...")
embedder = SentenceTransformer('BAAI/bge-m3')

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
    model="openai/gpt-4o-mini",
    default_headers={
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "P-RAG-matic"
    }
)

# ---------------------------------------------------------
# 1. State 정의 (intent 필드 추가)
# ---------------------------------------------------------
class RAGState(TypedDict):
    question: str
    intent: str      # 추가됨: SLM이 분류한 의도 (medical_qa, chitchat, out_of_domain)
    context: str
    prompt: str
    answer: str

# ---------------------------------------------------------
# 2. Nodes (스테이지 로직)
# ---------------------------------------------------------
def planner_node(state: RAGState):
    """사용자 질문의 의도를 파악하여 라우팅 방향을 결정 (현재는 Mocking)"""
    question = state["question"]
    print(f"\n[Planner] 쿼리 분석 중: '{question}'")
    
    # TODO: 다음 스텝에서 여기에 SLM을 호출하여 의도를 분류하는 로직이 들어감.
    # 당장 파이프라인 흐름 테스트를 위해 의도를 수동으로 지정 (아래 값을 바꿔가며 테스트)
    mock_intent = "medical_qa"  # 테스트 옵션: "medical_qa", "chitchat", "out_of_domain"
    
    print(f"[Planner] 결정된 의도: {mock_intent}")
    return {"intent": mock_intent}

def retrieval_node(state: RAGState):
    """VDB에서 질문과 가장 유사한 청크를 검색 (의학 질문일 때만 실행됨)"""
    question = state["question"]
    query_vec = embedder.encode(question).tolist()
    
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        stmt = select(SourceChunk.content).join(
            SourceChunkVec, SourceChunk.id == SourceChunkVec.chunk_id
        ).order_by(
            SourceChunkVec.chunk_vec.cosine_distance(query_vec)
        ).limit(3)
        results = session.execute(stmt).scalars().all()
        
    context_str = "\n\n---\n\n".join(results)
    print(f"[Retrieval] {len(results)}개의 관련 논문 청크를 찾았습니다.")
    return {"context": context_str}

def prompt_maker_node(state: RAGState):
    """검색된 컨텍스트와 질문을 결합하여 메인 LLM 프롬프트 조립"""
    question = state["question"]
    context = state["context"]
    
    prompt = f"""당신은 전문적인 스포츠 의학 AI 어시스턴트입니다.
아래 제공된 [의학 논문 초록]만을 기반으로 사용자의 질문에 답하세요.

[의학 논문 초록]
{context}

[사용자 질문]
{question}
"""
    print("[Prompt] 메인 프롬프트 조립 완료.")
    return {"prompt": prompt}

def generator_node(state: RAGState):
    """메인 LLM을 호출하여 최종 답변 생성"""
    prompt = state["prompt"]
    response = llm.invoke(prompt)
    print("[Generator] LLM 답변 생성 완료.")
    return {"answer": response.content}

def general_generator_node(state: RAGState):
    """VDB 검색 없이 시스템 룰에 따라 즉시 답변 생성 (우회 경로)"""
    question = state["question"]
    intent = state["intent"]
    
    if intent == "out_of_domain":
        answer = "저는 스포츠 의학 및 재활 전문 어시스턴트입니다. 의학 외의 질문에는 답변해 드릴 수 없습니다."
    else: # chitchat
        response = llm.invoke(f"너는 스포츠 의학 전문 AI야. 사용자의 가벼운 말에 짧고 친절하게 답해줘: {question}")
        answer = response.content
        
    print(f"[General Generator] 우회 경로 답변 생성 완료 (의도: {intent})")
    return {"answer": answer}

# ---------------------------------------------------------
# 3. LangGraph 라우팅 및 오케스트레이션
# ---------------------------------------------------------
def route_query(state: RAGState) -> Literal["retrieval", "general_generator"]:
    """intent 상태값에 따라 다음 실행할 노드를 결정하는 조건부 엣지 함수"""
    if state["intent"] == "medical_qa":
        return "retrieval"
    return "general_generator"

workflow = StateGraph(RAGState)

workflow.add_node("planner", planner_node)
workflow.add_node("retrieval", retrieval_node)
workflow.add_node("prompt_maker", prompt_maker_node)
workflow.add_node("generator", generator_node)
workflow.add_node("general_generator", general_generator_node)

workflow.add_edge(START, "planner")

# 분기점 (Conditional Edge) 설정
workflow.add_conditional_edges("planner", route_query)

# 메인 RAG 경로
workflow.add_edge("retrieval", "prompt_maker")
workflow.add_edge("prompt_maker", "generator")
workflow.add_edge("generator", END)

# 우회 경로
workflow.add_edge("general_generator", END)

rag_app = workflow.compile()

# ---------------------------------------------------------
# 4. 테스트 실행부
# ---------------------------------------------------------
if __name__ == "__main__":
    test_question = "파이썬으로 웹 크롤링하는 코드 좀 짜줄래?"
    
    # 주의: 현재 planner_node에서 mock_intent 값이 하드코딩 되어 있음.
    # 테스트 시 mock_intent 값을 "medical_qa", "out_of_domain", "chitchat"으로 바꿔가며 실행해 볼 것.
    
    result = rag_app.invoke({"question": test_question})
    
    print("\n" + "="*50)
    print("Final Answer:")
    print("="*50)
    print(result["answer"])