import { useState } from 'react';

const API = 'http://localhost:8000';

export default function ActionButtons({ activeFile, files, onResult, onToast, isLoading, setIsLoading, aiMode }) {
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [compareFile2, setCompareFile2] = useState('');

  async function handleSummarize() {
    if (!activeFile || isLoading) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: activeFile, mode: aiMode }),
      });
      if (!res.ok) throw new Error('Summarize failed');
      const data = await res.json();
      onResult(`📋 **Log Summary for \`${activeFile}\`**\n\n${data.summary}`);
    } catch (err) {
      onToast(err.message, 'error');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCompare() {
    if (!activeFile || !compareFile2 || isLoading) return;
    setShowCompareModal(false);
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename1: activeFile, filename2: compareFile2, mode: aiMode }),
      });
      if (!res.ok) throw new Error('Comparison failed');
      const data = await res.json();
      onResult(`🔍 **Log Comparison: \`${activeFile}\` vs \`${compareFile2}\`**\n\n${data.comparison}`);
    } catch (err) {
      onToast(err.message, 'error');
    } finally {
      setIsLoading(false);
    }
  }

  const otherFiles = files.filter(f => f.filename !== activeFile);

  return (
    <>
      <div className="actions-panel">
        <div className="sidebar-label">Actions</div>
        <button
          id="btn-summarize"
          className="btn btn-primary"
          onClick={handleSummarize}
          disabled={!activeFile || isLoading}
          title="Generate AI summary of the active log"
        >
          <span>📋</span> Summarize Log
        </button>
        <button
          id="btn-compare"
          className="btn btn-secondary"
          onClick={() => { setCompareFile2(''); setShowCompareModal(true); }}
          disabled={!activeFile || files.length < 2 || isLoading}
          title={files.length < 2 ? 'Upload at least 2 files to compare' : 'Compare two log files'}
        >
          <span>🔍</span> Compare Logs
          {files.length < 2 && <span style={{ marginLeft: 'auto', fontSize: '10px', opacity: 0.6 }}>need 2 files</span>}
        </button>
      </div>

      {showCompareModal && (
        <div className="modal-overlay" onClick={() => setShowCompareModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🔍 Compare Logs</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Comparing <strong style={{ color: 'var(--accent-cyan)' }}>{activeFile}</strong> against:
            </div>
            <select
              className="modal-select"
              value={compareFile2}
              onChange={e => setCompareFile2(e.target.value)}
              id="compare-file-select"
            >
              <option value="">— Select a file —</option>
              {otherFiles.map(f => (
                <option key={f.filename} value={f.filename}>{f.filename}</option>
              ))}
            </select>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowCompareModal(false)} style={{ width: 'auto' }}>
                Cancel
              </button>
              <button
                id="btn-compare-confirm"
                className="btn btn-primary"
                onClick={handleCompare}
                disabled={!compareFile2}
                style={{ width: 'auto' }}
              >
                Compare
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
