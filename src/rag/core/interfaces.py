# src/rag/core/interfaces.py
from typing import TypeVar, Protocol
from src.rag.core.types import RagRequest, RagContext

class ComponentInterface(Protocol):
    async def __call__(self, req: RagRequest, ctx: RagContext) -> None:
        ...

TInterface = TypeVar("TInterface", bound=ComponentInterface)

# 구체화된 인터페이스들 (추후 각 플러그인이 상속받아 구현)
class RagPlanner(ComponentInterface, Protocol): 
    pass

class RagQueryExpander(ComponentInterface, Protocol): 
    pass

class RagRetriever(ComponentInterface, Protocol): 
    pass

class RagReranker(ComponentInterface, Protocol): 
    pass

class RagFilterer(ComponentInterface, Protocol): 
    pass

class RagAssembler(ComponentInterface, Protocol): 
    pass

class RagCompressor(ComponentInterface, Protocol): 
    pass

class RagPacker(ComponentInterface, Protocol): 
    pass

class RagPromptMaker(ComponentInterface, Protocol): 
    pass

class RagGenerator(ComponentInterface, Protocol): 
    pass

class RagPostChecker(ComponentInterface, Protocol): 
    pass

class RagInputGuard(ComponentInterface, Protocol): 
    pass