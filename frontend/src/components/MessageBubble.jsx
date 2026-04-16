import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Highlights ERROR/WARNING/INFO keywords in a log line with colored spans.
 */
function highlightLogLine(text) {
  const lines = text.split('\n');
  return lines.map((line, lineIdx) => {
    const upperLine = line.toUpperCase();
    let cls = '';
    if (upperLine.includes('ERROR'))   cls = 'err';
    else if (upperLine.includes('WARN')) cls = 'warn';
    else if (upperLine.includes('INFO')) cls = 'info';

    return (
      <span key={lineIdx} className={cls || undefined}>
        {line}{lineIdx < lines.length - 1 ? '\n' : ''}
      </span>
    );
  });
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function MessageBubble({ message }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';
  const hasSources = !isUser && message.sources && message.sources.length > 0;

  return (
    <div className={`message ${isUser ? 'user' : 'ai'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>

      <div className="message-content">
        <div className="bubble markdown">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {hasSources && (
          <button
            className="sources-toggle"
            onClick={() => setShowSources(s => !s)}
            aria-expanded={showSources}
          >
            <span>{showSources ? '▾' : '▸'}</span>
            {showSources ? 'Hide' : 'Show'} {message.sources.length} source chunk{message.sources.length !== 1 ? 's' : ''}
          </button>
        )}

        {hasSources && showSources && (
          <div className="sources-panel">
            {message.sources.map((src, i) => (
              <div key={i} className="source-chunk">
                {highlightLogLine(src.text)}
              </div>
            ))}
          </div>
        )}

        <div className="message-time">
          {formatTime(new Date(message.timestamp))}
        </div>
      </div>
    </div>
  );
}
