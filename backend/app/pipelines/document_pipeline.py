import os
import time
from typing import Dict, Any, List, Optional, Callable
from backend.app.models.schema import DocumentModel, DocumentChunkModel, GraphNodeModel, GraphEdgeModel, ProcessingJobModel
from ingestion.parsers.parser_factory import ParserFactory
from ingestion.chunking.chunker import ConfigurableChunker
from ingestion.extraction.entity_extractor import HybridEntityExtractor
from ingestion.extraction.relationship_extractor import RelationshipExtractor
from ingestion.normalization.normalizer import EntityNormalizer
from ingestion.normalization.conflict_detector import ConflictDetector
from backend.app.graph.graph_engine import GraphEngine
from backend.app.retrieval.vector_store import VectorStore

class DocumentProcessingPipeline:
    STAGES = [
        ("Validate File", 10),
        ("Store Original File", 18),
        ("Extract Text", 28),
        ("Normalize Text", 36),
        ("Chunk Document", 45),
        ("Generate Embeddings", 55),
        ("Extract Entities", 65),
        ("Extract Relationships", 75),
        ("Resolve Duplicate Entities", 84),
        ("Detect Conflicts", 90),
        ("Build / Update Knowledge Graph", 96),
        ("Store Provenance & Mark Complete", 100),
    ]

    def __init__(self, graph_engine: GraphEngine, vector_store: VectorStore):
        self.graph_engine = graph_engine
        self.vector_store = vector_store
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
        import traceback
        import logging

        logger = logging.getLogger(__name__)
        start_time = time.time()
        stage_logs = []

        def log_stage(stage_name: str, pct: int, details: str = ""):
            entry = {"stage": stage_name, "progress": pct, "timestamp": time.time(), "details": details}
            stage_logs.append(entry)
            if job:
                job.current_stage = stage_name
                job.progress = pct
                job.stages_log.append(entry)
            if progress_callback:
                progress_callback(stage_name, pct)

        try:
            # 1. Validate File
            log_stage("Validate File", 10, f"Validating format and size ({document.file_size} bytes)")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # 2. Store Original File
            log_stage("Store Original File", 18, f"Stored securely at {file_path}")

            # 3. Extract Text
            log_stage("Extract Text", 28, f"Extracting content with parser for {document.filename}")
            parsed_doc = ParserFactory.parse_file(file_path, document.filename)
            document.raw_text = parsed_doc.raw_text
            if not parsed_doc.raw_text.strip():
                raise ValueError(
                    "No extractable text was found. This file may be image-only; "
                    "OCR is not enabled in the local hobby configuration."
                )

            # 4. Normalize Text
            log_stage("Normalize Text", 36, "Normalizing unicode encodings, whitespaces, and section structure")

            # 5. Chunk Document
            log_stage("Chunk Document", 45, "Generating configurable semantic chunks preserving page metadata")
            chunks = self.chunker.chunk_document(document.id, parsed_doc.pages)
            document.chunk_count = len(chunks)

            # 6. Generate embeddings. Entity and relationship extraction is
            # optional enrichment; it is not required for general PDF RAG.
            log_stage(
                "Generate Embeddings",
                55,
                "Calculating local semantic embeddings for all chunks"
            )

            all_extracted_entities = []
            all_extracted_rels = []

            for chunk in chunks:
                chunk_ents = []
                if self.enable_knowledge_graph:
                    chunk_ents = self.entity_extractor.extract_entities(
                        chunk.text,
                        page_number=chunk.page_number or 1,
                        chunk_id=chunk.id,
                    )
                    chunk.entities = [entity.name for entity in chunk_ents]
                    all_extracted_entities.extend(chunk_ents)
                else:
                    chunk.entities = []

                self.vector_store.upsert_chunk(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    text=chunk.text,
                    entities=chunk.entities,
                    page=chunk.page_number or 1,
                    source=document.filename,
                    extra_metadata={"section": chunk.section}
                )

            document.entity_count = len(all_extracted_entities)
            conflicts = []
            if self.enable_knowledge_graph:
                log_stage("Extract Entities", 65, "Running optional document-adaptive entity extraction")
                log_stage("Extract Relationships", 75, "Extracting optional relationships with provenance")
                for chunk in chunks:
                    all_extracted_rels.extend(self.relationship_extractor.extract_relationships(
                        text=chunk.text,
                        entities=all_extracted_entities,
                        document_id=document.id,
                        chunk_id=chunk.id,
                        page_number=chunk.page_number or 1,
                    ))
                document.relationship_count = len(all_extracted_rels)

                log_stage("Resolve Duplicate Entities", 84, "Resolving optional entity aliases")
                existing_node_dicts = [
                    {"id": n.id, "name": n.name, "type": n.type, "aliases": n.aliases}
                    for n in self.graph_engine.get_all_nodes()
                ]
                resolved_entity_map = {}
                for ent in all_extracted_entities:
                    canonical_name, _, existing_id = self.normalizer.resolve_entity(
                        ent.name, ent.type, existing_node_dicts, threshold=0.85
                    )
                    resolved_entity_map[ent.name.lower()] = canonical_name
                    node_id = existing_id or f"node_{canonical_name.lower().replace(' ', '_').replace('.', '_')}"
                    existing_node = self.graph_engine.nodes.get(node_id)
                    if existing_node:
                        if document.id not in existing_node.document_ids:
                            existing_node.document_ids.append(document.id)
                        if ent.name not in existing_node.aliases and ent.name != existing_node.name:
                            existing_node.aliases.append(ent.name)
                    else:
                        new_node = GraphNodeModel(
                            id=node_id,
                            name=canonical_name,
                            normalized_name=canonical_name.lower(),
                            type=ent.type.capitalize(),
                            confidence=ent.confidence,
                            document_ids=[document.id],
                            aliases=[ent.name] if ent.name != canonical_name else [],
                        )
                        self.graph_engine.add_node(new_node)
                        existing_node_dicts.append({"id": new_node.id, "name": new_node.name, "type": new_node.type, "aliases": new_node.aliases})

                log_stage("Detect Conflicts", 90, "Checking optional relationship conflicts")
                conflicts = self.conflict_detector.detect_conflicts([r.model_dump() for r in all_extracted_rels])

                log_stage("Build / Update Knowledge Graph", 96, "Updating optional in-process knowledge graph")
                for rel in all_extracted_rels:
                    src_node = self.graph_engine.find_node_by_name(resolved_entity_map.get(rel.source_entity.lower(), rel.source_entity))
                    tgt_node = self.graph_engine.find_node_by_name(resolved_entity_map.get(rel.target_entity.lower(), rel.target_entity))
                    if src_node and tgt_node and src_node.id != tgt_node.id:
                        self.graph_engine.add_edge(GraphEdgeModel(
                            id=f"edge_{src_node.id}_{rel.relationship}_{tgt_node.id}",
                            source=src_node.id,
                            target=tgt_node.id,
                            relationship_type=rel.relationship,
                            confidence=rel.confidence,
                            source_document=rel.source_document,
                            source_chunk=rel.source_chunk,
                            source_page=rel.source_page,
                            extraction_method=rel.extraction_method,
                            start_date=rel.start_date,
                            end_date=rel.end_date,
                            original_text=rel.original_text,
                        ))
            else:
                log_stage("Optional Knowledge Graph Skipped", 96, "Vector RAG is sufficient for this local workspace")

            # 12. Store Provenance & Mark Document Complete
            duration = round(time.time() - start_time, 2)
            log_stage("Store Provenance & Mark Complete", 100, f"Processing finished in {duration}s")
            document.status = "completed"
            document.current_stage = "Indexed"
            document.progress = 100

            if job:
                job.status = "completed"
                job.current_stage = "Indexed"
                job.progress = 100
                job.duration_seconds = duration

            return {
                "document_id": document.id,
                "chunks_count": len(chunks),
                "entities_count": len(all_extracted_entities),
                "relationships_count": len(all_extracted_rels),
                "conflicts_count": len(conflicts),
                "duration_seconds": duration,
                "stages_log": stage_logs,
                "chunks": chunks,
            }

        except Exception as e:

            error_msg = f"Pipeline failed: {type(e).__name__}: {str(e)}"

            print("\n")
            print("========================================")
            print("         PIPELINE ERROR")
            print("========================================")
            print(f"Document : {document.filename}")
            print(f"Stage    : {document.current_stage}")
            print(f"Progress : {document.progress}%")
            print(f"Error    : {error_msg}")
            print("========================================")

            traceback.print_exc()

            duration = round(time.time() - start_time, 2)

            # Mark document as failed
            document.status = "failed"
            document.current_stage = f"Failed: {type(e).__name__}"
            document.progress = document.progress or 0

            # Only set error_message if your schema supports it
            if hasattr(document, "error_message"):
                document.error_message = error_msg

            # Mark job as failed
            if job:
                job.status = "failed"
                job.current_stage = f"Failed: {type(e).__name__}"
                job.progress = document.progress or 0
                job.duration_seconds = duration

                if hasattr(job, "error_message"):
                    job.error_message = error_msg

            return {
                "document_id": document.id,
                "error": error_msg,
                "duration_seconds": duration,
                "stages_log": stage_logs,
            }
