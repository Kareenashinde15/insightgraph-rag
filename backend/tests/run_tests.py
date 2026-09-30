import os
import sys
# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ingestion.chunking.chunker import ConfigurableChunker
from ingestion.parsers.base import ParsedChunkDraft
from ingestion.extraction.entity_extractor import HybridEntityExtractor
from ingestion.extraction.relationship_extractor import RelationshipExtractor
from ingestion.normalization.normalizer import EntityNormalizer
from backend.app.graph.graph_engine import GraphEngine
from backend.app.models.schema import GraphNodeModel, GraphEdgeModel
from backend.app.services.knowledge_service import KnowledgeService

def test_chunking():
    chunker = ConfigurableChunker(target_chunk_size=50, overlap_size=10)
    drafts = [
        ParsedChunkDraft(page_number=1, section="Intro", paragraph="Alice worked at Microsoft.", text="Alice worked at Microsoft. She built scalable distributed systems.")
    ]
    chunks = chunker.chunk_document("doc_test", drafts)
    assert len(chunks) >= 1
    assert chunks[0].page_number == 1
    assert "Microsoft" in chunks[0].text
    print("test_chunking passed!")

def test_extraction():
    extractor = HybridEntityExtractor()
    rel_extractor = RelationshipExtractor()

    text = "Alice developed Project Alpha using Python at Google."
    entities = extractor.extract_entities(text, page_number=1, chunk_id="test_001")
    ent_names = [e.name for e in entities]
    assert "Alice" in ent_names
    assert "Python" in ent_names
    assert "Google" in ent_names

    rels = rel_extractor.extract_relationships(text, entities, "doc_001", "test_001", 1)
    rel_types = [r.relationship for r in rels]
    assert any(r in ["DEVELOPED", "WORKED_ON", "USES", "WORKED_AT"] for r in rel_types)
    print("test_extraction passed!")

def test_entity_resolution():
    normalizer = EntityNormalizer()
    norm_google = normalizer.normalize_name("Google Inc.", "COMPANY")
    assert norm_google == "Google"

    norm_python = normalizer.normalize_name("Python programming language", "TECHNOLOGY")
    assert norm_python == "Python"

    existing = [{"id": "node_google", "name": "Google", "type": "Company", "aliases": ["Google LLC"]}]
    resolved, merged, ex_id = normalizer.resolve_entity("Google LLC", "COMPANY", existing)
    assert merged is True
    assert resolved == "Google"
    assert ex_id == "node_google"
    print("test_entity_resolution passed!")

def test_graph_and_multi_hop():
    ge = GraphEngine()
    ge.add_node(GraphNodeModel(id="n_msft", name="Microsoft", normalized_name="microsoft", type="Company"))
    ge.add_node(GraphNodeModel(id="n_alice", name="Alice", normalized_name="alice", type="Person"))
    ge.add_node(GraphNodeModel(id="n_apollo", name="Apollo", normalized_name="apollo", type="Project"))
    ge.add_node(GraphNodeModel(id="n_python", name="Python", normalized_name="python", type="Technology"))

    ge.add_edge(GraphEdgeModel(id="e1", source="n_alice", target="n_msft", relationship_type="WORKED_AT", source_document="doc1"))
    ge.add_edge(GraphEdgeModel(id="e2", source="n_alice", target="n_apollo", relationship_type="WORKED_ON", source_document="doc2"))
    ge.add_edge(GraphEdgeModel(id="e3", source="n_apollo", target="n_python", relationship_type="USES", source_document="doc3"))

    # Multi-hop find paths from Microsoft to Apollo or Python
    paths = ge.find_paths("n_msft", max_hops=3)
    assert len(paths) > 0
    print("test_graph_and_multi_hop passed!")

def test_knowledge_service_query():
    ks = KnowledgeService()
    assert ks.documents == {}
    assert ks.graph_engine.get_all_nodes() == []
    ans = ks.ask("Which projects are in the knowledge base?")
    assert len(ans.content) > 20
    assert len(ans.citations) == 0
    assert "Groq is not configured" in ans.content
    print("test_knowledge_service_query passed!")

if __name__ == "__main__":
    test_chunking()
    test_extraction()
    test_entity_resolution()
    test_graph_and_multi_hop()
    test_knowledge_service_query()
    print("ALL TESTS PASSED SUCCESSFULLY!")
