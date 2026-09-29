import React, { useEffect, useState } from 'react';
import { SystemMetrics, DocumentItem, ChatMessage } from '../types';
import { fetchMetrics, fetchDocuments, fetchChatSessions } from '../services/api';
import { 
  FileText, 
  Database, 
  Sparkles,
} from 'lucide-react';

interface DashboardPageProps {
  onNavigateTab: (tab: string) => void;
  onOpenDocument: (docId: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigateTab,
  onOpenDocument,
}) => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [recentQuestions, setRecentQuestions] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [m, docs, sessions] = await Promise.all([
          fetchMetrics(),
          fetchDocuments(),
          fetchChatSessions(),
        ]);
        setMetrics(m);
        setDocuments(docs);

        const questions = sessions
          .flatMap((session: any) => session.messages || [])
          .filter((message: ChatMessage) => message.role === 'user')
          .sort((a: ChatMessage, b: ChatMessage) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )
          .slice(0, 5);
        setRecentQuestions(questions);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Heading - Strictly adhering to Brand Guidelines */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '30px', fontWeight: 700, color: 'var(--text-primary)' }}>Knowledge Overview</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Upload documents, search their contents, and ask grounded questions.
        </p>
      </div>

      {/* 4 Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '20px',
        marginBottom: '32px',
      }}>
        {/* Card 1: Documents */}
        <div className="jm-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-secondary)' }}>Documents</span>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: 'rgba(46, 58, 140, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <FileText size={18} color="var(--jm-dark-blue)" />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {metrics ? metrics.documents.total : 0}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {metrics ? metrics.documents.processed : 0} processed · {metrics ? metrics.documents.processing : 0} processing
            </div>
          </div>
        </div>

        {/* Card 2: Questions */}
        <div className="jm-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-secondary)' }}>Questions Asked</span>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: 'rgba(74, 95, 217, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Sparkles size={18} color="var(--jm-light-blue)" />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {metrics?.query_count || 0}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Grounded retrieval requests
            </div>
          </div>
        </div>

        {/* Card 3: Embeddings */}
        <div className="jm-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-secondary)' }}>Embeddings</span>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: 'rgba(26, 34, 84, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Database size={18} color="var(--jm-navy)" />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {metrics ? metrics.knowledge_sources.total_embeddings : 0}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Local semantic index
            </div>
          </div>
        </div>

        {/* Card 4: Knowledge Sources */}
        <div className="jm-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-secondary)' }}>Knowledge Sources</span>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: 'rgba(67, 85, 185, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Database size={18} color="var(--jm-light-blue)" />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {metrics ? metrics.knowledge_sources.total_chunks : 0} chunks
            </div>
            <div style={{ fontSize: '13px', color: '#10B981', fontWeight: 600, marginTop: '4px' }}>
              ● Vector index active
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Recent Documents & Recent Questions */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))',
        gap: '24px',
      }}>
        {/* Recent Documents Table */}
        <div className="jm-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '17px', fontWeight: 700 }}>Recent Documents</h2>
            <button
              onClick={() => onNavigateTab('documents')}
              style={{ border: 'none', background: 'transparent', color: 'var(--jm-dark-blue)', fontWeight: 600, fontSize: '13px', cursor: 'pointer' }}
            >
              View All ({documents.length})
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {documents.slice(0, 5).map((doc) => (
              <div
                key={doc.id}
                onClick={() => onOpenDocument(doc.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  border: '1px solid var(--jm-border)',
                  cursor: 'pointer',
                  transition: 'border-color 0.16s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--jm-dark-blue)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--jm-border)')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileText size={16} color="var(--jm-dark-blue)" />
                  <div>
                    <div style={{ fontSize: '13.5px', fontWeight: 600 }}>{doc.filename}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {doc.chunk_count} indexed chunks · {doc.file_type.toUpperCase()}
                    </div>
                  </div>
                </div>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#10B981',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  padding: '3px 8px',
                  borderRadius: '4px',
                }}>
                  Completed
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Questions Card */}
        <div className="jm-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '17px', fontWeight: 700 }}>Recent Questions</h2>
            <button
              onClick={() => onNavigateTab('ask')}
              className="btn-primary"
              style={{ padding: '6px 14px', fontSize: '13px' }}
            >
              <Sparkles size={14} /> Ask Knowledge
            </button>
          </div>

          {recentQuestions.length === 0 ? (
            <div style={{ padding: '24px 14px', color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center' }}>
              No questions have been asked in this workspace yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {recentQuestions.map((question) => (
                <button
                  key={question.id}
                  onClick={() => onNavigateTab('ask')}
                  style={{
                    width: '100%',
                    padding: '11px 14px',
                    borderRadius: '8px',
                    border: '1px solid var(--jm-border)',
                    backgroundColor: 'var(--bg-surface-secondary)',
                    color: 'var(--text-primary)',
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontSize: '13.5px', fontWeight: 600, lineHeight: 1.4 }}>
                    {question.content.length > 105 ? `${question.content.slice(0, 105)}…` : question.content}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
