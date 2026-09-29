from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.embeddings.embedding_engine import EmbeddingEngine

class VectorRecord(BaseModel):
    id: str
    vector: List[float]
    document_id: str
    chunk_id: str
    text: str
    entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VectorSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page: Optional[int] = 1
    source: Optional[str] = ""
    similarity: float
    entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VectorStore:
    def __init__(self, embedding_engine: Optional[EmbeddingEngine] = None):
        self.records: Dict[str, VectorRecord] = {}
        self.embedding_engine = embedding_engine or EmbeddingEngine()
        self.last_search_latency_ms = 0.0

    def upsert(self, record: VectorRecord):
        self.records[record.id] = record

    def upsert_chunk(
        self,
        document_id: str,
        chunk_id: str,
        text: str,
        entities: List[str],
        page: int = 1,
        source: str = "",
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> VectorRecord:
        vector = self.embedding_engine.embed_document(text)
        meta = {
            "page": page,
            "source": source,
            **(extra_metadata or {})
        }
        record = VectorRecord(
            id=chunk_id,
            vector=vector,
            document_id=document_id,
            chunk_id=chunk_id,
            text=text,
            entities=entities,
            metadata=meta,
        )
        self.upsert(record)
        return record

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        import time
        started = time.perf_counter()
        query_vector = self.embedding_engine.embed_query(query)
        scored: List[VectorSearchResult] = []

        for rec in self.records.values():
            # Check metadata filters if provided
            if filters:
                match = True
                for k, v in filters.items():
                    if k == "document_id" and rec.document_id != v:
                        match = False
                        break
                    elif k in rec.metadata and rec.metadata[k] != v:
                        match = False
                        break
                if not match:
                    continue

            sim = EmbeddingEngine.cosine_similarity(query_vector, rec.vector)
            
            # Boost score if query terms or entity names appear directly in text
            lower_q = query.lower()
            lower_t = rec.text.lower()
            if any(e.lower() in lower_q for e in rec.entities):
                sim = min(1.0, sim + 0.15)
            elif any(w in lower_t for w in lower_q.split() if len(w) > 3):
                sim = min(1.0, sim + 0.08)

            scored.append(
                VectorSearchResult(
                    chunk_id=rec.chunk_id,
                    document_id=rec.document_id,
                    text=rec.text,
                    page=rec.metadata.get("page", 1),
                    source=rec.metadata.get("source", ""),
                    similarity=round(sim, 4),
                    entities=rec.entities,
                    metadata=rec.metadata,
                )
            )

        scored.sort(key=lambda x: x.similarity, reverse=True)
        self.last_search_latency_ms = round((time.perf_counter() - started) * 1000, 3)
        return scored[:top_k]

    def count(self) -> int:
        return len(self.records)

    def delete_by_document(self, document_id: str):
        to_del = [rid for rid, r in self.records.items() if r.document_id == document_id]
        for rid in to_del:
            del self.records[rid]
