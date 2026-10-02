import { useState, useEffect } from 'react';
import { Save } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function SettingsForm() {
  const [config, setConfig] = useState({});
  const [saved, setSaved] = useState(false);

  const { user } = useAuth();

  useEffect(() => {
    fetch('/api/config', { headers: { 'Authorization': `Bearer ${user?.id}` } })
      .then(res => res.json())
      .then(data => setConfig(data))
      .catch(err => console.error(err));
  }, [user]);

  const handleChange = (e) => {
    setConfig({ ...config, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user?.id}`
        },
        body: JSON.stringify(config)
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="card glass-panel">
      <h2 className="card-title">System Configuration</h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        <div>
          <h3 style={{ color: 'var(--color-accent)', marginBottom: '1rem', fontSize: '1.1rem' }}>Telegram Integration</h3>
          <div className="form-group">
            <label className="form-label">Bot Token</label>
            <input type="password" name="TELEGRAM_BOT_TOKEN" className="form-input" value={config.TELEGRAM_BOT_TOKEN || ''} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label className="form-label">Chat ID</label>
            <input type="text" name="TELEGRAM_CHAT_ID" className="form-input" value={config.TELEGRAM_CHAT_ID || ''} onChange={handleChange} />
          </div>
        </div>

        <div>
          <h3 style={{ color: 'var(--color-accent)', marginBottom: '1rem', fontSize: '1.1rem' }}>Notion Sync</h3>
          <div className="form-group">
            <label className="form-label">Internal Integration Token</label>
            <input type="password" name="NOTION_TOKEN" className="form-input" value={config.NOTION_TOKEN || ''} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label className="form-label">Database ID</label>
            <input type="text" name="NOTION_DATABASE_ID" className="form-input" value={config.NOTION_DATABASE_ID || ''} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label className="form-label">Page URL</label>
            <input type="text" name="NOTION_PAGE_URL" className="form-input" value={config.NOTION_PAGE_URL || ''} onChange={handleChange} />
          </div>
        </div>

        <div>
          <h3 style={{ color: 'var(--color-accent)', marginBottom: '1rem', fontSize: '1.1rem' }}>Browser Automation</h3>
          <div className="form-group">
            <label className="form-label">CDP Port</label>
            <input type="text" name="CDP_PORT" className="form-input" value={config.CDP_PORT || ''} onChange={handleChange} />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
          <button type="submit" className="btn btn-primary" style={{ width: 'auto' }}>
            <Save size={18} /> Save Settings
          </button>
          {saved && <span style={{ color: '#10B981', fontSize: '0.9rem', fontWeight: '500' }}>Changes applied successfully!</span>}
        </div>
      </form>
    </div>
  );
}
