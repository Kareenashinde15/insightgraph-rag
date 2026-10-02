"""Lexical + reasoning retrieval without embeddings or vector search."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.graph.graph_engine import GraphEngine
from backend.app.retrieval.query_classifier import QueryClassifier
from backend.app.retrieval.query_planner import QueryPlanner
from backend.app.retrieval.text_search import TextSearchResult
from backend.app.storage.mongo_store import MongoVectorlessStore


class RetrievedFact(BaseModel):
    source_entity: str
    relationship: str
    target_entity: str
    confidence: float
    source_document: str
    source_chunk: Optional[str] = None
    original_text: Optional[str] = None


class VectorlessRetrievalResult(BaseModel):
    query: str
    query_type: str
    query_plan: Any
    identified_entities: List[str] = Field(default_factory=list)
    graph_facts: List[RetrievedFact] = Field(default_factory=list)
    graph_evidence_paths: List[List[Dict[str, str]]] = Field(default_factory=list)
    retrieved_sections: List[TextSearchResult] = Field(default_factory=list)
    assembled_context: str = ""
    retrieval_trace: Dict[str, Any] = Field(default_factory=dict)


class VectorlessRetriever:
    def __init__(self, store: MongoVectorlessStore, graph_engine: GraphEngine):
        self.store = store
        self.graph_engine = graph_engine
        self.classifier = QueryClassifier()
        self.planner = QueryPlanner(graph_engine)

    def retrieve(self, query: str, top_k: int = 5, max_hops: int = 3) -> VectorlessRetrievalResult:
        started = time.perf_counter()
        query_type, confidence = self.classifier.classify(query)
        plan = self.planner.create_plan(query, query_type)
        entities = plan.identified_entities

        graph_facts: List[RetrievedFact] = []
        graph_paths: List[List[Dict[str, str]]] = []
        visited_edges = set()
        graph_started = time.perf_counter()

        for entity_name in entities:
            node = self.graph_engine.find_node_by_name(entity_name)
            if not node:
                continue
            _, edges = self.graph_engine.get_subgraph(node.id, depth=1)
            for edge in edges:
                if edge.id in visited_edges:
                    continue
                visited_edges.add(edge.id)
                source = self.graph_engine.nodes.get(edge.source)
                target = self.graph_engine.nodes.get(edge.target)
                if source and target:
                    graph_facts.append(
                        RetrievedFact(
                            source_entity=source.name,
                            relationship=edge.relationship_type,
                            target_entity=target.name,
                            confidence=edge.confidence,
                            source_document=edge.source_document,
                            source_chunk=edge.source_chunk,
                            original_text=edge.original_text,
                        )
                    )
            graph_paths.extend(self.graph_engine.find_paths(node.id, max_hops=max_hops)[:4])

        graph_latency_ms = round((time.perf_counter() - graph_started) * 1000, 3)

        text_started = time.perf_counter()
        raw_sections = self.store.search_sections(query, top_k=top_k)
        sections: List[TextSearchResult] = []
        max_score = max((float(item.get("score", 0)) for item in raw_sections), default=1.0)
        for item in raw_sections:
            score = float(item.get("score", 0))
            sections.append(
                TextSearchResult(
                    section_id=str(item.get("id", "")),
                    document_id=str(item.get("document_id", "")),
                    text=str(item.get("text", "")),
                    page=item.get("page_number") or 1,
                    source=str(item.get("metadata", {}).get("source", "")),
                    relevance=round(score / max_score, 4) if max_score else 0.0,
                    entities=list(item.get("entities") or []),
                    metadata=dict(item.get("metadata") or {}),
                )
            )
        text_latency_ms = round((time.perf_counter() - text_started) * 1000, 3)

        context_parts: List[str] = []
        if graph_facts:
            context_parts.append("### STRUCTURED GRAPH FACTS:")
            context_parts.extend(
                f"- {fact.source_entity} --[{fact.relationship}]--> {fact.target_entity} "
                f"(Document: {fact.source_document})"
                for fact in graph_facts[:15]
            )
        if graph_paths:
            context_parts.append("\n### GRAPH EVIDENCE PATHS:")
            for path in graph_paths[:3]:
                context_parts.append(
                    "- " + " -> ".join(
                        f"{step['source']} -[{step['relationship']}]-> {step['target']}"
                        for step in path
                    )
                )
        if sections:
            context_parts.append("\n### RETRIEVED DOCUMENT SECTIONS:")
            for index, section in enumerate(sections, 1):
                context_parts.append(
                    f"[{index}] Source: {section.source or section.document_id} "
                    f"(Page {section.page}, Section: {section.chunk_id})\n\"{section.text}\""
                )

        trace = {
            "retrieval_mode": "vectorless_text",
            "query_type": query_type,
            "classification_confidence": confidence,
            "entities_identified": entities,
            "graph_facts_count": len(graph_facts),
            "graph_paths_count": len(graph_paths),
            "text_sections_retrieved": len(sections),
            "text_sections_retrieved": len(sections),
            "evidence_used_count": len(sections) + len(graph_facts),
            "graph_query_latency_ms": graph_latency_ms,
            "text_search_latency_ms": text_latency_ms,
            "retrieval_latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }

        return VectorlessRetrievalResult(
            query=query,
            query_type="HYBRID" if graph_facts else "TEXT",
            query_plan=plan,
            identified_entities=entities,
            graph_facts=graph_facts,
            graph_evidence_paths=graph_paths,
            retrieved_sections=sections,
            assembled_context="\n".join(context_parts),
            retrieval_trace=trace,
        )
