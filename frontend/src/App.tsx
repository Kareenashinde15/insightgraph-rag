import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DocumentDetailsModal } from './components/DocumentDetailsModal';

import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { SearchPage } from './pages/SearchPage';
import { AskKnowledgePage } from './pages/AskKnowledgePage';
import { ProcessingJobsPage } from './pages/ProcessingJobsPage';
import { SettingsPage } from './pages/SettingsPage';

import { DocumentItem, DocumentChunk, GraphNode, GraphEdge } from './types';
import { fetchDocumentDetails } from './services/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Selected Document state for modal
  const [selectedDocument, setSelectedDocument] = useState<DocumentItem | null>(null);
  const [documentChunks, setDocumentChunks] = useState<DocumentChunk[]>([]);
  const [documentEntities, setDocumentEntities] = useState<GraphNode[]>([]);
  const [documentRels, setDocumentRels] = useState<GraphEdge[]>([]);
  const [highlightedChunkId, setHighlightedChunkId] = useState<string | null>(null);

  // Toggle Theme
  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  };

  const handleOpenDocument = async (docId: string, chunkId?: string) => {
    try {
      const details = await fetchDocumentDetails(docId);
      setSelectedDocument(details.document);
      setDocumentChunks(details.chunks || []);
      setDocumentEntities(details.entities || []);
      setDocumentRels(details.relationships || []);
      setHighlightedChunkId(chunkId || null);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="app-shell" style={{ display: 'flex', width: '100vw', minHeight: '100vh', backgroundColor: 'var(--bg-app)' }}>
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
          setIsSidebarOpen(false);
        }}
      />

      {/* Main Content Area */}
      <div className="app-main-shell" style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflowX: 'hidden' }}>
        <Header
          theme={theme}
          onToggleTheme={toggleTheme}
          onOpenSettings={() => setCurrentTab('settings')}
          onMenuClick={() => setIsSidebarOpen(true)}
        />

        <main className="app-main" style={{ flex: 1, overflowY: 'auto' }}>
          {currentTab === 'dashboard' && (
            <DashboardPage
              onNavigateTab={(tab) => setCurrentTab(tab)}
              onOpenDocument={handleOpenDocument}
            />
          )}

          {currentTab === 'documents' && (
            <DocumentsPage
              onOpenDocument={handleOpenDocument}
            />
          )}

          {currentTab === 'search' && (
            <SearchPage
              onOpenDocument={handleOpenDocument}
            />
          )}

          {currentTab === 'ask' && (
            <AskKnowledgePage
              onOpenDocument={handleOpenDocument}
            />
          )}

          {currentTab === 'processing' && (
            <ProcessingJobsPage />
          )}

          {currentTab === 'settings' && (
            <SettingsPage />
          )}
        </main>
      </div>

      {/* Document Details Modal with Extracted Text Viewer and Citations */}
      <DocumentDetailsModal
        document={selectedDocument}
        chunks={documentChunks}
        entities={documentEntities}
        relationships={documentRels}
        highlightedChunkId={highlightedChunkId}
        onClose={() => setSelectedDocument(null)}
      />
    </div>
  );
};

export default App;
