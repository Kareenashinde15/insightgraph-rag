from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any, List
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.models.schema import ProcessingJobModel

router = APIRouter(prefix="/api", tags=["System / Admin"])

@router.get("/metrics")
def get_system_metrics():
    ks = KnowledgeService()
    return ks.get_metrics()

@router.get("/processing/jobs", response_model=List[ProcessingJobModel])
def list_processing_jobs():
    ks = KnowledgeService()
    return list(ks.jobs.values())

@router.get("/conflicts")
def get_detected_conflicts():
    ks = KnowledgeService()
    raw_rels = [e.model_dump() for e in ks.graph_engine.get_all_edges()]
    return ks.conflict_detector.detect_conflicts(raw_rels)

@router.get("/settings")
def get_settings():
    ks = KnowledgeService()
    return ks.settings

@router.post("/settings")
def update_settings(updates: Dict[str, Any] = Body(...)):
    ks = KnowledgeService()
    if "llm_provider" in updates and updates["llm_provider"] != "groq":
        raise HTTPException(status_code=400, detail="Only Groq is supported in the local hobby configuration")
    ks.settings.update(updates)
    ks.db.upsert("settings", "config", ks.settings)
    return {"message": "Settings updated", "settings": ks.settings}

