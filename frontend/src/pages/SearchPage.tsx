import React, { useState } from 'react';
import { hybridSearch } from '../services/api';
import { Search, FileText, CircleUser, GitBranch, ArrowRight } from 'lucide-react';

interface SearchPageProps {
  onOpenDocument: (docId: string) => void;
  onSelectEntity?: (node: any) => void;
}

export const SearchPage: React.FC<SearchPageProps> = ({ onOpenDocument, onSelectEntity }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await hybridSearch(query);
      setResults(data);
    } catch (err) {
      console.error(err);
      setResults(null);
      setError(err instanceof Error ? err.message : 'Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Unified Knowledge Search</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Search your uploaded documents with lexical retrieval and grounded reasoning.
        </p>
      </div>

      {/* Main Search Input */}
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px', marginBottom: '32px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={18} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            className="jm-input"
            placeholder="Search your uploaded documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ paddingLeft: '42px', height: '46px', fontSize: '15px' }}
          />
        </div>
        <button type="submit" className="btn-primary" style={{ padding: '0 24px', height: '46px' }} disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && (
        <div className="jm-card" style={{ padding: '14px 16px', marginBottom: '24px', color: '#9b1c1c', borderColor: '#f1b5b5', background: '#fff7f7' }}>
          {error}
        </div>
      )}

      {/* Results Sections */}
      {results && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Vectorless text matches */}
          {results.sections && results.sections.length > 0 && (
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} color="var(--jm-dark-blue)" /> Relevant document sections ({results.sections.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {results.sections.map((chunk: any) => (
                  <div
                    key={chunk.chunk_id}
                    className="jm-card"
                    onClick={() => onOpenDocument(chunk.document_id)}
                    style={{ padding: '14px 16px', cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 700, fontSize: '13px' }}>{chunk.source || 'Uploaded document'}</span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        Page {chunk.page ?? '—'} · {(Number(chunk.similarity || 0) * 100).toFixed(1)}% text relevance
                      </span>
                    </div>
                    <div style={{ fontSize: '14px', lineHeight: 1.55, color: 'var(--text-secondary)' }}>
                      {chunk.text?.length > 420 ? `${chunk.text.slice(0, 420)}…` : chunk.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Matched Entities */}
          {results.entities && results.entities.length > 0 && (
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CircleUser size={18} color="var(--jm-dark-blue)" /> Entities ({results.entities.length})
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '12px' }}>
                {results.entities.map((ent: any) => (
                  <div
                    key={ent.id}
                    onClick={() => onSelectEntity?.(ent)}
                    className="jm-card"
                    style={{ padding: '14px', cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700, fontSize: '14.5px' }}>{ent.name}</span>
                      <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--jm-dark-blue)' }}>
                        {ent.type}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Matched Documents */}
          {results.documents && results.documents.length > 0 && (
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} color="var(--jm-light-blue)" /> Documents ({results.documents.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {results.documents.map((doc: any) => (
                  <div
                    key={doc.id}
                    onClick={() => onOpenDocument(doc.id)}
                    className="jm-card"
                    style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <FileText size={18} color="var(--jm-dark-blue)" />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '14px' }}>{doc.filename}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          {doc.entity_count} entities · {doc.relationship_count} relationships
                        </div>
                      </div>
                    </div>
                    <ArrowRight size={16} color="var(--text-muted)" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Matched Relationships */}
          {results.relationships && results.relationships.length > 0 && (
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GitBranch size={18} color="var(--jm-navy)" /> Relationships ({results.relationships.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {results.relationships.map((rel: any) => (
                  <div
                    key={rel.id}
                    className="jm-card"
                    style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontWeight: 600 }}>{rel.source.replace('node_', '').replace(/_/g, ' ')}</span>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: 'rgba(46, 58, 140, 0.08)',
                        color: 'var(--jm-dark-blue)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                      }}>
                        {rel.relationship_type}
                      </span>
                      <span style={{ fontWeight: 600 }}>{rel.target.replace('node_', '').replace(/_/g, ' ')}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Doc: {rel.source_document}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!results.sections?.length && !results.entities?.length && !results.documents?.length && !results.relationships?.length) && (
            <div className="jm-card" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              No matching passages, documents, entities, or relationships were found.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
