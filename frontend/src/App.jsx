import { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import ActionButtons from './components/ActionButtons';
import API, { DEFAULT_AI_MODE, TOAST_TIMEOUT } from './config';

// const API = 'http://localhost:8000';

function Toast({ toast, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, TOAST_TIMEOUT);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div className={`toast toast-${toast.type}`} role="alert">
      <span>{toast.message}</span>
      <button
        onClick={onClose}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', marginLeft: 'auto', fontSize: '14px' }}
      >✕</button>
    </div>
  );
}

export default function App() {
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  // Per-file chat history: { filename -> messages[] }
  const [chatHistory, setChatHistory] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [ollamaOnline, setOllamaOnline] = useState(null);
  const [aiMode, setAiMode] = useState(DEFAULT_AI_MODE); // 'local' or 'cloud'
  const [toast, setToast] = useState(null);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');

  const checkHealth = () => {
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(d => setOllamaOnline(d.ollama)) // Set the whole object
      .catch(() => setOllamaOnline({ online: false }));
  };

  // Consolidated health management: 
  // Runs on mount and whenever aiMode changes (to be snappy), then polls every 30s.
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); 
    return () => clearInterval(interval);
  }, [aiMode]);

  // Sync theme to body attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  function toggleTheme() {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  }

  const messages = activeFile ? (chatHistory[activeFile] || []) : [];

  function setMessages(updater) {
    if (!activeFile) return;
    setChatHistory(prev => ({
      ...prev,
      [activeFile]: typeof updater === 'function' ? updater(prev[activeFile] || []) : updater,
    }));
  }

  function showToast(message, type = 'info') {
    setToast({ message, type, id: Date.now() });
  }

  const activeFileData = files.find(f => f.filename === activeFile);

  return (
    <>
      <div className="app-shell">
        {/* ── Header ── */}
        <header className="app-header">
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
            {aiMode === 'cloud'
              ? 'Gemini online'
              : (ollamaOnline?.online === true && ollamaOnline?.model_found === true
                ? 'Ollama online'
                : (ollamaOnline?.online === false
                  ? 'Ollama offline'
                  : ollamaOnline?.model_found === false
                    ? 'Model missing'
                    : 'Checking...'))}
          </div>
        </header>

        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <FileUpload
            files={files}
            activeFile={activeFile}
            onFileSelect={setActiveFile}
            onFilesChange={setFiles}
            onToast={showToast}
          />
          <ActionButtons
            activeFile={activeFile}
            files={files}
            setMessages={setMessages}
            onToast={showToast}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
            aiMode={aiMode}
          />
        </aside>

        {/* ── Main ── */}
        <main className="main-panel">
          {!activeFile ? (
            <div className="empty-state">
              <span className="empty-icon">🔍</span>
              <div className="empty-title">Upload a log to get started</div>
              <div className="empty-desc">
                Drop a <strong>.log</strong> or <strong>.txt</strong> file in the sidebar.
                The AI will index it and answer your debugging questions instantly.
              </div>
              {aiMode === 'local' && (ollamaOnline?.online === false || ollamaOnline?.model_found === false) && (
                <div style={{
                  marginTop: '16px',
                  padding: '16px 20px',
                  background: 'rgba(255,77,109,0.1)',
                  border: '1px solid rgba(255,77,109,0.3)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '13px',
                  color: 'var(--error-color)',
                  maxWidth: '420px',
                  lineHeight: '1.6',
                  textAlign: 'left'
                }}>
                  <div style={{ fontWeight: '700', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    ⚠️ {ollamaOnline.online === false ? 'Ollama not detected' : 'Model not found'}
                  </div>
                  {ollamaOnline.online === false ? (
                    <ul style={{ margin: '0', paddingLeft: '18px' }}>
                      <li>Run <code>ollama serve</code> in your terminal.</li>
                      <li>Ensure Ollama is accessible at <code>http://localhost:11434</code>.</li>
                      <li>Check if the Ollama application is running in the background.</li>
                    </ul>
                  ) : (
                    <ul style={{ margin: '0', paddingLeft: '18px' }}>
                      <li>The model <code>{ollamaOnline.model_name}</code> is not pulled.</li>
                      <li>Run <code>ollama pull {ollamaOnline.model_name}</code> in your terminal.</li>
                    </ul>
                  )}
                  <div style={{ marginTop: '12px' }}>
                    <button 
                      onClick={checkHealth}
                      style={{
                        background: 'rgba(255,255,255,0.1)',
                        border: '1px solid rgba(255,77,109,0.3)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '6px 12px',
                        fontSize: '11px',
                        color: 'inherit',
                        cursor: 'pointer',
                        fontWeight: '600'
                      }}
                    >
                      🔄 Retry Connection
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <ChatInterface
              activeFile={activeFile}
              fileData={activeFileData}
              messages={messages}
              setMessages={setMessages}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
              onToast={showToast}
              aiMode={aiMode}
            />
          )}
        </main>
      </div>

      {/* ── Toast ── */}
      {toast && (
        <Toast
          key={toast.id}
          toast={toast}
          onClose={() => setToast(null)}
        />
      )}
    </>
  );
}
