from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.models.schema import GraphNodeModel, GraphEdgeModel

router = APIRouter(prefix="/api/entities", tags=["Entities"])

@router.get("", response_model=List[GraphNodeModel])
def list_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (Person, Company, Project, Technology, etc.)"),
    search: Optional[str] = Query(None, description="Search query")
):
    ks = KnowledgeService()
    nodes = ks.graph_engine.get_all_nodes()

    if entity_type:
        nodes = [n for n in nodes if n.type.lower() == entity_type.lower()]

    if search:
        s = search.lower().strip()
        nodes = [
            n for n in nodes
            if s in n.name.lower() or s in n.normalized_name or any(s in a.lower() for a in n.aliases)
        ]

    # Sort by connectivity / source count
    nodes.sort(key=lambda n: n.source_count, reverse=True)
    return nodes

@router.get("/{entity_id}")
def get_entity_details(entity_id: str):
    ks = KnowledgeService()
    node = ks.graph_engine.nodes.get(entity_id)
    if not node:
        # Try search by name
        node = ks.graph_engine.find_node_by_name(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail="Entity not found")

    out_eids = ks.graph_engine.out_edges.get(node.id, [])
    in_eids = ks.graph_engine.in_edges.get(node.id, [])
    rels = [ks.graph_engine.edges[eid] for eid in out_eids + in_eids if eid in ks.graph_engine.edges]

    docs = [ks.documents[did] for did in node.document_ids if did in ks.documents]

    return {
        "entity": node,
        "relationships_count": len(rels),
        "relationships": rels,
        "documents": docs,
    }

@router.get("/{entity_id}/relationships", response_model=List[GraphEdgeModel])
def get_entity_relationships(entity_id: str):
    ks = KnowledgeService()
    node = ks.graph_engine.nodes.get(entity_id) or ks.graph_engine.find_node_by_name(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail="Entity not found")

    out_eids = ks.graph_engine.out_edges.get(node.id, [])
    in_eids = ks.graph_engine.in_edges.get(node.id, [])
    rels = [ks.graph_engine.edges[eid] for eid in out_eids + in_eids if eid in ks.graph_engine.edges]
    return rels

@router.get("/{entity_id}/sources")
def get_entity_sources(entity_id: str):
    ks = KnowledgeService()
    node = ks.graph_engine.nodes.get(entity_id) or ks.graph_engine.find_node_by_name(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail="Entity not found")

    sources = []
    for did in node.document_ids:
        doc = ks.documents.get(did)
        if doc:
            chunks = ks.document_chunks.get(did, [])
            relevant_chunks = [c for c in chunks if any(node.name.lower() in e.lower() for e in c.entities)]
            sources.append({
                "document": doc,
                "relevant_chunks": relevant_chunks or chunks[:2],
            })
    return sources
