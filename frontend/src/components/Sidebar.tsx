import React from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  Search, 
  Sparkles, 
  Cpu, 
  Settings,
  ShieldCheck
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, isOpen = false, onClose }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'search', label: 'Search', icon: Search },
    { id: 'ask', label: 'Ask Knowledge', icon: Sparkles },
    { id: 'processing', label: 'Processing Jobs', icon: Cpu },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {isOpen && <div className="app-sidebar-backdrop" onClick={onClose} aria-hidden="true" />}
      <aside className={`app-sidebar${isOpen ? ' is-open' : ''}`} style={{
      width: '260px',
      backgroundColor: 'var(--jm-navy)',
      color: '#FFFFFF',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      height: '100vh',
      position: 'sticky',
      top: 0,
      borderRight: '1px solid rgba(255, 255, 255, 0.08)',
      zIndex: 40,
    }}>
      {/* Brand Logo & Title Area */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '9px',
            backgroundColor: 'var(--jm-light-blue)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '18px',
            color: '#FFFFFF',
            boxShadow: '0 4px 12px rgba(74, 95, 217, 0.4)',
          }}>
            IG
          </div>
          <div>
            <div style={{
              fontWeight: 700,
              fontSize: '17px',
              letterSpacing: '-0.01em',
              color: '#FFFFFF',
              minWidth: '120px',
            }}>
              InsightGraph RAG
            </div>
            <div style={{
              fontSize: '11px',
              color: '#93C5FD',
              fontWeight: 500,
              letterSpacing: '0.02em',
              textTransform: 'uppercase',
            }}>
              Document Intelligence
            </div>
          </div>
        </div>
      </div>

      {/* Navigation List */}
      <nav style={{ padding: '16px 12px', flex: 1, overflowY: 'auto' }}>
        <div style={{
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: '#94A3B8',
          padding: '0 12px 10px',
        }}>
          Knowledge Platform
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onClose?.();
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: isActive ? 'var(--jm-dark-blue)' : 'transparent',
                  color: isActive ? '#FFFFFF' : '#CBD5E1',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '14px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.16s ease',
                  boxShadow: isActive ? '0 2px 8px rgba(46, 58, 140, 0.4)' : 'none',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)';
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <Icon size={19} style={{ color: isActive ? '#FFFFFF' : '#94A3B8' }} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Footer System Status */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        backgroundColor: 'rgba(0, 0, 0, 0.15)',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <ShieldCheck size={18} style={{ color: '#10B981' }} />
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#E2E8F0' }}>Local RAG Engine</div>
          <div style={{ fontSize: '11px', color: '#94A3B8' }}>InsightGraph RAG v1.0.0</div>
        </div>
      </div>
      </aside>
    </>
  );
};
