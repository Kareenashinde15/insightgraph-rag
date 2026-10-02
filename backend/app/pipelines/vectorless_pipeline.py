"""Document indexing pipeline for the MongoDB-backed vectorless mode."""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Optional

from backend.app.graph.graph_engine import GraphEngine
from backend.app.models.schema import (
    DocumentChunkModel,
    DocumentModel,
    GraphEdgeModel,
    GraphNodeModel,
    ProcessingJobModel,
)
from ingestion.chunking.chunker import ConfigurableChunker
from ingestion.extraction.entity_extractor import HybridEntityExtractor
from ingestion.extraction.relationship_extractor import RelationshipExtractor
from ingestion.normalization.conflict_detector import ConflictDetector
from ingestion.normalization.normalizer import EntityNormalizer
from ingestion.parsers.parser_factory import ParserFactory


class VectorlessDocumentPipeline:
    """Parse documents into searchable text sections without embeddings."""

    def __init__(self, graph_engine: GraphEngine):
        self.graph_engine = graph_engine
        self.chunker = ConfigurableChunker(target_chunk_size=400, overlap_size=80)
        self.entity_extractor = HybridEntityExtractor()
        self.relationship_extractor = RelationshipExtractor()
        self.normalizer = EntityNormalizer()
        self.conflict_detector = ConflictDetector()
        self.enable_knowledge_graph = os.getenv("ENABLE_KNOWLEDGE_GRAPH", "false").lower() == "true"

    def process(
        self,
        document: DocumentModel,
        file_path: str,
        job: Optional[ProcessingJobModel] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        started = time.time()
        stage_logs = []

        def log_stage(name: str, progress: int, details: str = "") -> None:
            entry = {"stage": name, "progress": progress, "timestamp": time.time(), "details": details}
            stage_logs.append(entry)
            if job:
                job.current_stage = name
                job.progress = progress
                job.stages_log.append(entry)
            if progress_callback:
                progress_callback(name, progress)

        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            log_stage("Extract Text", 25, f"Parsing {document.filename}")
            parsed = ParserFactory.parse_file(file_path, document.filename)
            if not parsed.raw_text.strip():
                details = "; ".join((parsed.metadata.get("parse_errors") or [])[:3])
                raise ValueError("No extractable text was found." + (f" {details}" if details else ""))

            log_stage("Build Text Sections", 45, "Creating page-aware lexical sections")
            sections = self.chunker.chunk_document(document.id, parsed.pages)
            document.raw_text = ""
            document.chunk_count = len(sections)

            extracted_entities = []
            extracted_relationships = []
            conflicts = []

            if self.enable_knowledge_graph:
                log_stage("Extract Entities", 60, "Extracting optional entities")
                for section in sections:
                    found = self.entity_extractor.extract_entities(
                        section.text,
                        page_number=section.page_number or 1,
                        chunk_id=section.id,
                    )
                    section.entities = [entity.name for entity in found]
                    extracted_entities.extend(found)

                log_stage("Extract Relationships", 70, "Extracting optional relationships")
                for section in sections:
                    extracted_relationships.extend(
                        self.relationship_extractor.extract_relationships(
                            text=section.text,
                            entities=extracted_entities,
                            document_id=document.id,
                            chunk_id=section.id,
                            page_number=section.page_number or 1,
                        )
                    )

                existing = [
                    {"id": node.id, "name": node.name, "type": node.type, "aliases": node.aliases}
                    for node in self.graph_engine.get_all_nodes()
                ]
                resolved: Dict[str, str] = {}
                for entity in extracted_entities:
                    canonical, _, existing_id = self.normalizer.resolve_entity(
                        entity.name, entity.type, existing, threshold=0.85
                    )
                    resolved[entity.name.lower()] = canonical
                    node_id = existing_id or f"node_{canonical.lower().replace(' ', '_').replace('.', '_')}"
                    node = self.graph_engine.nodes.get(node_id)
                    if node:
                        if document.id not in node.document_ids:
                            node.document_ids.append(document.id)
                        if entity.name != node.name and entity.name not in node.aliases:
                            node.aliases.append(entity.name)
                    else:
                        node = GraphNodeModel(
                            id=node_id,
                            name=canonical,
                            normalized_name=canonical.lower(),
                            type=entity.type.capitalize(),
                            confidence=entity.confidence,
                            document_ids=[document.id],
                            aliases=[entity.name] if entity.name != canonical else [],
                        )
                        self.graph_engine.add_node(node)
                        existing.append({"id": node.id, "name": node.name, "type": node.type, "aliases": node.aliases})

                conflicts = self.conflict_detector.detect_conflicts(
                    [relationship.model_dump() for relationship in extracted_relationships]
                )
                for relationship in extracted_relationships:
                    source = self.graph_engine.find_node_by_name(
                        resolved.get(relationship.source_entity.lower(), relationship.source_entity)
                    )
                    target = self.graph_engine.find_node_by_name(
                        resolved.get(relationship.target_entity.lower(), relationship.target_entity)
                    )
                    if source and target and source.id != target.id:
                        self.graph_engine.add_edge(
                            GraphEdgeModel(
                                id=f"edge_{source.id}_{relationship.relationship}_{target.id}",
                                source=source.id,
                                target=target.id,
                                relationship_type=relationship.relationship,
                                confidence=relationship.confidence,
                                source_document=relationship.source_document,
                                source_chunk=relationship.source_chunk,
                                source_page=relationship.source_page,
                                extraction_method=relationship.extraction_method,
                                start_date=relationship.start_date,
                                end_date=relationship.end_date,
                                original_text=relationship.original_text,
                            )
                        )
            else:
                log_stage("Optional Knowledge Graph Skipped", 90, "Vectorless text retrieval does not require graph extraction")

            document.entity_count = len(extracted_entities)
            document.relationship_count = len(extracted_relationships)
            document.status = "completed"
            document.current_stage = "Indexed"
            document.progress = 100
            duration = round(time.time() - started, 2)
            if job:
                job.status = "completed"
                job.current_stage = "Indexed"
                job.progress = 100
                job.duration_seconds = duration
                job.completion_time = time.strftime("%Y-%m-%dT%H:%M:%S")

            return {
                "document_id": document.id,
                "chunks": sections,
                "chunks_count": len(sections),
                "entities_count": len(extracted_entities),
                "relationships_count": len(extracted_relationships),
                "conflicts_count": len(conflicts),
                "duration_seconds": duration,
                "stages_log": stage_logs,
            }
        except Exception as exc:
            message = f"Pipeline failed: {type(exc).__name__}: {exc}"
            document.status = "failed"
            document.current_stage = f"Failed: {type(exc).__name__}"
            document.error_message = message
            if job:
                job.status = "failed"
                job.current_stage = f"Failed: {type(exc).__name__}"
                job.error_message = message
            return {
                "document_id": document.id,
                "error": message,
                "duration_seconds": round(time.time() - started, 2),
                "stages_log": stage_logs,
            }
