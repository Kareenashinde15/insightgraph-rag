from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.models.schema import ChatMessageModel, ChatSessionModel

router = APIRouter(prefix="/api/chat", tags=["Ask Knowledge / Chat"])

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = "session_default"

@router.post("", response_model=ChatMessageModel)
def send_chat_query(req: ChatRequest):
    ks = KnowledgeService()
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return ks.ask(query=req.query, session_id=req.session_id)

@router.get("/sessions", response_model=List[ChatSessionModel])
def list_chat_sessions():
    ks = KnowledgeService()
    return list(ks.chat_sessions.values())

@router.get("/sessions/{session_id}", response_model=ChatSessionModel)
def get_chat_session(session_id: str):
    ks = KnowledgeService()
    if session_id not in ks.chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return ks.chat_sessions[session_id]
