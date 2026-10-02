import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from backend.app.services.service_factory import get_knowledge_service
from backend.app.models.schema import ChatMessageModel, ChatSessionModel, CitationModel

router = APIRouter(prefix="/api/chat", tags=["Ask Knowledge / Chat"])

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = "session_default"


@router.get("")
def chat_endpoint_info():
    """Provide a friendly response when the endpoint is opened in a browser."""
    return {
        "service": "InsightGraph RAG chat",
        "status": "ready",
        "method": "POST",
        "message": "Send a POST request with a JSON body containing 'query' to ask a question.",
    }

@router.post("", response_model=ChatMessageModel)
def send_chat_query(req: ChatRequest):
    ks = get_knowledge_service()
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        return ks.ask(query=req.query, session_id=req.session_id)
    except Exception as exc:
        # Retrieval must remain useful even when graph enrichment or the LLM
        # provider fails. Return the evidence directly instead of surfacing a
        # gateway 502 to the browser.
        print(f"Chat generation failed; returning retrieval fallback: {type(exc).__name__}: {exc}")
        result = ks.retriever.retrieve(
            query=req.query,
            top_k=int(ks.settings.get("top_k_retrieval", 5)),
            max_hops=int(ks.settings.get("max_graph_hops", 3)),
        )
        citations = [
            CitationModel(
                id=f"cit_{idx}",
                citation_index=idx,
                document_id=chunk.document_id,
                document_name=chunk.source or chunk.document_id,
                page=chunk.page or 1,
                chunk_id=chunk.chunk_id,
                snippet=chunk.text[:220],
                similarity_score=chunk.similarity,
            )
            for idx, chunk in enumerate(result.retrieved_sections, 1)
        ]
        passages = [
            f"[{idx}] {chunk.source or chunk.document_id}, page {chunk.page}:\n{chunk.text}"
            for idx, chunk in enumerate(result.retrieved_sections, 1)
        ]
        content = (
            "Based on the retrieved document evidence:\n\n"
            + ("\n\n".join(passages) if passages else "No matching document evidence was found.")
        )
        return ChatMessageModel(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            session_id=req.session_id or "session_default",
            role="assistant",
            content=content,
            retrieval_type=result.query_type,
            citations=citations,
            graph_evidence_paths=result.graph_evidence_paths,
            retrieval_trace=result.retrieval_trace,
            query_plan=[step.description for step in result.query_plan.steps],
            created_at=datetime.now().isoformat(),
        )

@router.get("/sessions", response_model=List[ChatSessionModel])
def list_chat_sessions():
    ks = get_knowledge_service()
    return list(ks.chat_sessions.values())

@router.get("/sessions/{session_id}", response_model=ChatSessionModel)
def get_chat_session(session_id: str):
    ks = get_knowledge_service()
    if session_id not in ks.chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return ks.chat_sessions[session_id]
