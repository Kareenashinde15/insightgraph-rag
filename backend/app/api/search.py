from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/search", tags=["Search"])

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None

@router.post("/vector")
def vector_search(req: SearchRequest):
    ks = KnowledgeService()
    results = ks.vector_store.search(req.query, top_k=req.top_k, filters=req.filters)
    return {"query": req.query, "mode": "VECTOR", "count": len(results), "results": results}

@router.post("/graph")
def graph_search(req: SearchRequest):
    ks = KnowledgeService()
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
    ks = KnowledgeService()
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
    # Vector chunks
    vector_results = ks.vector_store.search(req.query, top_k=req.top_k)

    return {
        "query": req.query,
        "mode": "HYBRID",
        "entities": matched_entities[:10],
        "documents": matched_docs[:10],
        "relationships": matched_rels[:15],
        "vector_chunks": vector_results,
    }
