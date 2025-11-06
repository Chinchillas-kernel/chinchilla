"""FastAPI application entry point."""

import os
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import AgentRequest, AgentResponse
from app.config import settings
from agent.router import dispatch
from agent.router_runtime import get_runtime


# ============================================================================
# LangSmith 추적 설정 (앱 시작 전에 환경변수 설정)
# ============================================================================
def setup_langsmith():
    """LangSmith 추적 활성화 (API 키가 있을 경우)"""
    if settings.langsmith_api_key:
        # 환경변수로 LangSmith 설정
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project or "chinchilla"

    else:
        print("   LangSmith API key not found - tracing disabled")
        print("   Add LANGSMITH_API_KEY to .env to enable tracing\n")


# LangSmith 초기화 (FastAPI 앱 생성 전에 실행)
setup_langsmith()

# Initialize FastAPI app
app = FastAPI(
    title="Elderly Administrative Assistant API",
    description="RAG-based multi-category agent system",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize runtime (빌드된 그래프 캐시)
GRAPHS, HOOKS = get_runtime()

# API router
router = APIRouter()


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "Elderly Administrative Assistant",
        "version": "0.1.0",
        "categories": list(GRAPHS.keys()),
        "langsmith_enabled": bool(settings.langsmith_api_key),  # LangSmith 상태 추가
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "ok": True,
        "categories": list(GRAPHS.keys()),
        "upstage_configured": bool(settings.upstage_api_key),
        "langsmith_enabled": bool(settings.langsmith_api_key),  # LangSmith 상태 추가
    }


@router.post("/agent/query", response_model=AgentResponse)
def agent_query(req: AgentRequest) -> AgentResponse:
    """Main agent query endpoint.

    Args:
        req: AgentRequest (discriminated union by category)

    Returns:
        AgentResponse with answer and sources

    Raises:
        HTTPException: If category unknown or execution fails
    """
    try:
        return dispatch(req, graphs=GRAPHS, hooks=HOOKS)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
