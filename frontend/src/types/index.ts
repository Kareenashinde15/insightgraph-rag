export interface DocumentItem {
  id: string;
  user_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  storage_path?: string;
  status: string;
  current_stage: string;
  progress: number;
  chunk_count: number;
  entity_count: number;
  relationship_count: number;
  created_at: string;
  updated_at: string;
  raw_text?: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  page_number: number;
  section: string;
  paragraph: string;
  text: string;
  token_count: number;
  entities: string[];
}

export interface GraphNode {
  id: string;
  name: string;
  normalized_name: string;
  type: string;
  description?: string;
  aliases: string[];
  confidence: number;
  source_count: number;
  document_ids: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  confidence: number;
  source_document: string;
  source_chunk?: string;
  source_page?: number;
  extraction_method: string;
  start_date?: string;
  end_date?: string;
  original_text?: string;
}

export interface Citation {
  id: string;
  citation_index: number;
  document_id: string;
  document_name: string;
  page: number;
  chunk_id: string;
  snippet: string;
  similarity_score?: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  retrieval_type?: 'TEXT' | 'SEMANTIC' | 'GRAPH' | 'HYBRID';
  citations?: Citation[];
  graph_evidence_paths?: Array<Array<{
    source: string;
    relationship: string;
    target: string;
  }>>;
  retrieval_trace?: {
    query_type?: string;
    classification_confidence?: number;
    entities_identified?: string[];
    graph_facts_count?: number;
    graph_paths_count?: number;
    text_sections_retrieved?: number;
    evidence_used_count?: number;
    graph_query_latency_ms?: number;
    text_search_latency_ms?: number;
    llm_latency_ms?: number;
    total_query_latency_ms?: number;
    citation_validation?: {
      valid: boolean;
      input_count: number;
      accepted_count: number;
      rejected_count: number;
      invalid_markers: number[];
      issues: string[];
    };
  };
  query_plan?: string[];
  created_at: string;
}

export interface ProcessingJob {
  id: string;
  document_id: string;
  filename: string;
  status: string;
  current_stage: string;
  progress: number;
  start_time: string;
  completion_time?: string;
  duration_seconds: number;
  stages_log: Array<{
    stage: string;
    progress: number;
    timestamp: number;
    details: string;
  }>;
}

export interface SystemMetrics {
  documents: {
    total: number;
    processed: number;
    processing: number;
  };
  entities: {
    total: number;
    people: number;
    companies: number;
    projects: number;
    technologies: number;
  };
  relationships: {
    total: number;
    recent: number;
  };
  knowledge_sources: {
    total_chunks: number;
    total_indexed_sources: number;
  };
  system_status: string;
  retrieval_mode?: string;
  latency: {
    llm_latency_ms: number;
    graph_query_latency_ms: number;
    text_search_latency_ms?: number;
    total_query_latency_ms: number;
  };
  token_usage: {
    total_tokens_consumed: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
  };
  query_count?: number;
  processing_count?: number;
  failed_jobs?: number;
  last_query_at?: string | null;
  last_processing_at?: string | null;
  llm_provider?: string;
}
