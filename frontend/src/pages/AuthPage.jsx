import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { UserPlus, LogIn } from 'lucide-react';

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    
    const endpoint = isLogin ? '/api/login' : '/api/register';
    
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const result = await res.json();
      
      if (res.ok) {
        login(result.user);
        if (!result.user.onboarding_completed) {
          navigate('/onboarding');
        } else {
          navigate('/dashboard');
        }
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError("Failed to connect to server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
      <div className="glass-panel" style={{ padding: '3rem', width: '100%', maxWidth: '450px' }}>
        <h2 className="chapter-title" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
          {isLogin ? 'Welcome Back.' : 'Create Profile.'}
        </h2>
        <p className="chapter-subtitle" style={{ fontSize: '1rem', marginBottom: '2rem' }}>
          {isLogin ? 'Log in to orchestrate your study routine.' : 'Set up your local workspace environment.'}
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input type="text" name="username" className="form-input" required />
          </div>
          
          <div className="form-group">
            <label className="form-label">Password</label>
            <input type="password" name="password" className="form-input" required />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label className="form-label">Local Save Directory</label>
              <input type="text" name="local_save_path" className="form-input" placeholder="e.g. D:\StudyData" required />
              <small style={{ color: 'var(--color-muted-foreground)', marginTop: '0.5rem', display: 'block' }}>
                Where should downloaded PDFs and Transcripts be saved?
              </small>
            </div>
          )}

          {error && <div style={{ color: 'var(--color-destructive)', fontSize: '0.9rem' }}>{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: '1rem' }}>
            {isLogin ? <><LogIn size={18} /> Login</> : <><UserPlus size={18} /> Create Profile</>}
          </button>
        </form>

        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <button className="btn-ghost" onClick={() => setIsLogin(!isLogin)} style={{ border: 'none', background: 'transparent', color: 'var(--color-accent)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
            {isLogin ? 'Need an account? Create one.' : 'Already have an account? Log in.'}
          </button>
        </div>
      </div>
    </div>
  );
}
