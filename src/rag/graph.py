# src/rag/graph.py
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

from src.rag.core.types import RagRequest, RagContext, RagResponse

class GraphState(TypedDict):
    request: RagRequest
    ctx: RagContext

class RagDependencies:
    """그래프 빌드 시점에 주입할 레지스트리 및 의존성 컨테이너"""
    def __init__(self, **kwargs: Any):
        self.retriever_registry = kwargs.get("retriever_registry")
        self.generator_registry = kwargs.get("generator_registry")
        # 필요에 따라 다른 레지스트리나 로거, 트레이서 추가

def build_graph(deps: RagDependencies):
    """
    의존성을 주입받아 LangGraph를 컴파일하여 반환한다.
    """
    g = StateGraph(GraphState)

    # 임시 노드 함수들 (향후 src/rag/stages/ 구현체로 대체)
    async def node_planner(state: GraphState) -> GraphState:
        req, ctx = state["request"], state["ctx"]
        if req.safety_level == "high":
            ctx.plan_id = "strict"
            ctx.plan = {"bm25_weight": 0.7, "vector_weight": 0.3}
        return state

    async def node_retrieval(state: GraphState) -> GraphState:
        # deps.retriever_registry.get().invoke(...) 형태로 사용
        return state

    async def node_generator(state: GraphState) -> GraphState:
        # deps.generator_registry.get().invoke(...) 형태로 사용
        return state

    # 라우팅 로직
    def route_after_planner(state: GraphState) -> str:
        q = state["request"].user_query.strip()
        if len(q) <= 2:
            return "generator" # 쿼리가 너무 짧으면 바로 생성(혹은 거절) 단계로 점프
        return "retrieval"

    # 노드 추가
    g.add_node("planner", node_planner)
    g.add_node("retrieval", node_retrieval)
    g.add_node("generator", node_generator)

    # 엣지 연결
    g.set_entry_point("planner")
    
    g.add_conditional_edges(
        "planner", 
        route_after_planner, 
        {
            "retrieval": "retrieval",
            "generator": "generator",
        }
    )

    g.add_edge("retrieval", "generator")
    g.add_edge("generator", END)

    return g.compile()

async def run_graph(app, request: RagRequest) -> RagResponse:
    """컴파일된 그래프 애플리케이션을 실행"""
    state: GraphState = {"request": request, "ctx": RagContext()}
    out = await app.ainvoke(state)
    
    # 임시 응답 처리 (실제로는 ctx의 데이터를 정제하여 반환)
    return RagResponse(answer="생성된 응답입니다.", source_nodes=out["ctx"].retrieved_chunks)