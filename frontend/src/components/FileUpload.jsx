export default function FileUpload({ files, activeFile, onFileSelect }) {
  return (
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
  );
}
