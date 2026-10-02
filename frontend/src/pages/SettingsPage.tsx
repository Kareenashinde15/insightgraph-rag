import React, { useState, useEffect } from 'react';
import { fetchSettings, updateSettings, fetchMetrics } from '../services/api';
import { SystemMetrics } from '../types';
import { Cpu, Activity } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<any>({
    llm_provider: 'groq',
    retrieval_mode: 'vectorless_text',
    temperature: 0.2,
    top_k_retrieval: 5,
    max_graph_hops: 3,
    entity_resolution_threshold: 0.85,
  });
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [s, m] = await Promise.all([fetchSettings(), fetchMetrics()]);
        setSettings(s);
        setMetrics(m);
      } catch (err) {
        console.error(err);
      }
    }
    load();
  }, []);

  const handleSave = async () => {
    try {
      await updateSettings(settings);
      setSaveMessage('Settings updated successfully!');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err: any) {
      setSaveMessage(`Error: ${err.message}`);
    }
  };

  return (
    <div style={{ padding: '32px', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Platform Settings & Observability</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Configure Groq and vectorless text retrieval behavior for this workspace.
        </p>
      </div>

      {/* Observability & System Latency Telemetry */}
      <div className="jm-card" style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Activity size={18} color="var(--jm-dark-blue)" />
          <h2 style={{ fontSize: '17px', fontWeight: 700 }}>System Telemetry & Observability</h2>
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '12px',
        }}>
          <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-secondary)', borderRadius: '8px', border: '1px solid var(--jm-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>LLM Latency</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--jm-dark-blue)' }}>
              {metrics?.latency.llm_latency_ms || 0} ms
            </div>
          </div>
          <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-secondary)', borderRadius: '8px', border: '1px solid var(--jm-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Graph Traversal Latency</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--jm-light-blue)' }}>
              {metrics?.latency.graph_query_latency_ms || 0} ms
            </div>
          </div>
          <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-secondary)', borderRadius: '8px', border: '1px solid var(--jm-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Text Search Latency</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--jm-navy)' }}>
              {metrics?.latency.text_search_latency_ms || 0} ms
            </div>
          </div>
          <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-secondary)', borderRadius: '8px', border: '1px solid var(--jm-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Tokens Consumed</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#10B981' }}>
              {metrics?.token_usage.total_tokens_consumed.toLocaleString() || '0'}
            </div>
          </div>
          <div style={{ padding: '12px', backgroundColor: 'var(--bg-surface-secondary)', borderRadius: '8px', border: '1px solid var(--jm-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Questions Asked</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#10B981' }}>
              {metrics?.query_count || 0}
            </div>
          </div>
        </div>
      </div>

      {/* AI Configuration */}
      <div className="jm-card" style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Cpu size={18} color="var(--jm-dark-blue)" />
          <h2 style={{ fontSize: '17px', fontWeight: 700 }}>AI & LLM Configuration</h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13.5px', fontWeight: 600, marginBottom: '6px' }}>
              LLM Provider
            </label>
            <select
              className="jm-input"
              value={settings.llm_provider}
              onChange={(e) => setSettings({ ...settings, llm_provider: e.target.value })}
              style={{ height: '40px' }}
            >
              <option value="groq">Groq</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13.5px', fontWeight: 600, marginBottom: '6px' }}>
              Retrieval Architecture
            </label>
            <input type="text" className="jm-input" value="Vectorless MongoDB text retrieval" readOnly />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13.5px', fontWeight: 600, marginBottom: '6px' }}>
                Temperature ({settings.temperature})
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.temperature}
                onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13.5px', fontWeight: 600, marginBottom: '6px' }}>
                Top-K Retrieved Sections ({settings.top_k_retrieval})
              </label>
              <input
                type="range"
                min="1"
                max="15"
                step="1"
                value={settings.top_k_retrieval}
                onChange={(e) => setSettings({ ...settings, top_k_retrieval: parseInt(e.target.value, 10) })}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <button onClick={handleSave} className="btn-primary" style={{ padding: '10px 24px' }}>
          Save Configuration
        </button>
      </div>

      {saveMessage && (
        <div style={{ marginTop: '16px', fontSize: '13.5px', fontWeight: 600, color: 'var(--jm-dark-blue)' }}>
          {saveMessage}
        </div>
      )}
    </div>
  );
};
