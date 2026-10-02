"""Clean-slate MongoDB-backed vectorless knowledge service."""

from __future__ import annotations

import os
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.graph.graph_engine import GraphEngine
from backend.app.llm.providers import get_llm_provider
from backend.app.models.schema import (
    ChatMessageModel,
    ChatSessionModel,
    CitationModel,
    DocumentChunkModel,
    DocumentModel,
    GraphEdgeModel,
    GraphNodeModel,
    ProcessingJobModel,
)
from backend.app.pipelines.vectorless_pipeline import VectorlessDocumentPipeline
from backend.app.retrieval.citation_validator import CitationValidator
from backend.app.retrieval.text_search import TextSearchResult
from backend.app.retrieval.vectorless_retriever import VectorlessRetriever
from backend.app.storage.mongo_store import MongoVectorlessStore


class MongoVectorlessKnowledgeService:
    """Application service for MongoDB persistence and lexical retrieval."""

    _instance: Optional["MongoVectorlessKnowledgeService"] = None

    def __new__(cls) -> "MongoVectorlessKnowledgeService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self) -> None:
        self.store = MongoVectorlessStore()
        self.graph_engine = GraphEngine()
        self.pipeline = VectorlessDocumentPipeline(self.graph_engine)
        self.retriever = VectorlessRetriever(self.store, self.graph_engine)
        self.citation_validator = CitationValidator()

        self.documents: Dict[str, DocumentModel] = self.store.load_documents()
        self.document_chunks: Dict[str, List[DocumentChunkModel]] = {}
        self.jobs: Dict[str, ProcessingJobModel] = self.store.load_jobs()
        self.chat_sessions: Dict[str, ChatSessionModel] = self.store.load_sessions()
        self.metrics: Dict[str, Any] = {
            "query_count": 0,
            "processing_count": 0,
            "failed_jobs": 0,
            "total_llm_latency_ms": 0.0,
            "total_graph_query_latency_ms": 0.0,
            "total_text_search_latency_ms": 0.0,
            "total_query_latency_ms": 0.0,
            "total_tokens_consumed": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "last_query_at": None,
            "last_processing_at": None,
        }
        self.metrics.update(self.store.load_metrics())
        self.settings = {
            "llm_provider": "groq",
            "retrieval_mode": "vectorless_text",
            "knowledge_graph_enabled": os.getenv("ENABLE_KNOWLEDGE_GRAPH", "false").lower() == "true",
            "temperature": 0.2,
            "top_k_retrieval": int(os.getenv("TOP_K_RETRIEVAL", "5")),
            "max_graph_hops": 3,
            "appearance": "light",
        }
        stored_settings = self.store.load_settings()
        self.settings.update(stored_settings)
        self.settings["llm_provider"] = "groq"
        self.settings["retrieval_mode"] = "vectorless_text"
        self.settings["knowledge_graph_enabled"] = (
            os.getenv("ENABLE_KNOWLEDGE_GRAPH", "false").lower() == "true"
        )

        nodes, edges = self.store.load_graph()
        for node in nodes:
            self.graph_engine.add_node(node)
        for edge in edges:
            self.graph_engine.add_edge(edge)

    def get_chunks(self, document_id: str) -> List[DocumentChunkModel]:
        if document_id not in self.document_chunks:
            self.document_chunks[document_id] = self.store.load_sections(document_id)
        return self.document_chunks[document_id]

    def persist_document(self, document: DocumentModel) -> None:
        document.updated_at = datetime.now().isoformat()
        self.store.save_document(document)
        self.documents[document.id] = document

    def persist_job(self, job: ProcessingJobModel) -> None:
        self.store.save_job(job)
        self.jobs[job.id] = job

    def persist_session(self, session: ChatSessionModel) -> None:
        self.store.save_session(session)
        self.chat_sessions[session.id] = session

    def persist_metrics(self) -> None:
        self.store.save_metrics(self.metrics)

    def persist_graph(self) -> None:
        self.store.replace_graph(
            self.graph_engine.get_all_nodes(),
            self.graph_engine.get_all_edges(),
        )

    def save_settings(self) -> None:
        self.store.save_settings(self.settings)

    def process_document(
        self,
        document: DocumentModel,
        file_path: str,
        job: ProcessingJobModel,
    ) -> Dict[str, Any]:
        self.metrics["processing_count"] += 1
        result = self.pipeline.process(document=document, file_path=file_path, job=job)
        sections = result.get("chunks", [])
        for section in sections:
            section.metadata = {
                **section.metadata,
                "source": document.filename,
                "retrieval_mode": "vectorless_text",
            }
        self.store.save_sections(document.id, sections)
        self.document_chunks[document.id] = sections
        self.persist_document(document)
        self.persist_job(job)
        self.persist_graph()
        self.metrics["last_processing_at"] = datetime.now().isoformat()
        if result.get("error"):
            self.metrics["failed_jobs"] += 1
        self.persist_metrics()

        # The original is durable in Cloudinary; remove the temporary Render
        # filesystem copy after indexing to avoid unnecessary disk usage.
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            pass
        return result

    def materialize_document(self, document: DocumentModel) -> str:
        if document.storage_path and os.path.exists(document.storage_path):
            return document.storage_path
        if not document.cloudinary_url:
            raise FileNotFoundError("The document original is unavailable in Cloudinary")
        upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        extension = document.file_type or "pdf"
        target = upload_dir / f"{document.id}_reprocess.{extension}"
        urllib.request.urlretrieve(document.cloudinary_url, target)
        document.storage_path = str(target)
        return str(target)

    def recover_cloudinary_documents(self) -> Dict[str, int]:
        """MongoDB is durable; startup-wide Cloudinary reindexing is disabled."""
        return {"found": 0, "recovered": 0, "failed": 0}

    def delete_document_state(self, document_id: str) -> None:
        self.store.delete_document(document_id)
        self.documents.pop(document_id, None)
        self.document_chunks.pop(document_id, None)
        for job_id in [job_id for job_id, job in self.jobs.items() if job.document_id == document_id]:
            self.jobs.pop(job_id, None)
        self.graph_engine.delete_by_document(document_id)
        self.persist_graph()

    def ask(self, query: str, session_id: Optional[str] = "session_default") -> ChatMessageModel:
        request_started = time.perf_counter()
        retrieval_result = self.retriever.retrieve(
            query=query,
            top_k=int(self.settings.get("top_k_retrieval", 5)),
            max_hops=int(self.settings.get("max_graph_hops", 3)),
        )
        llm = get_llm_provider("groq")
        llm_started = time.perf_counter()
        llm_response = llm.generate_answer(
            query=query,
            context=retrieval_result.assembled_context,
            retrieval_result=retrieval_result,
            temperature=float(self.settings.get("temperature", 0.2)),
        )
        llm_latency_ms = round((time.perf_counter() - llm_started) * 1000, 3)

        validated, validation = self.citation_validator.validate(
            llm_response.answer,
            llm_response.citations,
            retrieval_result,
        )
        retrieval_result.retrieval_trace.update(
            {
                "citation_validation": validation,
                "llm_grounded": llm_response.grounded,
                "uncertainty_noted": llm_response.uncertainty_noted,
                "llm_model": llm_response.model,
                "llm_latency_ms": llm_latency_ms,
                "total_query_latency_ms": round((time.perf_counter() - request_started) * 1000, 3),
            }
        )

        citations = [
            CitationModel(
                id=f"cit_{item.get('citation_index', index)}",
                citation_index=item.get("citation_index", index),
                document_id=item.get("document_id", ""),
                document_name=item.get("document_name", ""),
                page=item.get("page", 1),
                chunk_id=item.get("chunk_id", ""),
                snippet=item.get("snippet", ""),
                similarity_score=item.get("similarity_score"),
            )
            for index, item in enumerate(validated, 1)
        ]
        assistant = ChatMessageModel(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            session_id=session_id or "session_default",
            role="assistant",
            content=llm_response.answer,
            retrieval_type=retrieval_result.query_type,
            citations=citations,
            graph_evidence_paths=retrieval_result.graph_evidence_paths,
            retrieval_trace=retrieval_result.retrieval_trace,
            query_plan=[step.description for step in retrieval_result.query_plan.steps],
            created_at=datetime.now().isoformat(),
        )

        if session_id:
            session = self.chat_sessions.get(session_id) or ChatSessionModel(
                id=session_id,
                title=query[:40],
                messages=[],
            )
            session.messages.extend(
                [
                    ChatMessageModel(
                        id=f"msg_user_{uuid.uuid4().hex[:8]}",
                        session_id=session_id,
                        role="user",
                        content=query,
                        retrieval_type=retrieval_result.query_type,
                    ),
                    assistant,
                ]
            )
            self.persist_session(session)

        trace = retrieval_result.retrieval_trace
        self.metrics["query_count"] += 1
        self.metrics["total_llm_latency_ms"] += llm_latency_ms
        self.metrics["total_graph_query_latency_ms"] += float(trace.get("graph_query_latency_ms", 0))
        self.metrics["total_text_search_latency_ms"] += float(trace.get("text_search_latency_ms", 0))
        self.metrics["total_query_latency_ms"] += float(trace.get("total_query_latency_ms", 0))
        self.metrics["total_tokens_consumed"] += int(llm_response.tokens_used or 0)
        self.metrics["total_prompt_tokens"] += int(llm_response.prompt_tokens or 0)
        self.metrics["total_completion_tokens"] += int(llm_response.completion_tokens or 0)
        self.metrics["last_query_at"] = datetime.now().isoformat()
        self.persist_metrics()
        return assistant

    def get_metrics(self) -> Dict[str, Any]:
        nodes = self.graph_engine.get_all_nodes()
        edges = self.graph_engine.get_all_edges()
        query_count = max(1, int(self.metrics.get("query_count", 0)))
        return {
            "documents": {
                "total": len(self.documents),
                "processed": sum(document.status == "completed" for document in self.documents.values()),
                "processing": sum(document.status in {"uploading", "processing"} for document in self.documents.values()),
            },
            "entities": {
                "total": len(nodes),
                "people": sum(node.type.lower() == "person" for node in nodes),
                "companies": sum(node.type.lower() in {"company", "organization"} for node in nodes),
                "projects": sum(node.type.lower() == "project" for node in nodes),
                "technologies": sum(node.type.lower() in {"technology", "database", "framework"} for node in nodes),
            },
            "relationships": {"total": len(edges), "recent": len(edges)},
            "knowledge_sources": {
                "total_chunks": self.store.count_sections(),
                "total_indexed_sources": len(self.documents),
            },
            "system_status": "Knowledge Base Online",
            "retrieval_mode": "vectorless_text",
            "latency": {
                "llm_latency_ms": round(self.metrics["total_llm_latency_ms"] / query_count, 2),
                "graph_query_latency_ms": round(self.metrics["total_graph_query_latency_ms"] / query_count, 2),
                "text_search_latency_ms": round(self.metrics["total_text_search_latency_ms"] / query_count, 2),
                "total_query_latency_ms": round(self.metrics["total_query_latency_ms"] / query_count, 2),
            },
            "token_usage": {
                "total_tokens_consumed": int(self.metrics["total_tokens_consumed"]),
                "total_prompt_tokens": int(self.metrics["total_prompt_tokens"]),
                "total_completion_tokens": int(self.metrics["total_completion_tokens"]),
            },
            "query_count": int(self.metrics["query_count"]),
            "processing_count": int(self.metrics["processing_count"]),
            "failed_jobs": int(self.metrics["failed_jobs"]),
            "last_query_at": self.metrics.get("last_query_at"),
            "last_processing_at": self.metrics.get("last_processing_at"),
            "llm_provider": "groq",
            "embedding": None,
        }

    def text_search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[TextSearchResult]:
        document_id = (filters or {}).get("document_id")
        raw = self.store.search_sections(query, top_k=top_k, document_id=document_id)
        max_score = max((float(item.get("score", 0)) for item in raw), default=1.0)
        return [
            TextSearchResult(
                section_id=str(item.get("id", "")),
                document_id=str(item.get("document_id", "")),
                text=str(item.get("text", "")),
                page=item.get("page_number") or 1,
                source=str(item.get("metadata", {}).get("source", "")),
                relevance=round(float(item.get("score", 0)) / max_score, 4) if max_score else 0,
                entities=list(item.get("entities") or []),
                metadata=dict(item.get("metadata") or {}),
            )
            for item in raw
        ]
