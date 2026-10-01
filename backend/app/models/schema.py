from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class UserModel(BaseModel):
    id: str = "user_default"
    name: str = "InsightGraph RAG Admin"
    email: str = "admin@insightgraph.local"
    avatar: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class DocumentModel(BaseModel):
    id: str
    user_id: str = "user_default"
    filename: str
    file_type: str
    file_size: int
    storage_path: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    cloudinary_url: Optional[str] = None
    status: str = "completed"  # uploading, processing, extracting_entities, extracting_relationships, building_graph, creating_embeddings, completed, failed
    current_stage: str = "Indexed"
    progress: int = 100
    chunk_count: int = 0
    entity_count: int = 0
    relationship_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    error_message: Optional[str] = None
    raw_text: Optional[str] = ""

class DocumentChunkModel(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    page_number: Optional[int] = 1
    section: Optional[str] = "General"
    paragraph: Optional[str] = ""
    text: str
    token_count: int = 0
    entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class GraphNodeModel(BaseModel):
    id: str
    name: str
    normalized_name: str
    type: str  # Person, Company, Organization, Project, Technology, Product, Location, Event, Skill, Document
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    confidence: float = 0.95
    source_count: int = 1
    document_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class GraphEdgeModel(BaseModel):
    id: str
    source: str  # source node id
    target: str  # target node id
    relationship_type: str  # WORKED_AT, WORKED_ON, USES, CREATED, DEVELOPED, etc.
    confidence: float = 0.92
    source_document: str
    source_chunk: Optional[str] = None
    source_page: Optional[int] = 1
    extraction_method: str = "hybrid_pipeline"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    original_text: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class CitationModel(BaseModel):
    id: str
    citation_index: int
    document_id: str
    document_name: str
    page: Optional[int] = 1
    chunk_id: str
    snippet: str
    similarity_score: Optional[float] = None

class ProcessingJobModel(BaseModel):
    id: str
    document_id: str
    filename: str
    status: str = "processing" # queued, processing, completed, failed
    current_stage: str = "Upload"
    progress: int = 0
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    completion_time: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = 0.0
    stages_log: List[Dict[str, Any]] = Field(default_factory=list)

class ChatMessageModel(BaseModel):
    id: str
    session_id: str
    role: str  # user, assistant
    content: str
    retrieval_type: Optional[str] = "HYBRID"  # SEMANTIC, GRAPH, HYBRID
    citations: List[CitationModel] = Field(default_factory=list)
    graph_evidence_paths: List[List[Dict[str, str]]] = Field(default_factory=list)
    retrieval_trace: Optional[Dict[str, Any]] = Field(default_factory=dict)
    query_plan: Optional[List[str]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class ChatSessionModel(BaseModel):
    id: str
    title: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    messages: List[ChatMessageModel] = Field(default_factory=list)
