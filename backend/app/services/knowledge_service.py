import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from backend.app.models.schema import DocumentModel, DocumentChunkModel, GraphNodeModel, GraphEdgeModel, ProcessingJobModel, ChatMessageModel, ChatSessionModel, CitationModel
from backend.app.graph.graph_engine import GraphEngine
from backend.app.retrieval.vector_store import VectorStore, VectorRecord
from backend.app.retrieval.hybrid_retriever import HybridRetriever
from backend.app.retrieval.citation_validator import CitationValidator
from backend.app.embeddings.embedding_engine import EmbeddingEngine
from backend.app.pipelines.document_pipeline import DocumentProcessingPipeline
from backend.app.llm.providers import get_llm_provider
from ingestion.normalization.conflict_detector import ConflictDetector
from backend.app.local_db import LocalDatabase

class KnowledgeService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        self.graph_engine = GraphEngine()
        self.vector_store = VectorStore(
            embedding_engine=EmbeddingEngine(
                model_name=os.getenv(
                    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
                )
            )
        )
        self.pipeline = DocumentProcessingPipeline(self.graph_engine, self.vector_store)
        self.retriever = HybridRetriever(self.graph_engine, self.vector_store)
        self.citation_validator = CitationValidator()
        self.conflict_detector = ConflictDetector()

        self.documents: Dict[str, DocumentModel] = {}
        self.document_chunks: Dict[str, List[DocumentChunkModel]] = {}
        self.jobs: Dict[str, ProcessingJobModel] = {}
        self.chat_sessions: Dict[str, ChatSessionModel] = {}
        self.db = LocalDatabase()
        self.metrics = {
            "query_count": 0,
            "processing_count": 0,
            "failed_jobs": 0,
            "total_llm_latency_ms": 0.0,
            "total_embedding_latency_ms": 0.0,
            "total_graph_query_latency_ms": 0.0,
            "total_vector_search_latency_ms": 0.0,
            "total_query_latency_ms": 0.0,
            "total_tokens_consumed": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "last_query_at": None,
            "last_processing_at": None,
        }

        # System configuration settings
        self.settings = {
            "llm_provider": "groq",
            "embedding_model": os.getenv(
                "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            "embedding_device": os.getenv("EMBEDDING_DEVICE", "cpu"),
            "knowledge_graph_enabled": os.getenv("ENABLE_KNOWLEDGE_GRAPH", "false").lower() == "true",
            "temperature": 0.2,
            "top_k_retrieval": 5,
            "max_graph_hops": 3,
            "entity_resolution_threshold": 0.85,
            "relationship_confidence_threshold": 0.70,
            "appearance": "light",
        }
        self._load_local_state()

    def recover_cloudinary_documents(self) -> Dict[str, int]:
        """Restore documents missing from ephemeral Render storage.

        Cloudinary stores the original files, while SQLite stores the derived
        document and graph data.  When Render recreates the instance, the
        SQLite file can be empty even though the originals still exist.  This
        method downloads only those missing originals and sends them through
        the normal pipeline so chunks, embeddings, entities, and relationships
        are rebuilt consistently.
        """
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        if not all((cloud_name, api_key, api_secret)):
            return {"found": 0, "recovered": 0, "failed": 0}

        import cloudinary  # pyright: ignore[reportMissingImports]
        import cloudinary.api  # pyright: ignore[reportMissingImports]

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

        resources = cloudinary.api.resources(
            resource_type="raw",
            type="upload",
            prefix="insightgraph/documents/",
            max_results=500,
        ).get("resources", [])
        recovered = 0
        failed = 0

        for resource in resources:
            public_id = str(resource.get("public_id", ""))
            if not public_id or public_id in {
                doc.cloudinary_public_id for doc in self.documents.values()
            }:
                continue

            try:
                filename = self._cloudinary_filename(resource)
                extension = Path(filename).suffix.lower().lstrip(".")
                if extension not in {"txt", "md", "markdown", "html", "htm", "pdf", "docx"}:
                    print(f"Skipping Cloudinary asset with unsupported format: {public_id}")
                    continue

                doc_id = self._cloudinary_document_id(public_id)
                content = urllib.request.urlopen(
                    str(resource["secure_url"]), timeout=60
                ).read()
                storage_path = self._write_recovered_file(content, doc_id, extension)
                document = DocumentModel(
                    id=doc_id,
                    filename=filename,
                    file_type=extension,
                    file_size=len(content),
                    storage_path=storage_path,
                    cloudinary_public_id=public_id,
                    cloudinary_url=resource.get("secure_url"),
                    status="processing",
                    current_stage="Recovery",
                    progress=5,
                )
                job = ProcessingJobModel(
                    id=f"job_recovery_{doc_id.removeprefix('doc_')}",
                    document_id=doc_id,
                    filename=filename,
                    status="processing",
                    current_stage="Recovery",
                    progress=5,
                )
                self.documents[doc_id] = document
                self.jobs[job.id] = job
                self.persist_document(document)
                self.persist_job(job)
                self.process_document(document, storage_path, job)
                recovered += 1
            except Exception as exc:
                failed += 1
                print(f"Cloudinary recovery failed for {public_id}: {type(exc).__name__}: {exc}")

        return {"found": len(resources), "recovered": recovered, "failed": failed}

    @staticmethod
    def _cloudinary_document_id(public_id: str) -> str:
        filename = public_id.rsplit("/", 1)[-1]
        parts = filename.split("_", 2)
        if len(parts) >= 2 and parts[0] == "doc":
            return f"{parts[0]}_{parts[1]}"
        return filename

    @staticmethod
    def _cloudinary_filename(resource: Dict[str, Any]) -> str:
        context = resource.get("context") or {}
        custom = context.get("custom") if isinstance(context, dict) else {}
        original = custom.get("original_filename") if isinstance(custom, dict) else None
        if original:
            return Path(str(original)).name
        public_id = str(resource.get("public_id", "")).rsplit("/", 1)[-1]
        parts = public_id.split("_", 2)
        stem = parts[2] if len(parts) >= 3 else (parts[-1] or "recovered-document")
        # Older raw Cloudinary uploads did not preserve the extension in the
        # public ID or resource metadata. All legacy assets in this project
        # were PDFs; new uploads carry the exact original filename in context.
        file_format = str(resource.get("format") or "pdf").lower()
        if file_format in {"", "bin", "raw"}:
            file_format = "pdf"
        return f"{stem}.{file_format}"

    @staticmethod
    def _write_recovered_file(content: bytes, document_id: str, extension: str) -> str:
        upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"{document_id}_recovered.{extension}"
        path.write_bytes(content)
        return str(path)
    def recover_cloudinary_documents(self) -> Dict[str, int]:
        """Restore documents missing from ephemeral Render storage.

        Cloudinary stores the original files, while SQLite stores the derived
        document and graph data.  When Render recreates the instance, the
        SQLite file can be empty even though the originals still exist.  This
        method downloads only those missing originals and sends them through
        the normal pipeline so chunks, embeddings, entities, and relationships
        are rebuilt consistently.
        """
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        if not all((cloud_name, api_key, api_secret)):
            return {"found": 0, "recovered": 0, "failed": 0}

        import cloudinary  # pyright: ignore[reportMissingImports]
        import cloudinary.api  # pyright: ignore[reportMissingImports]

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

        resources = cloudinary.api.resources(
            resource_type="raw",
            type="upload",
            prefix="insightgraph/documents/",
            max_results=500,
        ).get("resources", [])
        recovered = 0
        failed = 0

        for resource in resources:
            public_id = str(resource.get("public_id", ""))
            if not public_id or public_id in {
                doc.cloudinary_public_id for doc in self.documents.values()
            }:
                continue

            try:
                filename = self._cloudinary_filename(resource)
                extension = Path(filename).suffix.lower().lstrip(".")
                if extension not in {"txt", "md", "markdown", "html", "htm", "pdf", "docx"}:
                    print(f"Skipping Cloudinary asset with unsupported format: {public_id}")
                    continue

                doc_id = self._cloudinary_document_id(public_id)
                content = urllib.request.urlopen(
                    str(resource["secure_url"]), timeout=60
                ).read()
                storage_path = self._write_recovered_file(content, doc_id, extension)
                document = DocumentModel(
                    id=doc_id,
                    filename=filename,
                    file_type=extension,
                    file_size=len(content),
                    storage_path=storage_path,
                    cloudinary_public_id=public_id,
                    cloudinary_url=resource.get("secure_url"),
                    status="processing",
                    current_stage="Recovery",
                    progress=5,
                )
                job = ProcessingJobModel(
                    id=f"job_recovery_{doc_id.removeprefix('doc_')}",
                    document_id=doc_id,
                    filename=filename,
                    status="processing",
                    current_stage="Recovery",
                    progress=5,
                )
                self.documents[doc_id] = document
                self.jobs[job.id] = job
                self.persist_document(document)
                self.persist_job(job)
                self.process_document(document, storage_path, job)
                recovered += 1
            except Exception as exc:
                failed += 1
                print(f"Cloudinary recovery failed for {public_id}: {type(exc).__name__}: {exc}")

        return {"found": len(resources), "recovered": recovered, "failed": failed}

    @staticmethod
    def _cloudinary_document_id(public_id: str) -> str:
        filename = public_id.rsplit("/", 1)[-1]
        parts = filename.split("_", 2)
        if len(parts) >= 2 and parts[0] == "doc":
            return f"{parts[0]}_{parts[1]}"
        return filename

    @staticmethod
    def _cloudinary_filename(resource: Dict[str, Any]) -> str:
        context = resource.get("context") or {}
        custom = context.get("custom") if isinstance(context, dict) else {}
        original = custom.get("original_filename") if isinstance(custom, dict) else None
        if original:
            return Path(str(original)).name
        public_id = str(resource.get("public_id", "")).rsplit("/", 1)[-1]
        parts = public_id.split("_", 2)
        stem = parts[2] if len(parts) >= 3 else (parts[-1] or "recovered-document")
        # Older raw Cloudinary uploads did not preserve the extension in the
        # public ID or resource metadata. All legacy assets in this project
        # were PDFs; new uploads carry the exact original filename in context.
        file_format = str(resource.get("format") or "pdf").lower()
        if file_format in {"", "bin", "raw"}:
            file_format = "pdf"
        return f"{stem}.{file_format}"

    @staticmethod
    def _write_recovered_file(content: bytes, document_id: str, extension: str) -> str:
        upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"{document_id}_recovered.{extension}"
        path.write_bytes(content)
        return str(path)

    @staticmethod
    def _dump(model: Any) -> Dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="json")
        return model.dict()

    def _load_local_state(self) -> None:
        """Restore the local SQLite state after a process restart."""
        for key, payload in self.db.load("documents").items():
            self.documents[key] = DocumentModel.model_validate(payload)
        for key, payload in self.db.load("chunks").items():
            chunk = DocumentChunkModel.model_validate(payload)
            self.document_chunks.setdefault(chunk.document_id, []).append(chunk)
        for chunks in self.document_chunks.values():
            chunks.sort(key=lambda chunk: chunk.chunk_index)
        for key, payload in self.db.load("jobs").items():
            self.jobs[key] = ProcessingJobModel.model_validate(payload)
        for key, payload in self.db.load("sessions").items():
            self.chat_sessions[key] = ChatSessionModel.model_validate(payload)
        for key, payload in self.db.load("settings").items():
            if key == "config" and isinstance(payload, dict):
                self.settings.update(payload)
        stored_metrics = self.db.load("metrics").get("runtime")
        if isinstance(stored_metrics, dict):
            self.metrics.update(stored_metrics)
        # Migrate any old settings that referenced removed providers.
        self.settings["llm_provider"] = "groq"
        # Environment configuration is the source of truth for runtime
        # feature flags; an older SQLite settings record must not silently
        # disable a feature the user enabled in .env.
        self.settings["knowledge_graph_enabled"] = os.getenv(
            "ENABLE_KNOWLEDGE_GRAPH", "false"
        ).lower() == "true"
        self.settings["embedding_model"] = os.getenv(
            "EMBEDDING_MODEL", self.settings.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        )
        self.settings["embedding_device"] = os.getenv(
            "EMBEDDING_DEVICE", self.settings.get("embedding_device", "cpu")
        )

        for payload in self.db.load("graph_nodes").values():
            self.graph_engine.add_node(GraphNodeModel.model_validate(payload))
        for payload in self.db.load("graph_edges").values():
            self.graph_engine.add_edge(GraphEdgeModel.model_validate(payload))
        for payload in self.db.load("vectors").values():
            self.vector_store.upsert(VectorRecord.model_validate(payload))

    def persist_graph(self) -> None:
        self.db.clear("graph_nodes")
        self.db.clear("graph_edges")
        for node in self.graph_engine.get_all_nodes():
            self.db.upsert("graph_nodes", node.id, self._dump(node))
        for edge in self.graph_engine.get_all_edges():
            self.db.upsert("graph_edges", edge.id, self._dump(edge))

    def persist_vectors(self) -> None:
        self.db.clear("vectors")
        for record in self.vector_store.records.values():
            self.db.upsert("vectors", record.id, self._dump(record))

    def persist_document(self, document: DocumentModel) -> None:
        self.db.upsert("documents", document.id, self._dump(document))

    def persist_job(self, job: ProcessingJobModel) -> None:
        self.db.upsert("jobs", job.id, self._dump(job))

    def persist_session(self, session: ChatSessionModel) -> None:
        self.db.upsert("sessions", session.id, self._dump(session))

    def persist_metrics(self) -> None:
        self.db.upsert("metrics", "runtime", self.metrics)

    def persist_all(self) -> None:
        for document in self.documents.values():
            self.persist_document(document)
        self.db.clear("chunks")
        for chunks in self.document_chunks.values():
            for chunk in chunks:
                self.db.upsert("chunks", chunk.id, self._dump(chunk))
        for job in self.jobs.values():
            self.persist_job(job)
        for session in self.chat_sessions.values():
            self.persist_session(session)
        self.db.upsert("settings", "config", self.settings)
        self.persist_metrics()
        self.persist_graph()
        self.persist_vectors()

    def process_document(self, document: DocumentModel, file_path: str, job: ProcessingJobModel) -> Dict[str, Any]:
        self.metrics["processing_count"] += 1
        result = self.pipeline.process(document=document, file_path=file_path, job=job)
        chunks = result.get("chunks")
        if chunks is not None:
            self.document_chunks[document.id] = chunks
        self.persist_all()
        self.metrics["last_processing_at"] = datetime.now().isoformat()
        if result.get("error"):
            self.metrics["failed_jobs"] += 1
        self.persist_metrics()
        return result

    def ask(self, query: str, session_id: Optional[str] = "session_default") -> ChatMessageModel:
        request_started = time.perf_counter()
        retrieval_started = time.perf_counter()
        retrieval_result = self.retriever.retrieve(
            query=query,
            top_k=int(self.settings.get("top_k_retrieval", 5)),
            max_hops=int(self.settings.get("max_graph_hops", 3))
        )
        retrieval_latency_ms = round((time.perf_counter() - retrieval_started) * 1000, 3)
        llm = get_llm_provider(self.settings.get("llm_provider", "groq"))
        llm_started = time.perf_counter()
        llm_response = llm.generate_answer(
            query=query,
            context=retrieval_result.assembled_context,
            retrieval_result=retrieval_result,
            temperature=float(self.settings.get("temperature", 0.2))
        )
        llm_latency_ms = round((time.perf_counter() - llm_started) * 1000, 3)

        validated_citations, citation_validation = self.citation_validator.validate(
            llm_response.answer,
            llm_response.citations,
            retrieval_result,
        )
        retrieval_result.retrieval_trace["citation_validation"] = citation_validation
        retrieval_result.retrieval_trace["llm_grounded"] = llm_response.grounded
        retrieval_result.retrieval_trace["uncertainty_noted"] = llm_response.uncertainty_noted
        retrieval_result.retrieval_trace["llm_model"] = llm_response.model
        retrieval_result.retrieval_trace["llm_latency_ms"] = llm_latency_ms
        retrieval_result.retrieval_trace["total_query_latency_ms"] = round(
            (time.perf_counter() - request_started) * 1000, 3
        )

        import uuid
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"

        citations_models = [
            CitationModel(
                id=f"cit_{c.get('citation_index', idx)}",
                citation_index=c.get("citation_index", idx),
                document_id=c.get("document_id", ""),
                document_name=c.get("document_name", ""),
                page=c.get("page", 1),
                chunk_id=c.get("chunk_id", ""),
                snippet=c.get("snippet", ""),
                similarity_score=c.get("similarity_score"),
            )
            for idx, c in enumerate(validated_citations, 1)
        ]

        assistant_msg = ChatMessageModel(
            id=msg_id,
            session_id=session_id or "session_default",
            role="assistant",
            content=llm_response.answer,
            retrieval_type=retrieval_result.query_type,
            citations=citations_models,
            graph_evidence_paths=retrieval_result.graph_evidence_paths,
            retrieval_trace=retrieval_result.retrieval_trace,
            query_plan=[s.description for s in retrieval_result.query_plan.steps],
            created_at=datetime.now().isoformat(),
        )

        if session_id:
            if session_id not in self.chat_sessions:
                self.chat_sessions[session_id] = ChatSessionModel(
                    id=session_id,
                    title=query[:40],
                    messages=[]
                )
            # Add user message
            user_msg = ChatMessageModel(
                id=f"msg_user_{uuid.uuid4().hex[:8]}",
                session_id=session_id,
                role="user",
                content=query,
                retrieval_type=retrieval_result.query_type,
            )
            self.chat_sessions[session_id].messages.append(user_msg)
            self.chat_sessions[session_id].messages.append(assistant_msg)
            self.persist_session(self.chat_sessions[session_id])

        trace = retrieval_result.retrieval_trace
        self.metrics["query_count"] += 1
        self.metrics["total_llm_latency_ms"] += llm_latency_ms
        self.metrics["total_embedding_latency_ms"] += float(trace.get("embedding_latency_ms", 0.0))
        self.metrics["total_graph_query_latency_ms"] += float(trace.get("graph_query_latency_ms", 0.0))
        self.metrics["total_vector_search_latency_ms"] += float(trace.get("vector_search_latency_ms", 0.0))
        self.metrics["total_query_latency_ms"] += float(trace.get("total_query_latency_ms", 0.0))
        self.metrics["total_tokens_consumed"] += int(llm_response.tokens_used or 0)
        self.metrics["total_prompt_tokens"] += int(llm_response.prompt_tokens or 0)
        self.metrics["total_completion_tokens"] += int(llm_response.completion_tokens or 0)
        self.metrics["last_query_at"] = datetime.now().isoformat()
        self.persist_metrics()

        return assistant_msg

    def get_metrics(self) -> Dict[str, Any]:
        edges = self.graph_engine.get_all_edges()
        nodes = self.graph_engine.get_all_nodes()
        chunks_count = sum(len(c) for c in self.document_chunks.values())

        people_count = sum(1 for n in nodes if n.type.lower() == "person")
        companies_count = sum(1 for n in nodes if n.type.lower() in ["company", "organization"])
        projects_count = sum(1 for n in nodes if n.type.lower() == "project")
        technologies_count = sum(1 for n in nodes if n.type.lower() in ["technology", "programming_language", "database", "framework"])

        query_count = max(1, int(self.metrics.get("query_count", 0)))

        return {
            "documents": {
                "total": len(self.documents),
                "processed": sum(1 for d in self.documents.values() if d.status == "completed"),
                "processing": sum(1 for d in self.documents.values() if d.status in ["uploading", "processing"]),
            },
            "entities": {
                "total": len(nodes),
                "people": people_count,
                "companies": companies_count,
                "projects": projects_count,
                "technologies": technologies_count,
            },
            "relationships": {
                "total": len(edges),
                "recent": len(edges),
            },
            "knowledge_sources": {
                "total_chunks": max(chunks_count, self.vector_store.count()),
                "total_embeddings": self.vector_store.count(),
                "total_indexed_sources": len(self.documents),
            },
            "system_status": "Knowledge Base Online",
            "latency": {
                "llm_latency_ms": round(self.metrics["total_llm_latency_ms"] / query_count, 2),
                "embedding_latency_ms": round(self.metrics["total_embedding_latency_ms"] / query_count, 2),
                "graph_query_latency_ms": round(self.metrics["total_graph_query_latency_ms"] / query_count, 2),
                "vector_search_latency_ms": round(self.metrics["total_vector_search_latency_ms"] / query_count, 2),
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
            "llm_provider": self.settings.get("llm_provider", "groq"),
            "embedding": self.vector_store.embedding_engine.status(),
        }
