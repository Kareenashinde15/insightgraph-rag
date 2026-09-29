from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])

class CypherQueryRequest(BaseModel):
    query: str

@router.get("")
def get_entire_graph():
    ks = KnowledgeService()
    nodes = ks.graph_engine.get_all_nodes()
    edges = ks.graph_engine.get_all_edges()
    return {
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
        "metrics": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
    }

@router.get("/entity/{entity_id}")
def get_entity_subgraph(entity_id: str, depth: int = Query(1, ge=1, le=5)):
    ks = KnowledgeService()
    node = ks.graph_engine.nodes.get(entity_id) or ks.graph_engine.find_node_by_name(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail="Entity not found")

    nodes, edges = ks.graph_engine.get_subgraph(node.id, depth=depth)
    return {
        "root_entity": node.model_dump(),
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
    }

@router.post("/query")
def execute_graph_query(req: CypherQueryRequest):
    ks = KnowledgeService()
    try:
        res = ks.graph_engine.execute_read_only_cypher(req.query)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")
