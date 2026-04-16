import { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';

const API = 'http://localhost:8000';

export default function ChatInterface({ activeFile, fileData, messages, setMessages, isLoading, setIsLoading, onToast, aiMode }) {
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 160) + 'px';
    }
  }, [input]);

  async function sendMessage() {
    const question = input.trim();
    if (!question || isLoading || !activeFile) return;

    setInput('');

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, filename: activeFile, mode: aiMode }),
      });
      if (!res.ok) throw new Error('Failed to get answer');
      const data = await res.json();

      const aiMsg = {
        id: Date.now() + 1,
        role: 'ai',
        content: data.answer,
        sources: data.sources || [],
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      onToast(err.message, 'error');
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'ai',
        content: '❌ Failed to get a response. Make sure Ollama is running.',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const stats = fileData?.stats;

  return (
    <div className="chat-container">
      {/* Chat Header */}
      <div className="chat-header">
        <span style={{ fontSize: '16px' }}>📄</span>
        <span className="chat-file-name">{activeFile}</span>
        {stats && (
          <div className="chat-file-stats">
            {stats.error > 0 && <span className="badge badge-error">✕ {stats.error}</span>}
            {stats.warning > 0 && <span className="badge badge-warn">⚠ {stats.warning}</span>}
            <span className="badge badge-info">ℹ {stats.info}</span>
            <span className="badge badge-chunk">{stats.total_lines} lines</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="messages-area" id="messages-area">
        {messages.length === 0 && (
          <div className="empty-state" style={{ flex: 'none', padding: '40px 20px' }}>
            <span className="empty-icon">💬</span>
            <div className="empty-title">Ask about your logs</div>
            <div className="empty-desc">
              Try: <em>"What errors occurred?"</em> · <em>"What caused the high latency?"</em> · <em>"Summarize all warnings"</em>
            </div>
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="message ai">
            <div className="message-avatar">🤖</div>
            <div className="loading-bubble">
              <div className="loading-dot" />
              <div className="loading-dot" />
              <div className="loading-dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <div className="input-row">
          <textarea
            id="chat-input"
            ref={textareaRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question about the log..."
            rows={1}
            disabled={isLoading}
          />
          <button
            id="send-btn"
            className="send-btn"
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            title="Send (Enter)"
          >
            ➤
          </button>
        </div>
        <div className="input-hint">
          Enter to send · Shift+Enter for new line · Powered by Ollama + FAISS
        </div>
      </div>
    </div>
  );
}
