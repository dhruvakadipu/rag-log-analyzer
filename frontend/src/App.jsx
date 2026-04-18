import { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import ActionButtons from './components/ActionButtons';
import API from './config';

// const API = 'http://localhost:8000';

function Toast({ toast, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000);
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
  const [aiMode, setAiMode] = useState('local'); // 'local' or 'cloud'
  const [toast, setToast] = useState(null);

  // Health check on mount
  useEffect(() => {
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(d => setOllamaOnline(d.ollama_connected))
      .catch(() => setOllamaOnline(false));
  }, []);

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
          <div className="header-logo">🔍</div>
          <div>
            <div className="header-title">Engineering Copilot</div>
            <div className="header-subtitle">Log Analysis · RAG · Local AI</div>
          </div>
          <div className="header-spacer" />

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
              className={`status-dot ${aiMode === 'cloud' ? 'online' : (ollamaOnline === true ? 'online' : ollamaOnline === false ? 'offline' : '')}`}
            />
            {aiMode === 'cloud'
              ? 'Gemini online'
              : (ollamaOnline === true
                ? 'Ollama online'
                : ollamaOnline === false
                  ? 'Ollama offline'
                  : 'Checking...')}
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
              <span className="empty-icon">🚀</span>
              <div className="empty-title">Upload a log to get started</div>
              <div className="empty-desc">
                Drop a <strong>.log</strong> or <strong>.txt</strong> file in the sidebar.
                The AI will index it and answer your debugging questions instantly.
              </div>
              {ollamaOnline === false && (
                <div style={{
                  marginTop: '16px',
                  padding: '12px 18px',
                  background: 'rgba(255,77,109,0.1)',
                  border: '1px solid rgba(255,77,109,0.3)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '12px',
                  color: 'var(--error-color)',
                  maxWidth: '360px',
                  lineHeight: '1.7',
                }}>
                  ⚠️ <strong>Ollama not detected.</strong> Run <code>ollama serve</code> and make sure <code>gemma:2b</code> is pulled.
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
