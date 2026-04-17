import { useState, useRef } from 'react';
import API from '../config';

// const API = 'http://localhost:8000';

export default function FileUpload({ files, activeFile, onFileSelect, onFilesChange, onToast }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['log', 'txt'].includes(ext)) {
      onToast('Only .log and .txt files are supported.', 'error');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API}/upload-log`, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }
      const data = await res.json();
      onFilesChange(prev => {
        const exists = prev.find(f => f.filename === data.filename);
        if (exists) return prev.map(f => f.filename === data.filename ? data : f);
        return [...prev, data];
      });
      onFileSelect(data.filename);
      onToast(`✓ ${data.filename} processed — ${data.chunk_count} chunks`, 'success');
    } catch (err) {
      onToast(err.message, 'error');
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }

  function onInputChange(e) {
    handleFile(e.target.files[0]);
    e.target.value = '';
  }

  return (
    <>
      <div className="sidebar-section">
        <div className="sidebar-label">Upload Log</div>
        <label
          className={`upload-zone ${dragging ? 'drag-over' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          htmlFor="file-input"
        >
          <input
            id="file-input"
            ref={inputRef}
            type="file"
            accept=".log,.txt"
            onChange={onInputChange}
            disabled={uploading}
          />
          <span className="upload-icon">📂</span>
          <div className="upload-text">
            <strong>Drop a log file</strong> or click to browse
          </div>
          <div className="upload-hint">.log · .txt supported</div>
          {uploading && (
            <div className="uploading-bar">
              <div className="uploading-bar-fill" />
            </div>
          )}
        </label>
      </div>

      <div className="sidebar-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: 0 }}>
        <div style={{ padding: '12px 16px 6px' }} className="sidebar-label">
          Loaded Files ({files.length})
        </div>
        <div className="file-list">
          {files.length === 0 && (
            <div style={{ padding: '12px 8px', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
              No files loaded yet
            </div>
          )}
          {files.map(f => (
            <div
              key={f.filename}
              className={`file-item ${activeFile === f.filename ? 'active' : ''}`}
              onClick={() => onFileSelect(f.filename)}
            >
              <span className="file-icon">📄</span>
              <div className="file-info">
                <div className="file-name" title={f.filename}>{f.filename}</div>
                <div className="file-meta">
                  {f.stats?.error > 0 && <span className="badge badge-error">✕ {f.stats.error} err</span>}
                  {f.stats?.warning > 0 && <span className="badge badge-warn">⚠ {f.stats.warning} warn</span>}
                  {f.chunk_count > 0 && <span className="badge badge-chunk">{f.chunk_count} chunks</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
