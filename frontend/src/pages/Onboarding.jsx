import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Bot, CheckCircle2 } from 'lucide-react';

export default function Onboarding() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const authHeader = { 'Authorization': `Bearer ${user.id}` };

  const handleComplete = async () => {
    try {
      const res = await fetch('/api/onboarding/complete', { method: 'POST', headers: authHeader });
      const data = await res.json();
      if (data.status === 'success') {
        setUser(data.user);
        navigate('/dashboard');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLaunchIITM = async () => {
    try {
      await fetch('/api/onboarding/launch_iitm', { method: 'POST', headers: authHeader });
      setMessage("Chrome opened! Please login to the IITM portal in the new window, then click 'I am logged in'.");
    } catch (e) {
      console.error(e);
    }
  };

  const handleScrapeCourses = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/onboarding/scrape_courses', { method: 'POST', headers: authHeader });
      const data = await res.json();
      if (data.courses) {
        setMessage('');
        await handleComplete();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
      <div className="glass-panel" style={{ padding: '3rem', width: '100%', maxWidth: '600px' }}>
        
        {message && (
          <div style={{ padding: '1rem', background: 'rgba(161, 98, 7, 0.15)', border: '1px solid var(--color-accent)', borderRadius: '8px', color: 'var(--color-accent)', marginBottom: '1.5rem', textAlign: 'center' }}>
            {message}
          </div>
        )}
        
        {step === 1 && (
          <div>
            <BookOpen color="var(--color-accent)" size={48} style={{ margin: '0 auto 1.5rem auto', display: 'block' }} />
            <h2 className="chapter-title" style={{ fontSize: '2.5rem', textAlign: 'center', display: 'block' }}>Connect IITM</h2>
            <p className="chapter-subtitle" style={{ textAlign: 'center', marginBottom: '2rem' }}>
              We need to identify the courses you are currently enrolled in.
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <button className="btn btn-ghost" onClick={handleLaunchIITM}>
                1. Open Chrome and Login to IITM
              </button>
              <button className="btn btn-primary" onClick={handleScrapeCourses} disabled={loading}>
                {loading ? 'Scraping Curriculum...' : '2. I am logged in - Scrape Courses'}
              </button>
            </div>
          </div>
        )}
        
      </div>
    </div>
  );
}
