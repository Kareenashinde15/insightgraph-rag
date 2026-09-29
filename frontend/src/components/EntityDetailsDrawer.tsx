import React from 'react';
import { GraphNode, GraphEdge, DocumentItem } from '../types';
import { X, ExternalLink, BookOpen, GitFork, Tag, Layers } from 'lucide-react';

interface EntityDetailsDrawerProps {
  entity: GraphNode | null;
  relationships: GraphEdge[];
  documents: DocumentItem[];
  onClose: () => void;
  onSelectRelatedEntity: (entityName: string) => void;
  onOpenDocument: (docId: string) => void;
}

export const EntityDetailsDrawer: React.FC<EntityDetailsDrawerProps> = ({
  entity,
  relationships,
  documents,
  onClose,
  onSelectRelatedEntity,
  onOpenDocument,
}) => {
  if (!entity) return null;

  const connectedRels = relationships.filter(
    (r) => r.source === entity.id || r.target === entity.id
  );

  const getBadgeClass = (type: string) => {
    const t = type.toLowerCase();
    if (t === 'person') return 'badge-person';
    if (t === 'company' || t === 'organization') return 'badge-company';
    if (t === 'project') return 'badge-project';
    if (t.includes('tech') || t.includes('database') || t.includes('framework')) return 'badge-technology';
    if (t === 'location') return 'badge-location';
    return '';
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '380px',
      height: '100vh',
      backgroundColor: 'var(--bg-surface)',
      borderLeft: '1px solid var(--jm-border)',
      boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.12)',
      zIndex: 50,
      display: 'flex',
      flexDirection: 'column',
      animation: 'slideIn 0.2s ease-out',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px',
        borderBottom: '1px solid var(--jm-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitFork size={18} color="var(--jm-dark-blue)" />
          <span style={{ fontWeight: 700, fontSize: '16px' }}>Entity Inspector</span>
        </div>
        <button
          onClick={onClose}
          style={{
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            padding: '4px',
            color: 'var(--text-muted)',
          }}
        >
          <X size={19} />
        </button>
      </div>

      {/* Body Content */}
      <div style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
        {/* Name and Type */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <h2 style={{ fontSize: '22px', fontWeight: 700 }}>{entity.name}</h2>
            <span style={{
              padding: '3px 9px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }} className={getBadgeClass(entity.type)}>
              {entity.type}
            </span>
          </div>

          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Canonical ID: <code>{entity.id}</code>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          marginBottom: '24px',
        }}>
          <div style={{
            padding: '12px',
            backgroundColor: 'var(--bg-surface-secondary)',
            borderRadius: '8px',
            border: '1px solid var(--jm-border)',
          }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Relationships</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--jm-dark-blue)', marginTop: '2px' }}>
              {connectedRels.length}
            </div>
          </div>
          <div style={{
            padding: '12px',
            backgroundColor: 'var(--bg-surface-secondary)',
            borderRadius: '8px',
            border: '1px solid var(--jm-border)',
          }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Documents</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--jm-light-blue)', marginTop: '2px' }}>
              {entity.document_ids?.length || 1}
            </div>
          </div>
        </div>

        {/* Aliases */}
        {entity.aliases && entity.aliases.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>
              Known Aliases & Variations
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {entity.aliases.map((a, i) => (
                <span key={i} style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  border: '1px solid var(--jm-border)',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                }}>
                  {a}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Connected Relationships */}
        <div style={{ marginBottom: '24px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>
            Connected Graph Relationships ({connectedRels.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {connectedRels.map((rel) => {
              const isOutgoing = rel.source === entity.id;
              const targetName = isOutgoing ? rel.target.replace('node_', '').replace(/_/g, ' ') : rel.source.replace('node_', '').replace(/_/g, ' ');
              return (
                <div
                  key={rel.id}
                  onClick={() => onSelectRelatedEntity(targetName)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-surface-secondary)',
                    border: '1px solid var(--jm-border)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    transition: 'all 0.14s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--jm-dark-blue)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--jm-border)')}
                >
                  <div>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--jm-dark-blue)',
                      backgroundColor: 'rgba(46, 58, 140, 0.08)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      marginRight: '6px',
                    }}>
                      {rel.relationship_type}
                    </span>
                    <span style={{ fontSize: '13.5px', fontWeight: 600, textTransform: 'capitalize' }}>
                      {targetName}
                    </span>
                  </div>
                  <ExternalLink size={14} color="#94A3B8" />
                </div>
              );
            })}
          </div>
        </div>

        {/* Supporting Documents */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>
            Supporting Source Documents
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {documents.slice(0, 4).map((doc) => (
              <div
                key={doc.id}
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  border: '1px solid var(--jm-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <BookOpen size={16} color="var(--jm-dark-blue)" />
                  <span style={{ fontSize: '13px', fontWeight: 500 }}>{doc.filename}</span>
                </div>
                <button
                  onClick={() => onOpenDocument(doc.id)}
                  className="btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '12px' }}
                >
                  View Sources
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
