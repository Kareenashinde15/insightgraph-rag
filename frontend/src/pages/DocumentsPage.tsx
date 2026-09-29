import React, { useState, useEffect, useRef } from 'react';
import { DocumentItem } from '../types';
import { fetchDocuments, uploadDocument, deleteDocument, reprocessDocument } from '../services/api';
import { 
  UploadCloud, 
  FileText, 
  Trash2, 
  RefreshCw, 
  Eye, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  FileCheck 
} from 'lucide-react';

interface DocumentsPageProps {
  onOpenDocument: (docId: string) => void;
}

export const DocumentsPage: React.FC<DocumentsPageProps> = ({ onOpenDocument }) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const loadDocuments = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadDocuments();
    const interval = setInterval(loadDocuments, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setIsUploading(true);
    setUploadMessage(`Uploading and processing ${file.name}...`);
    try {
      await uploadDocument(file);
      setUploadMessage(`Successfully initiated processing pipeline for ${file.name}!`);
      loadDocuments();
      setTimeout(() => setUploadMessage(null), 4000);
    } catch (err: any) {
      setUploadMessage(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (!e.dataTransfer.files || e.dataTransfer.files.length === 0) return;
    const file = e.dataTransfer.files[0];
    setIsUploading(true);
    setUploadMessage(`Uploading and processing ${file.name}...`);
    try {
      await uploadDocument(file);
      setUploadMessage(`Successfully initiated pipeline for ${file.name}!`);
      loadDocuments();
      setTimeout(() => setUploadMessage(null), 4000);
    } catch (err: any) {
      setUploadMessage(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (confirm('Are you sure you want to remove this document and its associated vectors and entities?')) {
      await deleteDocument(docId);
      loadDocuments();
    }
  };

  const handleReprocess = async (docId: string) => {
    await reprocessDocument(docId);
    loadDocuments();
  };

  return (
    <div className="page-container documents-page" style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Title */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Documents</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Upload, manage, and inspect unstructured files processed into knowledge graph structures and vector embeddings.
        </p>
      </div>

      {/* Upload Drag & Drop Box */}
      <div
        className="doc-upload-card"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        style={{
          border: '2px dashed var(--jm-dark-blue)',
          borderRadius: '12px',
          padding: '40px 24px',
          textAlign: 'center',
          backgroundColor: 'var(--bg-surface)',
          marginBottom: '32px',
          boxShadow: 'var(--card-shadow)',
          cursor: 'pointer',
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: 'rgba(46, 58, 140, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px',
        }}>
          <UploadCloud size={28} color="var(--jm-dark-blue)" />
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '6px' }}>Upload Knowledge</h2>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          Add documents to build your personal knowledge graph.
        </p>
        <div style={{
          display: 'inline-flex',
          gap: '8px',
          padding: '4px 12px',
          borderRadius: '20px',
          backgroundColor: 'var(--bg-surface-secondary)',
          fontSize: '12px',
          fontWeight: 600,
          color: 'var(--text-muted)',
          marginBottom: '18px',
        }}>
          PDF · DOCX · TXT · MD · HTML · CSV
        </div>
        <div>
          <label
            className="btn-primary upload-file-label"
            aria-disabled={isUploading}
            onClick={(e) => {
              if (isUploading) e.preventDefault();
              e.stopPropagation();
            }}
          >
            {isUploading ? 'Processing File...' : 'Upload Documents'}
            <input
              ref={fileInputRef}
              className="file-picker-input"
              type="file"
              accept=".pdf,.docx,.txt,.md,.html,.csv"
              onChange={handleFileSelect}
              aria-label="Choose a knowledge document"
              disabled={isUploading}
            />
          </label>
        </div>
        {uploadMessage && (
          <div style={{ marginTop: '14px', fontSize: '13px', fontWeight: 600, color: 'var(--jm-dark-blue)' }}>
            {uploadMessage}
          </div>
        )}
      </div>

      {/* Document Table */}
      <div className="jm-card document-table-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--jm-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <h2 style={{ fontSize: '17px', fontWeight: 700 }}>
            Knowledge Documents ({documents.length})
          </h2>
          <button onClick={loadDocuments} className="btn-secondary" style={{ padding: '4px 10px', fontSize: '12px' }}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {documents.some((doc) => doc.status === 'completed' && doc.entity_count === 0 && doc.relationship_count === 0) && (
          <div className="document-graph-notice" role="status">
            Entity and relationship extraction is disabled on this API deployment. Set <code>ENABLE_KNOWLEDGE_GRAPH=true</code> in Render, then reprocess this document.
          </div>
        )}

        <div className="responsive-table-wrap" style={{ overflowX: 'auto' }}>
          <table className="responsive-data-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-surface-secondary)', borderBottom: '1px solid var(--jm-border)', color: 'var(--text-muted)', fontWeight: 600, fontSize: '12px', textTransform: 'uppercase' }}>
                <th style={{ padding: '14px 20px' }}>Document</th>
                <th style={{ padding: '14px 16px' }}>Format</th>
                <th style={{ padding: '14px 16px' }}>Status</th>
                <th style={{ padding: '14px 16px' }}>Chunks</th>
                <th style={{ padding: '14px 16px' }}>Entities</th>
                <th style={{ padding: '14px 16px' }}>Relationships</th>
                <th style={{ padding: '14px 20px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  style={{ borderBottom: '1px solid var(--jm-border)', transition: 'background-color 0.14s ease' }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-surface-secondary)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td data-label="Document" style={{ padding: '14px 20px', fontWeight: 600 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <FileText size={17} color="var(--jm-dark-blue)" />
                      <span>{doc.filename}</span>
                    </div>
                  </td>
                  <td data-label="Format" style={{ padding: '14px 16px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, fontSize: '12px' }}>
                    {doc.file_type}
                  </td>
                  <td data-label="Status" style={{ padding: '14px 16px' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '11.5px',
                      fontWeight: 700,
                      backgroundColor: doc.status === 'completed' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(74, 95, 217, 0.12)',
                      color: doc.status === 'completed' ? '#10B981' : 'var(--jm-light-blue)',
                    }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: doc.status === 'completed' ? '#10B981' : 'var(--jm-light-blue)' }} />
                      {doc.status}
                    </span>
                  </td>
                  <td data-label="Chunks" style={{ padding: '14px 16px' }}>{doc.chunk_count}</td>
                  <td data-label="Entities" style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--jm-dark-blue)' }}>{doc.entity_count}</td>
                  <td data-label="Relationships" style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--jm-light-blue)' }}>{doc.relationship_count}</td>
                  <td data-label="Actions" style={{ padding: '14px 20px', textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '8px' }}>
                      <button
                        onClick={() => onOpenDocument(doc.id)}
                        className="btn-secondary"
                        style={{ padding: '5px 10px', fontSize: '12px' }}
                      >
                        <Eye size={13} /> View
                      </button>
                      <button
                        onClick={() => handleReprocess(doc.id)}
                        title="Reprocess"
                        style={{ border: '1px solid var(--jm-border)', background: 'transparent', borderRadius: '6px', padding: '5px 8px', cursor: 'pointer' }}
                      >
                        <RefreshCw size={13} color="var(--text-muted)" />
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        title="Delete"
                        style={{ border: '1px solid var(--jm-border)', background: 'transparent', borderRadius: '6px', padding: '5px 8px', cursor: 'pointer' }}
                      >
                        <Trash2 size={13} color="#EF4444" />
                      </button>
                    </div>
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
