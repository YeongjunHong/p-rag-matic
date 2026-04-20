# p-rag-matic (Pragmatic RAG Engine)

"거품을 걷어낸 실용주의 RAG 아키텍처"

p-rag-matic은 LangGraph 기반의 상태 관리(State Management)와 의존성 주입(Dependency Injection) 패턴을 극대화하여 설계된, 고신뢰성 복합 추론 RAG 파이프라인 엔진입니다. MLOps 표준을 준수하며, 파편화된 설정을 제거하고 테스트 용이성을 최우선으로 고려했습니다.

##  Architecture & Design Principles

본 프로젝트는 현업에서 검증된 **Decoupled 3-Layer Architecture**를 따릅니다.

1. **Interface (API):** 외부 요청을 처리하고 파이프라인의 입출력을 제어합니다. (`src/api`)
2. **Stage (Workflow):** LangGraph를 기반으로 플래닝, 검색, 생성, 검증 등의 비즈니스 로직 단계를 제어합니다. (`src/rag/stages`, `src/rag/graph.py`)
3. **Plugin (Adapters):** DB, LLM, 외부 검색기 등 구체적인 기술 구현체들을 캡슐화합니다. (`src/rag/plugins`)

* **Single Source of Truth (SSOT):** 모든 환경 변수와 애플리케이션 설정은 Pydantic `BaseSettings`(`src/common/config.py`)를 통해 단일 지점에서 안전하게 관리됩니다.
* **Data Ingestion Isolation:** 무거운 문서 파싱 및 벡터 적재(Ingestion) 로직은 실시간 API 서빙(Runtime) 환경과 물리적으로 분리되어 있습니다. (`data_pipeline/`)
* **Determinism in Environments:** `uv` 기반의 패키지 관리로 운영, 개발, 테스트 환경 간의 의존성 충돌을 원천 차단합니다. (`pyproject.toml`, `uv.lock`)

##  Directory Structure

\`\`\`text
p-rag-matic/
├── data_pipeline/      # 데이터 적재 및 파싱 배치 작업 (API 런타임과 완전 분리)
├── pg-ext/             # PostgreSQL + pgvector + pg_search Docker 인프라
├── src/
│   ├── api/            # FastAPI 기반 라우팅 및 엔드포인트
│   ├── common/         # 전역 설정(SSOT), 로거, 공통 유틸리티
│   ├── evaluation/     # RAGAs 기반 파이프라인 품질 평가 모듈
│   ├── pgdb/           # SQLAlchemy ORM 스키마 및 Alembic 마이그레이션
│   └── rag/
│       ├── core/       # 시스템 전반의 타입 정의 및 인터페이스
│       ├── plugins/    # 구체적 기술 구현체 (pgvector, OpenRouter, Noop 등)
│       ├── services/   # 의존성 주입을 위한 Registry
│       ├── stages/     # 파이프라인의 각 처리 단계 (Node Logic)
│       └── graph.py    # LangGraph 오케스트레이터 및 파이프라인 빌더
├── tests/              # 단위 테스트 및 통합 테스트
├── alembic.ini         # 데이터베이스 마이그레이션 설정
└── pyproject.toml      # uv 기반 프로젝트 메타데이터 및 의존성 명세
\`\`\`

##  Quick Start

### 1. Requirements
* Python 3.12+ (권장)
* [uv](https://github.com/astral-sh/uv) (초고속 파이썬 패키지 매니저)
* Docker & Docker Compose (PostgreSQL 인프라용)

### 2. Installation

\`\`\`bash
# uv 설치 (이미 설치되어 있다면 생략)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 클론 및 의존성 설치
git clone https://github.com/YeongjunHong/p-rag-matic.git
cd p-rag-matic
uv sync  # uv.lock을 기반으로 가상환경 자동 생성 및 패키지 설치
\`\`\`

### 3. Environment Variables
프로젝트 루트에 `.env` 파일을 생성하고 다음 값을 채워 넣습니다.
\`\`\`env
# Database Settings
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rag_db

# LLM API
OPENROUTER_API_KEY=sk-or-v1-your-api-key
\`\`\`

### 4. Database Setup & Migration
\`\`\`bash
# 1. pgvector가 포함된 DB 인프라 구동 (Docker)
cd pg-ext
docker-compose up -d  # (docker-compose 파일이 구성되어 있다고 가정)
cd ..

# 2. Alembic 마이그레이션 적용 (초기 스키마 생성)
uv run alembic revision --autogenerate -m "Initial schema"
uv run alembic upgrade head
\`\`\`

## 🛠 Usage (Development)
VSCode 사용자라면 `.vscode/launch.json`에 정의된 디버그 프로필을 활용하여 FastAPI 서버, 특정 스크립트, 단위 테스트를 손쉽게 실행하고 디버깅할 수 있습니다.
\`\`\`bash
# API 서버 로컬 실행 (터미널)
uv run uvicorn src.api.routes:app --reload
\`\`\`