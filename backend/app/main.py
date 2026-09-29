import os
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

app = FastAPI(
    title="InsightGraph RAG — Local Document Intelligence Platform",
    description="Local personal knowledge graph and RAG hobby application",
    version="1.0.0"
)

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Register API routers
app.include_router(documents_router)
app.include_router(entities_router)
app.include_router(graph_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(system_router)

@app.on_event("startup")
def startup_event():
    # Warm up the service without loading any implicit data.
    ks = KnowledgeService()
    print(f"Knowledge Base Online: {len(ks.documents)} documents, {len(ks.graph_engine.nodes)} entities, {len(ks.graph_engine.edges)} relationships.")

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
