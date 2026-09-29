from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.graph.graph_engine import GraphEngine
from backend.app.retrieval.vector_store import VectorStore, VectorSearchResult
from backend.app.retrieval.query_classifier import QueryClassifier
from backend.app.retrieval.query_planner import QueryPlanner, QueryPlan

class RetrievedFact(BaseModel):
    source_entity: str
    relationship: str
    target_entity: str
    confidence: float
    source_document: str
    source_chunk: Optional[str] = None
    original_text: Optional[str] = None

class HybridRetrievalResult(BaseModel):
    query: str
    query_type: str  # SEMANTIC, GRAPH, HYBRID
    query_plan: QueryPlan
    identified_entities: List[str]
    graph_facts: List[RetrievedFact]
    graph_evidence_paths: List[List[Dict[str, str]]]
    vector_chunks: List[VectorSearchResult]
    assembled_context: str
    retrieval_trace: Dict[str, Any]

class HybridRetriever:
    def __init__(
        self,
        graph_engine: GraphEngine,
        vector_store: VectorStore,
        query_classifier: Optional[QueryClassifier] = None,
        query_planner: Optional[QueryPlanner] = None,
    ):
        self.graph_engine = graph_engine
        self.vector_store = vector_store
        self.classifier = query_classifier or QueryClassifier()
        self.planner = query_planner or QueryPlanner(graph_engine)

    def retrieve(self, query: str, top_k: int = 5, max_hops: int = 3) -> HybridRetrievalResult:
        import time

        query_type, conf = self.classifier.classify(query)
        plan = self.planner.create_plan(query, query_type)
        entities = plan.identified_entities

        graph_facts: List[RetrievedFact] = []
        graph_paths: List[List[Dict[str, str]]] = []
        visited_edge_ids = set()

        # 1. Graph Retrieval & Pathfinding (optional enrichment; vector RAG
        # remains the source of truth when no graph data exists).
        graph_started = time.perf_counter()
        for ent_name in entities:
            node = self.graph_engine.find_node_by_name(ent_name)
            if not node:
                continue

            # Direct connections
            sub_nodes, sub_edges = self.graph_engine.get_subgraph(node.id, depth=1)
            for edge in sub_edges:
                if edge.id not in visited_edge_ids:
                    visited_edge_ids.add(edge.id)
                    s_node = self.graph_engine.nodes.get(edge.source)
                    t_node = self.graph_engine.nodes.get(edge.target)
                    if s_node and t_node:
                        graph_facts.append(
                            RetrievedFact(
                                source_entity=s_node.name,
                                relationship=edge.relationship_type,
                                target_entity=t_node.name,
                                confidence=edge.confidence,
                                source_document=edge.source_document,
                                source_chunk=edge.source_chunk,
                                original_text=edge.original_text,
                            )
                        )

            # Multi-hop paths
            paths = self.graph_engine.find_paths(node.id, max_hops=max_hops)
            for p in paths[:4]:  # Top 4 traversal paths
                graph_paths.append(p)
        graph_latency_ms = round((time.perf_counter() - graph_started) * 1000, 3)

        # 2. Vector Retrieval
        vector_started = time.perf_counter()
        vector_results = self.vector_store.search(query, top_k=top_k)

        # Also retrieve chunks for entities if not already in vector results
        for ent in entities:
            if len(vector_results) < top_k + 2:
                ent_chunks = self.vector_store.search(f"{ent} {query}", top_k=2)
                for ec in ent_chunks:
                    if not any(v.chunk_id == ec.chunk_id for v in vector_results):
                        vector_results.append(ec)
        vector_latency_ms = round((time.perf_counter() - vector_started) * 1000, 3)

        # 3. Reranking (blend vector similarity + entity presence + graph fact confidence)
        for chunk in vector_results:
            boost = 0.0
            for fact in graph_facts:
                if fact.source_chunk == chunk.chunk_id:
                    boost += 0.25
                elif fact.source_document == chunk.document_id:
                    boost += 0.10
            chunk.similarity = min(1.0, chunk.similarity + boost)

        vector_results.sort(key=lambda x: x.similarity, reverse=True)
        top_chunks = vector_results[:top_k]

        # 4. Context Assembly
        context_parts = []
        if graph_facts:
            context_parts.append("### KNOWLEDGE GRAPH FACTS:")
            for f in graph_facts[:15]:
                context_parts.append(f"- {f.source_entity} --[{f.relationship}]--> {f.target_entity} (Doc: {f.source_document})")

        if graph_paths:
            context_parts.append("\n### GRAPH EVIDENCE PATHS:")
            for p in graph_paths[:3]:
                path_str = " -> ".join([f"{step['source']} -[{step['relationship']}]-> {step['target']}" for step in p])
                context_parts.append(f"- {path_str}")

        if top_chunks:
            context_parts.append("\n### RETRIEVED DOCUMENT EVIDENCE:")
            for idx, c in enumerate(top_chunks, 1):
                context_parts.append(
                    f"[{idx}] Source: {c.source or c.document_id} (Page {c.page}, Chunk: {c.chunk_id})\n\"{c.text}\""
                )

        assembled_context = "\n".join(context_parts)

        trace = {
            "query_type": query_type,
            "classification_confidence": conf,
            "entities_identified": entities,
            "graph_facts_count": len(graph_facts),
            "graph_paths_count": len(graph_paths),
            "vector_chunks_retrieved": len(top_chunks),
            "evidence_used_count": len(top_chunks) + len(graph_facts),
            "graph_query_latency_ms": graph_latency_ms,
            "vector_search_latency_ms": vector_latency_ms,
            "embedding_latency_ms": self.vector_store.embedding_engine.last_embedding_latency_ms,
        }

        return HybridRetrievalResult(
            query=query,
            query_type=query_type,
            query_plan=plan,
            identified_entities=entities,
            graph_facts=graph_facts,
            graph_evidence_paths=graph_paths,
            vector_chunks=top_chunks,
            assembled_context=assembled_context,
            retrieval_trace=trace,
        )
