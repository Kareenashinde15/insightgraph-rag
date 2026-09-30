import { DocumentItem, GraphNode, GraphEdge, ChatMessage, ProcessingJob, SystemMetrics } from '../types';

// Always use the same-origin /api path so every environment (dev and
// production) routes requests through the configured proxy (Vite in dev,
// Vercel rewrites in production).  This avoids cross-origin requests to
// Render and the CORS errors they cause.
const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
const DIRECT_API_BASE = 'https://insightgraph-rag-api.onrender.com/api';
const API_BASE = configuredApiBase
  ? configuredApiBase.replace(/\/$/, '')
  : '/api';

export async function fetchMetrics(): Promise<SystemMetrics> {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error('Failed to fetch system metrics');
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocumentDetails(id: string): Promise<{
  document: DocumentItem;
  chunks: any[];
  entities: GraphNode[];
  relationships: GraphEdge[];
}> {
  const res = await fetch(`${API_BASE}/documents/${id}`);
  if (!res.ok) throw new Error('Failed to fetch document details');
  return res.json();
}

export async function uploadDocument(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  // Keep uploads same-origin so desktop and mobile browsers follow the same
  // Vercel rewrite path. Fall back only for a network-level proxy failure.
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
  } catch (proxyError) {
    const retryFormData = new FormData();
    retryFormData.append('file', file);
    try {
      res = await fetch(`${DIRECT_API_BASE}/documents/upload`, {
        method: 'POST',
        body: retryFormData,
      });
    } catch {
      throw new Error('Upload connection failed. Please check your internet connection and try again.');
    }
  }
  if (!res.ok) {
    let detail = 'Failed to upload document';
    try {
      const payload = await res.json();
      detail = payload.detail || detail;
    } catch {
      // Keep the fallback message when the server did not return JSON.
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function reprocessDocument(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/documents/${id}/reprocess`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reprocess document');
  return res.json();
}

export async function deleteDocument(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
  return res.json();
}

export async function fetchGraph(): Promise<{
  nodes: GraphNode[];
  edges: GraphEdge[];
  metrics: { node_count: number; edge_count: number };
}> {
  const res = await fetch(`${API_BASE}/graph`);
  if (!res.ok) throw new Error('Failed to fetch knowledge graph');
  return res.json();
}

export async function fetchEntityDetails(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/entities/${id}`);
  if (!res.ok) throw new Error('Failed to fetch entity details');
  return res.json();
}

export async function fetchEntities(type?: string, search?: string): Promise<GraphNode[]> {
  const params = new URLSearchParams();
  if (type) params.append('entity_type', type);
  if (search) params.append('search', search);
  const res = await fetch(`${API_BASE}/entities?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch entities');
  return res.json();
}

export async function executeCypher(query: string): Promise<any> {
  const res = await fetch(`${API_BASE}/graph/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Cypher execution failed');
  }
  return res.json();
}

export async function hybridSearch(query: string): Promise<any> {
  const res = await fetch(`${API_BASE}/search/hybrid`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: 10 }),
  });
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

export async function sendChatMessage(query: string, sessionId: string = 'session_default'): Promise<ChatMessage> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  });
  if (!res.ok) throw new Error('Chat failed');
  return res.json();
}

export async function fetchChatSessions(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/chat/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function fetchProcessingJobs(): Promise<ProcessingJob[]> {
  const res = await fetch(`${API_BASE}/processing/jobs`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}

export async function fetchConflicts(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/conflicts`);
  if (!res.ok) throw new Error('Failed to fetch conflicts');
  return res.json();
}

export async function fetchSettings(): Promise<any> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update settings');
  return res.json();
}

