import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.documents import router as documents_router
from backend.app.api.entities import router as entities_router
from backend.app.api.graph import router as graph_router
from backend.app.api.search import router as search_router
from backend.app.api.chat import router as chat_router
from backend.app.api.system import router as system_router
from backend.app.services.knowledge_service import KnowledgeService

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Start the API immediately using local uploads and SQLite state.
    ks = KnowledgeService()

    print(f"Knowledge Base Online: {len(ks.documents)} documents, {len(ks.graph_engine.nodes)} entities, {len(ks.graph_engine.edges)} relationships.")
    yield


app = FastAPI(
    title="InsightGraph RAG — Local Document Intelligence Platform",
    description="Local personal knowledge graph and RAG hobby application",
    version="1.0.0",
    lifespan=lifespan,
)

def normalize_origin(origin: str) -> str:
    """Normalize configured browser origins before passing them to Starlette."""
    return origin.strip().rstrip("/")


raw_origins = [
    normalize_origin(origin)
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://insightsrag.vercel.app",
    "https://insightgraph.vercel.app",
]
base_origins = (default_origins or []) + (raw_origins or [])
cors_origins = sorted({normalize_origin(origin) for origin in base_origins if origin})

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(documents_router)
app.include_router(entities_router)
app.include_router(graph_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(system_router)

@app.get("/")
def root():
    return {
        "brand": "InsightGraph RAG",
        "product": "Local Document Intelligence + RAG",
        "status": "Online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "InsightGraph RAG"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)
