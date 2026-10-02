import { useState, useEffect } from 'react';
import { Play, Bot } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function TaskControls({ onTaskStart }) {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);

  const { user } = useAuth();

  useEffect(() => {
    fetch('/api/courses', { headers: { 'Authorization': `Bearer ${user?.id}` } })
      .then(res => res.json())
      .then(data => {
        if (data.courses) setCourses(data.courses);
      })
      .catch(err => console.error(err));
  }, [user]);

  const handleLaunchGemini = async () => {
    try {
      await fetch('/api/onboarding/launch_gemini', { method: 'POST', headers: { 'Authorization': `Bearer ${user?.id}` } });
      alert("Gemini Chrome session launched! Make sure you are logged in before running the note generation tasks.");
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    
    // Format numbers
    payload.download_weeks = parseInt(payload.download_weeks);
    payload.notes_weeks = parseInt(payload.notes_weeks);

    try {
      const res = await fetch('/api/run_task', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user?.id}`
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.task_id) {
        onTaskStart(data.task_id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card glass-panel">
      <h2 className="card-title">Task Orchestration</h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        
        <div className="form-group">
          <label className="form-label">Target Course</label>
          <select name="course" className="form-input" required defaultValue="">
            <option value="" disabled>Select a course...</option>
            {courses.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Weeks to Download</label>
            <input type="number" name="download_weeks" className="form-input" defaultValue="1" min="1" max="12" required />
          </div>
          <div className="form-group">
            <label className="form-label">Gemini Notes Weeks</label>
            <input type="number" name="notes_weeks" className="form-input" defaultValue="1" min="1" max="12" required />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Process script</label>
          <select name="script" className="form-input">
            <option value="orchestrator.py">Full Orchestrator (orchestrator.py)</option>
            <option value="phase2_extractor.py">Phase 2: PDF Extractor</option>
            <option value="phase3_transcripts.py">Phase 3: YouTube Transcripts</option>
            <option value="phase4_notion_sync.py">Phase 4: Notion Sync</option>
            <option value="phase5_telegram_bot.py">Phase 5: Telegram Bot</option>
          </select>
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: '1rem' }}>
          <Play size={18} /> {loading ? 'Starting...' : 'Execute Process'}
        </button>
      </form>
      
      <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid var(--color-border)' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Bot size={18} color="var(--color-accent)" /> AI Note Generation
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-muted-foreground)', marginBottom: '1rem' }}>
          If you are running the Gemini Note extraction phase, ensure the automated Chrome profile is logged into a Gemini Pro account.
        </p>
        <button className="btn btn-ghost" onClick={handleLaunchGemini} style={{ width: '100%', border: '1px solid var(--color-border)' }}>
          Launch Gemini Web UI
        </button>
      </div>
    </div>
  );
}
