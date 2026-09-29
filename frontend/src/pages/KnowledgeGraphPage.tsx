import React, { useState, useEffect } from 'react';
import { GraphNode, GraphEdge } from '../types';
import { fetchGraph, executeCypher } from '../services/api';
import { KnowledgeGraphCanvas } from '../components/KnowledgeGraphCanvas';
import { Network, Terminal, Play, CheckCircle2, AlertCircle, Info } from 'lucide-react';

interface KnowledgeGraphPageProps {
  onSelectEntity: (node: GraphNode) => void;
  selectedNodeId?: string | null;
}

export const KnowledgeGraphPage: React.FC<KnowledgeGraphPageProps> = ({
  onSelectEntity,
  selectedNodeId,
}) => {
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] });
  const [cypherQuery, setCypherQuery] = useState('MATCH (p:Project)-[:USES]->(t:Technology) RETURN p, t');
  const [cypherResults, setCypherResults] = useState<any | null>(null);
  const [cypherError, setCypherError] = useState<string | null>(null);
  const [showCypherConsole, setShowCypherConsole] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchGraph();
        setGraphData(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleRunCypher = async () => {
    setCypherError(null);
    try {
      const res = await executeCypher(cypherQuery);
      setCypherResults(res);
    } catch (err: any) {
      setCypherError(err.message || 'Cypher query execution failed.');
    }
  };

  return (
    <div style={{ padding: '28px', maxWidth: '1600px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Knowledge Graph</h1>
          <p style={{ fontSize: '14.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Interactive property graph topology of cross-document entities and relationships.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setShowCypherConsole(!showCypherConsole)}
            className="btn-secondary"
            style={{ fontSize: '13px', padding: '7px 14px' }}
          >
            <Terminal size={15} /> {showCypherConsole ? 'Hide Cypher Console' : 'Open Cypher Console'}
          </button>
        </div>
      </div>

      {/* Optional Read-Only Cypher Query Console */}
      {showCypherConsole && (
        <div className="jm-card" style={{ padding: '18px', backgroundColor: 'var(--bg-surface-secondary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={16} color="var(--jm-dark-blue)" />
              <span style={{ fontWeight: 700, fontSize: '14px' }}>Read-Only Cypher Query Console</span>
              <span style={{ fontSize: '11.5px', color: '#10B981', fontWeight: 600 }}>● Read-Only Security Guard Active</span>
            </div>
            <button
              onClick={handleRunCypher}
              className="btn-primary"
              style={{ padding: '5px 14px', fontSize: '12.5px' }}
            >
              <Play size={13} /> Run Cypher
            </button>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            {[
              'MATCH (p:Project)-[:USES]->(t:Technology) RETURN p, t',
              'MATCH (person:Person)-[:WORKED_AT]->(c:Company) RETURN person, c',
            'MATCH (n) RETURN n',
            ].map((q, idx) => (
              <button
                key={idx}
                onClick={() => setCypherQuery(q)}
                style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  border: '1px solid var(--jm-border)',
                  background: 'var(--bg-surface)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  color: 'var(--text-secondary)',
                }}
              >
                Sample {idx + 1}
              </button>
            ))}
          </div>

          <textarea
            value={cypherQuery}
            onChange={(e) => setCypherQuery(e.target.value)}
            rows={2}
            style={{
              width: '100%',
              padding: '10px',
              fontFamily: 'monospace',
              fontSize: '13px',
              borderRadius: '8px',
              border: '1px solid var(--jm-border)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              outline: 'none',
            }}
          />

          {cypherError && (
            <div style={{ color: '#EF4444', fontSize: '12.5px', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={15} /> {cypherError}
            </div>
          )}

          {cypherResults && (
            <div style={{ marginTop: '12px', maxHeight: '180px', overflowY: 'auto', backgroundColor: 'var(--bg-surface)', padding: '12px', borderRadius: '8px', border: '1px solid var(--jm-border)' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--jm-dark-blue)', marginBottom: '6px' }}>
                Returned {cypherResults.count} matches:
              </div>
              <pre style={{ fontSize: '11.5px', whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(cypherResults.results, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Main Full-Screen Graph Canvas */}
      <div className="jm-card" style={{ padding: '0', overflow: 'hidden' }}>
        <KnowledgeGraphCanvas
          nodes={graphData.nodes}
          edges={graphData.edges}
          onSelectNode={onSelectEntity}
          selectedNodeId={selectedNodeId}
          height="720px"
        />
      </div>
    </div>
  );
};
