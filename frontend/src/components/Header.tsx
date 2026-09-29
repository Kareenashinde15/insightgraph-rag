import React, { useState } from 'react';
import { Bell, Sun, Moon, CheckCircle2 } from 'lucide-react';

interface HeaderProps {
  theme: string;
  onToggleTheme: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  theme,
  onToggleTheme,
  onOpenSettings,
}) => {
  const [showNotifications, setShowNotifications] = useState(false);

  const notifications: Array<{ id: number; title: string; desc: string; time: string }> = [];

  return (
    <header style={{
      height: '68px',
      backgroundColor: 'var(--bg-surface)',
      borderBottom: '1px solid var(--jm-border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-end',
      padding: '0 28px',
      position: 'sticky',
      top: 0,
      zIndex: 30,
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)',
    }}>
      {/* Right Action Icons & Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {/* System Status Indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 12px',
          borderRadius: '20px',
          backgroundColor: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          fontSize: '12.5px',
          fontWeight: 600,
          color: '#10B981',
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#10B981',
            display: 'inline-block',
            boxShadow: '0 0 6px rgba(16, 185, 129, 0.6)',
          }} />
          <span>Knowledge Base Online</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          style={{
            background: 'transparent',
            border: '1px solid var(--jm-border)',
            borderRadius: '8px',
            width: '38px',
            height: '38px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            transition: 'all 0.16s ease',
          }}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {/* Notifications Popover Toggle */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            title="Notifications"
            style={{
              position: 'relative',
              background: 'transparent',
              border: '1px solid var(--jm-border)',
              borderRadius: '8px',
              width: '38px',
              height: '38px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: 'var(--text-secondary)',
            }}
          >
            <Bell size={18} />
            <span style={{
              position: 'absolute',
              top: '6px',
              right: '6px',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'var(--jm-light-blue)',
            }} />
          </button>

          {showNotifications && (
            <div style={{
              position: 'absolute',
              right: 0,
              top: '48px',
              width: '320px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--jm-border)',
              borderRadius: '10px',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
              padding: '16px',
              zIndex: 50,
            }}>
              <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '12px' }}>System Notifications</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {notifications.length === 0 && (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No new notifications.</div>
                )}
                {notifications.map((n) => (
                  <div key={n.id} style={{
                    padding: '10px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-surface-secondary)',
                    border: '1px solid var(--jm-border)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600 }}>
                      <CheckCircle2 size={14} color="#10B981" />
                      <span>{n.title}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>{n.desc}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>{n.time}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Avatar */}
        <div 
          onClick={onOpenSettings}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '4px 8px 4px 4px',
            borderRadius: '24px',
            border: '1px solid var(--jm-border)',
            cursor: 'pointer',
            transition: 'background-color 0.16s ease',
          }}
        >
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: 'var(--jm-dark-blue)',
            color: '#FFFFFF',
            fontWeight: 700,
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            IG
          </div>
          <span style={{ fontSize: '13.5px', fontWeight: 600, paddingRight: '6px' }}>InsightGraph RAG Admin</span>
        </div>
      </div>
    </header>
  );
};
