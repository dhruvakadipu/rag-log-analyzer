import { useRef, useState } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/chat/ChatInterface';
import ActionButtons from './components/ActionButtons';
import { useAppContext } from './contexts/AppContext';
import { uploadLog } from './api/endpoints';

export default function App() {
  const {
    theme, toggleTheme,
    aiMode, setAiMode,
    ollamaOnline, checkHealth,
    files, setFiles,
    activeFile, setActiveFile,
    toast, setToast, showToast
  } = useAppContext();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  async function handleMainUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['log', 'txt'].includes(ext)) {
      showToast('Only .log and .txt files are supported.', 'error');
      e.target.value = '';
      return;
    }

    setIsUploading(true);
    try {
      const data = await uploadLog(file);
      setFiles(prev => {
        const exists = prev.find(f => f.filename === data.filename);
        if (exists) return prev.map(f => f.filename === data.filename ? data : f);
        return [...prev, data];
      });
      handleFileSelect(data.filename);
      showToast(`✓ ${data.filename} processed — ${data.chunk_count} chunks`, 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  }

  function handleFileSelect(filename) {
    setActiveFile(filename);
    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  }

  return (
    <>
      <div className="app-shell">
        {/* ── Header ── */}
        <header className="app-header">
          <button className="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
            ☰
          </button>
          <div className="header-logo">L</div>
          <div>
            <div className="header-title">Logly</div>
            <div className="header-subtitle">Ask your logs anything.</div>
          </div>
          <div className="header-spacer" />

          <button className="theme-toggle" onClick={toggleTheme} title="Toggle Theme">
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          <div className="ai-toggle-container">
            <button
              className={`ai-toggle-btn ${aiMode === 'local' ? 'active' : ''}`}
              onClick={() => setAiMode('local')}
            >
              Local
            </button>
            <button
              className={`ai-toggle-btn ${aiMode === 'cloud' ? 'active' : ''}`}
              onClick={() => setAiMode('cloud')}
            >
              Cloud
            </button>
          </div>

          <div className="status-badge" style={{ opacity: aiMode === 'local' ? 1 : 0.5 }}>
            <span
              className={`status-dot ${aiMode === 'cloud' ? 'online' : (ollamaOnline?.online && ollamaOnline?.model_found ? 'online' : (ollamaOnline?.online === false || ollamaOnline?.model_found === false) ? 'offline' : '')}`}
            />
            <span className="status-text">
              {aiMode === 'cloud'
                ? 'Gemini online'
                : (ollamaOnline?.online === true && ollamaOnline?.model_found === true
                  ? 'Ollama online'
                  : (ollamaOnline?.online === false
                    ? 'Ollama offline'
                    : ollamaOnline?.model_found === false
                      ? 'Model missing'
                      : 'Checking...'))}
            </span>
          </div>
        </header>

        {/* ── Sidebar ── */}
        {sidebarOpen && <div className="mobile-overlay" onClick={() => setSidebarOpen(false)} />}
        <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <FileUpload
            files={files}
            activeFile={activeFile}
            onFileSelect={handleFileSelect}
          />
          <ActionButtons />
        </aside>

        {/* ── Main ── */}
        <main className="main-panel">
          {!activeFile ? (
            <div className="empty-state">
              <span className="empty-icon">🔍</span>
              <div className="empty-title">Ready to analyze your logs?</div>
              <div className="empty-desc">
                Upload a <strong>.log</strong> or <strong>.txt</strong> file below.
                The AI will index it and answer your debugging questions instantly.
              </div>
              <div style={{ marginTop: '24px' }}>
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  accept=".log,.txt"
                  onChange={handleMainUpload}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading || (aiMode === 'local' && (ollamaOnline?.online === false || ollamaOnline?.model_found === false))}
                  style={{ width: 'auto', padding: '12px 24px', fontSize: '14px', borderRadius: 'var(--radius-md)', margin: '0 auto' }}
                >
                  {isUploading ? 'Uploading...' : '📁 Upload Log File'}
                </button>
              </div>
            </div>
          ) : (
            <ChatInterface />
          )}
        </main>
      </div>

      {/* ── Toast ── */}
      {toast && (
        <div className={`toast toast-${toast.type}`} role="alert">
            <span>{toast.message}</span>
            <button
                onClick={() => setToast(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', marginLeft: 'auto', fontSize: '14px' }}
            >✕</button>
        </div>
      )}
    </>
  );
}
