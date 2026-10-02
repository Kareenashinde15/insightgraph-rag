"""MongoDB persistence for the vectorless knowledge service.

MongoDB stores document metadata, page-aware text sections, jobs, sessions,
metrics, and the optional graph.  No embeddings are generated or persisted.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

from backend.app.models.schema import (
    ChatSessionModel,
    DocumentChunkModel,
    DocumentModel,
    GraphEdgeModel,
    GraphNodeModel,
    ProcessingJobModel,
)


class MongoVectorlessStore:
    """Small repository wrapper with explicit collections and indexes."""

    def __init__(self) -> None:
        uri = os.getenv("MONGODB_URI", "").strip()
        if not uri:
            raise RuntimeError(
                "MONGODB_URI is required when STORAGE_BACKEND=mongodb. "
                "Create a MongoDB Atlas connection string and add it to the environment."
            )

        try:
            from pymongo import ASCENDING, TEXT, MongoClient  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pymongo is required for the MongoDB storage backend") from exc

        self.client = MongoClient(
            uri,
            serverSelectionTimeoutMS=int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")),
            connectTimeoutMS=int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "5000")),
        )
        self.client.admin.command("ping")
        self.database = self.client[os.getenv("MONGODB_DATABASE", "insightgraph")]

        self.documents = self.database["documents"]
        # These are ordinary page-aware text chunks; they contain no vectors.
        self.sections = self.database["chunks"]
        self.jobs = self.database["processing_jobs"]
        self.sessions = self.database["chat_sessions"]
        self.metrics = self.database["metrics"]
        self.settings = self.database["settings"]
        self.graph_nodes = self.database["graph_nodes"]
        self.graph_edges = self.database["graph_edges"]

        self.documents.create_index([("id", ASCENDING)], unique=True)
        self.sections.create_index([("id", ASCENDING)], unique=True)
        self.sections.create_index([("document_id", ASCENDING), ("chunk_index", ASCENDING)])
        self.sections.create_index(
            [("search_text", TEXT), ("section", TEXT), ("paragraph", TEXT)],
            name="vectorless_text_search",
            weights={"search_text": 8, "section": 4, "paragraph": 2},
        )
        self.jobs.create_index([("id", ASCENDING)], unique=True)
        self.sessions.create_index([("id", ASCENDING)], unique=True)
        self.graph_nodes.create_index([("id", ASCENDING)], unique=True)
        self.graph_edges.create_index([("id", ASCENDING)], unique=True)

    @staticmethod
    def _dump(value: Any) -> Dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value

    @staticmethod
    def _clean(document: Dict[str, Any]) -> Dict[str, Any]:
        document = dict(document)
        document.pop("_id", None)
        document.pop("search_text", None)
        return document

    @staticmethod
    def _upsert(collection: Any, key: str, value: Any) -> None:
        payload = MongoVectorlessStore._dump(value)
        collection.replace_one({"id": payload[key]}, payload, upsert=True)

    def save_document(self, document: DocumentModel) -> None:
        self._upsert(self.documents, "id", document)

    def load_documents(self) -> Dict[str, DocumentModel]:
        return {
            item["id"]: DocumentModel.model_validate(self._clean(item))
            for item in self.documents.find({})
        }

    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        item = self.documents.find_one({"id": document_id})
        return DocumentModel.model_validate(self._clean(item)) if item else None

    def delete_document(self, document_id: str) -> None:
        self.documents.delete_one({"id": document_id})
        self.sections.delete_many({"document_id": document_id})
        self.jobs.delete_many({"document_id": document_id})
        self.graph_nodes.update_many(
            {"document_ids": document_id},
            {"$pull": {"document_ids": document_id}},
        )
        self.graph_nodes.delete_many({"document_ids": {"$size": 0}})
        self.graph_edges.delete_many({"source_document": document_id})

    def save_sections(self, document_id: str, sections: Iterable[DocumentChunkModel]) -> None:
        self.sections.delete_many({"document_id": document_id})
        payloads = []
        for section in sections:
            item = self._dump(section)
            item["search_text"] = " ".join(
                value for value in (
                    item.get("section") or "",
                    item.get("paragraph") or "",
                    item.get("text") or "",
                    " ".join(item.get("entities") or []),
                )
                if value
            )
            payloads.append(item)
        if payloads:
            self.sections.insert_many(payloads, ordered=False)

    def load_sections(self, document_id: Optional[str] = None) -> List[DocumentChunkModel]:
        query = {"document_id": document_id} if document_id else {}
        return [
            DocumentChunkModel.model_validate(self._clean(item))
            for item in self.sections.find(query).sort("chunk_index", 1)
        ]

    def count_sections(self) -> int:
        return int(self.sections.count_documents({}))

    def search_sections(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search text and summaries using MongoDB's ordinary text index.

        This is intentionally lexical retrieval.  It does not create vectors
        and does not use MongoDB Vector Search.
        """
        stop_words = {
            "what", "which", "where", "when", "who", "how", "does", "are",
            "the", "this", "that", "with", "from", "into", "about", "have",
            "document", "documents", "available", "workspace",
        }
        terms = [word.strip(".,?!:;()[]{}\"").lower() for word in query.split()]
        terms = [term for term in terms if len(term) > 2 and term not in stop_words]
        search_query = " ".join(terms) or query.strip()
        filter_query: Dict[str, Any] = {"$text": {"$search": search_query}}
        if document_id:
            filter_query["document_id"] = document_id

        try:
            cursor = self.sections.find(
                filter_query,
                {"score": {"$meta": "textScore"}},
            ).sort([("score", {"$meta": "textScore"})]).limit(top_k)
            results = list(cursor)
        except Exception:
            results = []

        # A small lexical fallback keeps local Mongo-compatible deployments
        # useful even when their text index has not been created yet.
        if not results:
            candidates = self.sections.find(
                {"document_id": document_id} if document_id else {}
            ).limit(2000)
            query_terms = set(terms)
            scored = []
            for item in candidates:
                haystack = str(item.get("search_text", "")).lower()
                score = sum(haystack.count(term) for term in query_terms)
                if score:
                    item["score"] = float(score)
                    scored.append(item)
            results = sorted(scored, key=lambda item: item.get("score", 0), reverse=True)[:top_k]

        return results

    def save_job(self, job: ProcessingJobModel) -> None:
        self._upsert(self.jobs, "id", job)

    def load_jobs(self) -> Dict[str, ProcessingJobModel]:
        return {
            item["id"]: ProcessingJobModel.model_validate(self._clean(item))
            for item in self.jobs.find({})
        }

    def save_session(self, session: ChatSessionModel) -> None:
        self._upsert(self.sessions, "id", session)

    def load_sessions(self) -> Dict[str, ChatSessionModel]:
        return {
            item["id"]: ChatSessionModel.model_validate(self._clean(item))
            for item in self.sessions.find({})
        }

    def save_metrics(self, value: Dict[str, Any]) -> None:
        self.metrics.replace_one({"id": "runtime"}, {"id": "runtime", **value}, upsert=True)

    def load_metrics(self) -> Dict[str, Any]:
        item = self.metrics.find_one({"id": "runtime"}) or {}
        return self._clean(item)

    def save_settings(self, value: Dict[str, Any]) -> None:
        self.settings.replace_one({"id": "config"}, {"id": "config", **value}, upsert=True)

    def load_settings(self) -> Dict[str, Any]:
        return self._clean(self.settings.find_one({"id": "config"}) or {})

    def replace_graph(self, nodes: Iterable[GraphNodeModel], edges: Iterable[GraphEdgeModel]) -> None:
        self.graph_nodes.delete_many({})
        self.graph_edges.delete_many({})
        node_payloads = [self._dump(node) for node in nodes]
        edge_payloads = [self._dump(edge) for edge in edges]
        if node_payloads:
            self.graph_nodes.insert_many(node_payloads, ordered=False)
        if edge_payloads:
            self.graph_edges.insert_many(edge_payloads, ordered=False)

    def load_graph(self) -> tuple[List[GraphNodeModel], List[GraphEdgeModel]]:
        nodes = [
            GraphNodeModel.model_validate(self._clean(item))
            for item in self.graph_nodes.find({})
        ]
        edges = [
            GraphEdgeModel.model_validate(self._clean(item))
            for item in self.graph_edges.find({})
        ]
        return nodes, edges
