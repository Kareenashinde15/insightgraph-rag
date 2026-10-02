import React, { useState, useEffect } from 'react';
import { ProcessingJob } from '../types';
import { fetchProcessingJobs } from '../services/api';
import { Cpu, CheckCircle2, Clock, RefreshCw, AlertCircle } from 'lucide-react';

export const ProcessingJobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [loading, setLoading] = useState(true);

  const loadJobs = async () => {
    try {
      const data = await fetchProcessingJobs();
      setJobs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Processing Jobs</h1>
          <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Monitor parsing, sectioning, optional graph extraction, and indexing jobs.
          </p>
        </div>
        <button onClick={loadJobs} className="btn-secondary" style={{ fontSize: '13px', padding: '6px 14px' }}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="jm-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-surface-secondary)', borderBottom: '1px solid var(--jm-border)', color: 'var(--text-muted)', fontWeight: 600, fontSize: '12px', textTransform: 'uppercase' }}>
                <th style={{ padding: '14px 20px' }}>Job ID</th>
                <th style={{ padding: '14px 16px' }}>Document</th>
                <th style={{ padding: '14px 16px' }}>Stage</th>
                <th style={{ padding: '14px 16px', width: '220px' }}>Progress</th>
                <th style={{ padding: '14px 16px' }}>Status</th>
                <th style={{ padding: '14px 20px', textAlign: 'right' }}>Duration</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length > 0 ? (
                jobs.map((job) => (
                  <tr key={job.id} style={{ borderBottom: '1px solid var(--jm-border)' }}>
                    <td style={{ padding: '14px 20px', fontFamily: 'monospace', fontSize: '12.5px' }}>
                      {job.id}
                    </td>
                    <td style={{ padding: '14px 16px', fontWeight: 600 }}>
                      {job.filename}
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--jm-dark-blue)', fontWeight: 600 }}>
                      {job.current_stage}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1, height: '8px', backgroundColor: 'var(--jm-border)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${job.progress}%`,
                            height: '100%',
                            backgroundColor: job.status === 'completed' ? '#10B981' : 'var(--jm-dark-blue)',
                            transition: 'width 0.3s ease',
                          }} />
                        </div>
                        <span style={{ fontSize: '12px', fontWeight: 600 }}>{job.progress}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 700,
                        backgroundColor: job.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(74, 95, 217, 0.12)',
                        color: job.status === 'completed' ? '#10B981' : 'var(--jm-light-blue)',
                        textTransform: 'uppercase',
                      }}>
                        {job.status}
                      </span>
                    </td>
                    <td style={{ padding: '14px 20px', textAlign: 'right', color: 'var(--text-muted)' }}>
                      {job.duration_seconds ? `${job.duration_seconds}s` : '< 1s'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No background processing jobs currently queued. All documents are indexed and ready.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
