from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.app.services.service_factory import get_knowledge_service

router = APIRouter(prefix="/api/search", tags=["Search"])

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None

@router.post("/text")
def text_search(req: SearchRequest):
    ks = get_knowledge_service()
    results = ks.text_search(req.query, top_k=req.top_k, filters=req.filters)
    return {"query": req.query, "mode": "TEXT", "count": len(results), "results": results}

@router.post("/graph")
def graph_search(req: SearchRequest):
    ks = get_knowledge_service()
    node = ks.graph_engine.find_node_by_name(req.query)
    if node:
        nodes, edges = ks.graph_engine.get_subgraph(node.id, depth=2)
        return {
            "query": req.query,
            "mode": "GRAPH",
            "matched_entity": node.model_dump(),
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump() for e in edges],
        }
    return {"query": req.query, "mode": "GRAPH", "matched_entity": None, "nodes": [], "edges": []}

@router.post("/hybrid")
def hybrid_search(req: SearchRequest):
    ks = get_knowledge_service()
    # Search entities
    q_lower = req.query.lower()
    matched_entities = [
        n.model_dump() for n in ks.graph_engine.get_all_nodes()
        if q_lower in n.name.lower() or any(q_lower in a.lower() for a in n.aliases)
    ]
    # Search documents
    matched_docs = [
        {
            key: value
            for key, value in d.model_dump().items()
            if key != "raw_text"
        }
        for d in ks.documents.values()
        if q_lower in d.filename.lower() or (d.raw_text and q_lower in d.raw_text.lower())
    ]
    # Search relationships
    matched_rels = [
        e.model_dump() for e in ks.graph_engine.get_all_edges()
        if q_lower in e.relationship_type.lower() or (e.original_text and q_lower in e.original_text.lower())
    ]
    # Lexical sections; kept under the old response key for frontend compatibility.
    text_results = ks.text_search(req.query, top_k=req.top_k)

    return {
        "query": req.query,
        "mode": "HYBRID",
        "entities": matched_entities[:10],
        "documents": matched_docs[:10],
        "relationships": matched_rels[:15],
        "sections": text_results,
        "retrieval_mode": "vectorless_text",
    }
