import { useState, useEffect, useRef } from 'react';
import { Terminal, Trash2 } from 'lucide-react';

export default function DebugConsole({ taskId }) {
  const [logs, setLogs] = useState('');
  const [status, setStatus] = useState('idle');
  const viewerRef = useRef(null);

  useEffect(() => {
    if (!taskId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/task_status/${taskId}`);
        const data = await res.json();
        
        if (data.logs) {
          setLogs(data.logs);
        }
        if (data.status) {
          setStatus(data.status);
        }

        if (data.status === 'completed' || data.status === 'error') {
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [taskId]);

  useEffect(() => {
    if (viewerRef.current) {
      viewerRef.current.scrollTop = viewerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="card glass-panel debug-zone">
      <div className="debug-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Terminal size={20} color="var(--color-accent)" />
          <h2 className="card-title" style={{ margin: 0 }}>Debug Console</h2>
          <div className="status-badge">
            <span className={`dot ${status}`}></span>
            {status}
          </div>
        </div>
        <button className="btn btn-ghost" onClick={() => { setLogs(''); setStatus('idle'); }} style={{ padding: '0.5rem', width: 'auto' }}>
          <Trash2 size={16} />
        </button>
      </div>
      <div className="log-viewer" ref={viewerRef}>
        {logs || <span style={{ color: '#475569' }}>System is ready. Awaiting task execution...</span>}
      </div>
    </div>
  );
}
