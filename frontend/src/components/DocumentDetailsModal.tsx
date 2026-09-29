import React, { useState } from 'react';
import { DocumentItem, GraphNode, GraphEdge, DocumentChunk } from '../types';
import { X, CheckCircle2, Clock, FileText, Database, GitBranch, Sparkles } from 'lucide-react';

interface DocumentDetailsModalProps {
  document: DocumentItem | null;
  chunks: DocumentChunk[];
  entities: GraphNode[];
  relationships: GraphEdge[];
  onClose: () => void;
  highlightedChunkId?: string | null;
}

export const DocumentDetailsModal: React.FC<DocumentDetailsModalProps> = ({
  document,
  chunks,
  entities,
  relationships,
  onClose,
  highlightedChunkId,
}) => {
  const [activeTab, setActiveTab] = useState<'text' | 'entities' | 'relationships' | 'pipeline'>('text');

  if (!document) return null;

  const hasKnowledgeGraphData = document.entity_count > 0 || document.relationship_count > 0;
  const pipelineStages = [
    'Upload',
    'Validate File',
    'Store Original',
    'Extract Text',
    'Chunk Document',
    'Generate Embeddings',
    hasKnowledgeGraphData ? 'Extract Knowledge Graph' : 'Optional Knowledge Graph Skipped',
    'Store Provenance & Mark Complete',
  ];

  return (
    <div className="document-modal-backdrop" style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 60,
      padding: '24px',
    }}>
      <div className="document-modal" style={{
        backgroundColor: 'var(--bg-surface)',
        borderRadius: '14px',
        width: '900px',
        maxWidth: '100%',
        height: '85vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 45px rgba(0, 0, 0, 0.2)',
        border: '1px solid var(--jm-border)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div className="document-modal-header" style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--jm-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FileText size={20} color="var(--jm-dark-blue)" />
              <h2 style={{ fontSize: '20px', fontWeight: 700 }}>{document.filename}</h2>
              <span style={{
                padding: '2px 8px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 700,
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                color: '#10B981',
                textTransform: 'uppercase',
              }}>
                {document.status}
              </span>
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Size: {(document.file_size / 1024).toFixed(1)} KB · Format: {document.file_type.toUpperCase()} · Chunks: {chunks.length || document.chunk_count}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '6px' }}
          >
            <X size={20} color="var(--text-muted)" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="document-modal-tabs" style={{
          display: 'flex',
          borderBottom: '1px solid var(--jm-border)',
          padding: '0 24px',
          backgroundColor: 'var(--bg-surface-secondary)',
        }}>
          {[
            { id: 'text', label: 'Extracted Text & Citations' },
            { id: 'entities', label: `Entities (${entities.length || document.entity_count})` },
            { id: 'relationships', label: `Relationships (${relationships.length || document.relationship_count})` },
            { id: 'pipeline', label: 'Processing Pipeline' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: '12px 18px',
                border: 'none',
                background: 'transparent',
                fontWeight: activeTab === tab.id ? 700 : 500,
                fontSize: '13.5px',
                color: activeTab === tab.id ? 'var(--jm-dark-blue)' : 'var(--text-muted)',
                borderBottom: activeTab === tab.id ? '2.5px solid var(--jm-dark-blue)' : '2.5px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.14s ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Modal Content */}
        <div className="document-modal-body" style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {/* Tab 1: Extracted Text */}
          {activeTab === 'text' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {chunks && chunks.length > 0 ? (
                chunks.map((c) => {
                  const isHighlighted = highlightedChunkId === c.id;
                  return (
                    <div
                      key={c.id}
                      style={{
                        padding: '16px',
                        borderRadius: '10px',
                        border: isHighlighted ? '2px solid var(--jm-dark-blue)' : '1px solid var(--jm-border)',
                        backgroundColor: isHighlighted ? 'rgba(74, 95, 217, 0.06)' : 'var(--bg-surface-secondary)',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '8px',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '2px 7px',
                            borderRadius: '4px',
                            backgroundColor: 'var(--jm-dark-blue)',
                            color: '#FFFFFF',
                          }}>
                            Page {c.page_number}
                          </span>
                          <span style={{ fontSize: '13px', fontWeight: 600 }}>{c.section || 'General'}</span>
                        </div>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>ID: {c.id}</span>
                      </div>
                      <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-primary)' }}>
                        {c.text}
                      </p>
                      {c.entities && c.entities.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '10px' }}>
                          {c.entities.map((e, idx) => (
                            <span key={idx} style={{
                              fontSize: '11px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              backgroundColor: 'rgba(46, 58, 140, 0.08)',
                              color: 'var(--jm-dark-blue)',
                              fontWeight: 600,
                            }}>
                              {e}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: '14px' }}>
                  {document.raw_text || 'No raw text available.'}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Extracted Entities */}
          {activeTab === 'entities' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '12px' }}>
              {entities.length === 0 && (
                <div className="graph-empty-state">
                  No entities were extracted. This deployment has optional knowledge-graph extraction disabled; enable <code>ENABLE_KNOWLEDGE_GRAPH=true</code> in Render and reprocess the document.
                </div>
              )}
              {entities.map((ent) => (
                <div key={ent.id} style={{
                  padding: '14px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  border: '1px solid var(--jm-border)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontWeight: 700, fontSize: '14px' }}>{ent.name}</div>
                    <span style={{
                      fontSize: '10.5px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: 'rgba(46, 58, 140, 0.1)',
                      color: 'var(--jm-dark-blue)',
                    }}>
                      {ent.type}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
                    Confidence: {(ent.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tab 3: Extracted Relationships */}
          {activeTab === 'relationships' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {relationships.length === 0 && (
                <div className="graph-empty-state">
                  No relationships were extracted. Enable knowledge-graph extraction in Render and reprocess the document after changing the setting.
                </div>
              )}
              {relationships.map((rel) => (
                <div key={rel.id} style={{
                  padding: '12px 16px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  border: '1px solid var(--jm-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontWeight: 600, fontSize: '13.5px' }}>
                      {rel.source.replace('node_', '').replace(/_/g, ' ')}
                    </span>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--jm-dark-blue)',
                      backgroundColor: 'rgba(46, 58, 140, 0.08)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                    }}>
                      {rel.relationship_type}
                    </span>
                    <span style={{ fontWeight: 600, fontSize: '13.5px' }}>
                      {rel.target.replace('node_', '').replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Confidence: {(rel.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tab 4: 12-Stage Visual Processing Pipeline */}
          {activeTab === 'pipeline' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                Complete local document indexing pipeline status for this document:
              </div>
              {pipelineStages.map((stage, idx) => {
                const isCompleted = document.progress === 100 || idx < 11;
                return (
                  <div key={stage} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '14px',
                    padding: '10px 16px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-surface-secondary)',
                    border: '1px solid var(--jm-border)',
                  }}>
                    <div style={{
                      width: '28px',
                      height: '28px',
                      borderRadius: '50%',
                      backgroundColor: isCompleted ? '#10B981' : 'var(--jm-dark-blue)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#FFFFFF',
                      fontSize: '12px',
                      fontWeight: 700,
                    }}>
                      {isCompleted ? <CheckCircle2 size={16} /> : idx + 1}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '13.5px', fontWeight: 600 }}>{stage}</div>
                    </div>
                    <div style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: isCompleted ? '#10B981' : 'var(--jm-dark-blue)',
                    }}>
                      {isCompleted ? 'Completed' : 'Processing'}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
