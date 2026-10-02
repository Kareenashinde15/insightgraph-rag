import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChatMessage, Citation } from '../types';
import { sendChatMessage, fetchChatSessions, fetchConflicts } from '../services/api';
import { 
  Sparkles, 
  Send, 
  Network, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowRight, 
  Layers, 
  FileText,
  ExternalLink 
} from 'lucide-react';

interface AskKnowledgePageProps {
  onOpenDocument: (docId: string, chunkId?: string) => void;
}

export const AskKnowledgePage: React.FC<AskKnowledgePageProps> = ({ onOpenDocument }) => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [conflicts, setConflicts] = useState<any[]>([]);

  const suggestedQuestions = [
    'What documents are available in this workspace?',
    'Summarize the latest uploaded document.',
    'What are the main findings in my uploaded documents?',
  ];

  useEffect(() => {
    async function init() {
      try {
        const [sessions, confs] = await Promise.all([
          fetchChatSessions(),
          fetchConflicts(),
        ]);
        if (sessions && sessions.length > 0 && sessions[0].messages) {
          setMessages(sessions[0].messages);
        }
        setConflicts(confs);
      } catch (err) {
        console.error(err);
      }
    }
    init();
  }, []);

  const handleAsk = async (questionText?: string) => {
    const q = questionText || query;
    if (!q.trim()) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      session_id: 'session_default',
      role: 'user',
      content: q,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const assistantMsg = await sendChatMessage(q);
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        session_id: 'session_default',
        role: 'assistant',
        content: `Error retrieving grounded knowledge: ${err.message}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const renderAnswerMarkdown = (content: string, citations?: Citation[]) => {
    const availableCitations = citations || [];
    const markdown = content.replace(/\[(\d+)\]/g, (fullMatch, rawIndex: string) => {
      const citationIndex = Number(rawIndex);
      return availableCitations.some((citation) => citation.citation_index === citationIndex)
        ? `[${rawIndex}](citation://${citationIndex})`
        : fullMatch;
    });

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith('citation://')) {
              const citationIndex = Number(href.replace('citation://', ''));
              const citation = availableCitations.find((item) => item.citation_index === citationIndex);
              if (citation) {
                return (
                  <button
                    type="button"
                    className="answer-citation"
                    onClick={() => onOpenDocument(citation.document_id, citation.chunk_id)}
                    title={`View source: ${citation.document_name} (Page ${citation.page})`}
                  >
                    {children}
                  </button>
                );
              }
            }
            return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
          },
          table: ({ children }) => (
            <div className="answer-table-scroll">
              <table className="answer-table">{children}</table>
            </div>
          ),
          p: ({ children }) => <p className="answer-paragraph">{children}</p>,
          ul: ({ children }) => <ul className="answer-list">{children}</ul>,
          ol: ({ children }) => <ol className="answer-list">{children}</ol>,
          blockquote: ({ children }) => <blockquote className="answer-quote">{children}</blockquote>,
          code: ({ children }) => <code className="answer-inline-code">{children}</code>,
        }}
      >
        {markdown}
      </ReactMarkdown>
    );
  };

  // Keep the newest question/answer pair at the top so the user immediately
  // sees the latest result and its sources without scrolling through history.
  const latestAssistantIndex = [...messages]
    .map((message, index) => ({ message, index }))
    .reverse()
    .find(({ message }) => message.role === 'assistant')?.index;
  const latestAssistant = latestAssistantIndex !== undefined ? messages[latestAssistantIndex] : undefined;
  const latestUser = latestAssistantIndex !== undefined
    ? [...messages.slice(0, latestAssistantIndex)].reverse().find((message) => message.role === 'user')
    : [...messages].reverse().find((message) => message.role === 'user');
  // Keep each question attached to its answer, then show complete exchanges
  // from newest at the top to oldest at the bottom.
  const messageGroups: ChatMessage[][] = [];
  let currentGroup: ChatMessage[] = [];
  messages.forEach((message) => {
    if (message.role === 'user' && currentGroup.length > 0) {
      messageGroups.push(currentGroup);
      currentGroup = [];
    }
    currentGroup.push(message);
  });
  if (currentGroup.length > 0) messageGroups.push(currentGroup);
  const orderedMessages = messageGroups.reverse().flat();

  return (
    <div style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Title */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Ask Knowledge</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Ask questions across your uploaded documents and see grounded answers with their sources first.
        </p>
      </div>

      {/* Conflicting Information Warning Banner if detected */}
      {conflicts && conflicts.length > 0 && (
        <div style={{
          padding: '14px 18px',
          borderRadius: '10px',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}>
          <AlertTriangle size={20} color="#D97706" />
          <div style={{ flex: 1, fontSize: '13px', color: '#92400E' }}>
            <strong>Potential conflicting information detected:</strong> Divergent dates reported across documents for {conflicts[0].entity_name} tenure. Both claims are preserved with source provenance.
          </div>
        </div>
      )}

      {/* Suggested Questions Grid */}
      <div style={{ marginBottom: '28px' }}>
        <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>
          Suggested Multi-Hop Questions
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '8px' }}>
          {suggestedQuestions.map((sq, idx) => (
            <button
              key={idx}
              onClick={() => handleAsk(sq)}
              style={{
                padding: '10px 14px',
                textAlign: 'left',
                borderRadius: '8px',
                border: '1px solid var(--jm-border)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-secondary)',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--jm-dark-blue)';
                e.currentTarget.style.color = 'var(--jm-dark-blue)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--jm-border)';
                e.currentTarget.style.color = 'var(--text-secondary)';
              }}
            >
              <span>{sq}</span>
              <ArrowRight size={14} />
            </button>
          ))}
        </div>
      </div>

      {/* Query Input Box */}
      <div className="jm-card ask-query-card" style={{ padding: '16px', marginBottom: '32px' }}>
        <div className="ask-query-form" style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            id="knowledge-query"
            name="query"
            className="jm-input"
            placeholder="Ask a question about your uploaded documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            style={{ height: '48px', fontSize: '15px' }}
          />
          <button
            onClick={() => handleAsk()}
            className="btn-primary"
            disabled={loading || !query.trim()}
            style={{ padding: '0 24px', height: '48px', flexShrink: 0 }}
          >
            <Sparkles size={16} /> Ask Knowledge
          </button>
        </div>
      </div>

      {/* Messages / AI Answer Presentation */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
        {orderedMessages.map((msg) => {
          const isLatestAssistant = latestAssistant?.id === msg.id;
          if (msg.role === 'user') {
            return (
              <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                <div style={{
                  maxWidth: '75%',
                  backgroundColor: 'var(--jm-dark-blue)',
                  color: '#FFFFFF',
                  padding: '14px 20px',
                  borderRadius: '14px 14px 2px 14px',
                  fontSize: '15px',
                  fontWeight: 500,
                  boxShadow: '0 2px 8px rgba(46, 58, 140, 0.25)',
                }}>
                  {msg.content}
                </div>
              </div>
            );
          }

          // Assistant Research Answer Card
          return (
            <div key={msg.id} className="jm-card" style={{ padding: '24px', borderColor: isLatestAssistant ? 'var(--jm-light-blue)' : 'var(--jm-border)', boxShadow: isLatestAssistant ? '0 4px 16px rgba(74, 95, 217, 0.14)' : undefined }}>
              {/* Header Badges: Retrieval mode & Trust Indicators */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '10px',
                borderBottom: '1px solid var(--jm-border)',
                paddingBottom: '14px',
                marginBottom: '16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(74, 95, 217, 0.12)',
                    color: 'var(--jm-light-blue)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}>
                    {msg.retrieval_type || 'HYBRID'} RETRIEVAL
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    InsightGraph RAG Engine
                  </span>
                </div>

                {/* AI Trust Indicators - per Brand Guidelines */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', fontWeight: 600, color: '#10B981' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle2 size={14} /> {msg.citations?.length || 0} sources used
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle2 size={14} /> Grounded in retrieved evidence
                  </span>
                </div>
              </div>

              {/* Main Grounded Answer Text with Clickable Citations */}
              <div style={{
                fontSize: '15px',
                lineHeight: 1.7,
                color: 'var(--text-primary)',
                marginBottom: '20px',
              }} className="answer-markdown">
                {renderAnswerMarkdown(msg.content, msg.citations)}
              </div>

              {/* Visual Graph Evidence Path */}
              {msg.graph_evidence_paths && msg.graph_evidence_paths.length > 0 && (
                <div style={{
                  padding: '14px 16px',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  borderRadius: '10px',
                  border: '1px solid var(--jm-border)',
                  marginBottom: '18px',
                }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--jm-dark-blue)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Network size={14} /> Verified Graph Evidence Path
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    {msg.graph_evidence_paths[0].map((step, sIdx) => (
                      <React.Fragment key={sIdx}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor: 'var(--jm-navy)',
                          color: '#FFFFFF',
                          fontSize: '12.5px',
                          fontWeight: 600,
                        }}>
                          {step.source}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                          --[{step.relationship}]--&gt;
                        </span>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor: 'var(--jm-dark-blue)',
                          color: '#FFFFFF',
                          fontSize: '12.5px',
                          fontWeight: 600,
                        }}>
                          {step.target}
                        </span>
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              )}

              {/* Structured Query Planning Trace */}
              {msg.query_plan && msg.query_plan.length > 0 && (
                <div style={{
                  padding: '12px 16px',
                  backgroundColor: 'var(--bg-surface-secondary)',
                  borderRadius: '10px',
                  border: '1px solid var(--jm-border)',
                  marginBottom: '18px',
                }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Layers size={14} /> Multi-Hop Query Execution Trace
                  </div>
                  <ol style={{ paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                    {msg.query_plan.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Source Document Citations Cards */}
              {msg.citations && msg.citations.length > 0 && (
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>
                    Supporting source evidence ({msg.citations.length})
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: '10px' }}>
                    {msg.citations.map((c) => (
                      <div
                        key={c.id}
                        onClick={() => onOpenDocument(c.document_id, c.chunk_id)}
                        style={{
                          padding: '12px 14px',
                          borderRadius: '8px',
                          border: '1px solid var(--jm-border)',
                          backgroundColor: 'var(--bg-surface)',
                          cursor: 'pointer',
                          transition: 'border-color 0.16s ease',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--jm-dark-blue)')}
                        onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--jm-border)')}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px', marginBottom: '6px', minWidth: 0 }}>
                          <span title={c.document_name} style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '12.5px', fontWeight: 700, color: 'var(--jm-dark-blue)' }}>
                            [{c.citation_index}] {c.document_name}
                          </span>
                          <span style={{ flexShrink: 0, whiteSpace: 'nowrap', fontSize: '11px', color: 'var(--text-muted)' }}>Page {c.page}</span>
                        </div>
                        <p style={{ margin: 0, overflowWrap: 'anywhere', wordBreak: 'break-word', fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                          "{c.snippet}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="jm-card" style={{ padding: '24px', textAlign: 'center' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', fontSize: '14px', color: 'var(--jm-dark-blue)', fontWeight: 600 }}>
              <Sparkles size={18} className="pulse-glow" />
              <span>Searching your documents and preparing a grounded answer...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
