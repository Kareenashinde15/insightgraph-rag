import React, { useState, useEffect } from 'react';
import { GraphNode } from '../types';
import { fetchEntities } from '../services/api';
import { Search, CircleUser, ExternalLink, Filter } from 'lucide-react';

interface EntitiesPageProps {
  onSelectEntity: (node: GraphNode) => void;
}

export const EntitiesPage: React.FC<EntitiesPageProps> = ({ onSelectEntity }) => {
  const [entities, setEntities] = useState<GraphNode[]>([]);
  const [selectedType, setSelectedType] = useState('ALL');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const filterTabs = ['ALL', 'Person', 'Company', 'Project', 'Technology', 'Location'];

  const loadEntities = async () => {
    try {
      const typeParam = selectedType === 'ALL' ? undefined : selectedType;
      const data = await fetchEntities(typeParam, search);
      setEntities(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEntities();
  }, [selectedType, search]);

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
    <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Entities</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Explore and query the canonical entities discovered across all indexed documents.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        marginBottom: '24px',
      }}>
        {/* Type Filter Buttons */}
        <div style={{ display: 'flex', gap: '6px' }}>
          {filterTabs.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              style={{
                padding: '7px 14px',
                borderRadius: '8px',
                border: selectedType === t ? '1px solid var(--jm-dark-blue)' : '1px solid var(--jm-border)',
                backgroundColor: selectedType === t ? 'var(--jm-dark-blue)' : 'var(--bg-surface)',
                color: selectedType === t ? '#FFFFFF' : 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div style={{ position: 'relative', width: '320px' }}>
          <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            className="jm-input"
            placeholder="Search entities or aliases..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '36px', height: '38px', fontSize: '13px' }}
          />
        </div>
      </div>

      {/* Entity Table */}
      <div className="jm-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-surface-secondary)', borderBottom: '1px solid var(--jm-border)', color: 'var(--text-muted)', fontWeight: 600, fontSize: '12px', textTransform: 'uppercase' }}>
                <th style={{ padding: '14px 20px' }}>Entity</th>
                <th style={{ padding: '14px 16px' }}>Type</th>
                <th style={{ padding: '14px 16px' }}>Relationships</th>
                <th style={{ padding: '14px 16px' }}>Sources</th>
                <th style={{ padding: '14px 16px' }}>Aliases</th>
                <th style={{ padding: '14px 20px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((node) => (
                <tr
                  key={node.id}
                  style={{ borderBottom: '1px solid var(--jm-border)', cursor: 'pointer', transition: 'background-color 0.14s ease' }}
                  onClick={() => onSelectEntity(node)}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-surface-secondary)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '14px 20px', fontWeight: 700, color: 'var(--text-primary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <CircleUser size={16} color="var(--jm-dark-blue)" />
                      <span>{node.name}</span>
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span style={{
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                    }} className={getBadgeClass(node.type)}>
                      {node.type}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--jm-dark-blue)' }}>
                    {node.source_count || 1}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    {node.document_ids?.length || 1} documents
                  </td>
                  <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '12px' }}>
                    {node.aliases && node.aliases.length > 0 ? node.aliases.join(', ') : 'None'}
                  </td>
                  <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                    <button
                      className="btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectEntity(node);
                      }}
                    >
                      Inspect <ExternalLink size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
