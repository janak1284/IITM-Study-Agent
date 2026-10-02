import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight, Bot, BookOpen, Clock, AlertCircle } from 'lucide-react';

export default function LandingPage() {
  const containerRef = useRef(null);
  
  // Track scroll progress across the entire page (0 to 1)
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  // Chapter 1 Animations (Hero)
  const c1Opacity = useTransform(scrollYProgress, [0, 0.15, 0.2, 1], [1, 1, 0, 0]);
  const c1Scale = useTransform(scrollYProgress, [0, 0.2, 1], [1, 0.8, 0.8]);

  // Chapter 2 Animations (The Problem)
  const c2Opacity = useTransform(scrollYProgress, [0, 0.15, 0.25, 0.4, 0.5, 1], [0, 0, 1, 1, 0, 0]);
  const c2X = useTransform(scrollYProgress, [0, 0.15, 0.25, 1], [-100, -100, 0, 0]);

  // Chapter 3 Animations (The Solution)
  const c3Opacity = useTransform(scrollYProgress, [0, 0.45, 0.55, 0.75, 0.85, 1], [0, 0, 1, 1, 0, 0]);
  const c3Y = useTransform(scrollYProgress, [0, 0.45, 0.55, 1], [100, 100, 0, 0]);
  
  // Chapter 4 Animations (CTA)
  const c4Opacity = useTransform(scrollYProgress, [0, 0.8, 0.9, 1], [0, 0, 1, 1]);
  const c4Scale = useTransform(scrollYProgress, [0, 0.8, 0.9, 1], [0.9, 0.9, 1, 1]);

  return (
    <div ref={containerRef} className="scroll-container" style={{ height: '400vh', position: 'relative' }}>
      
      {/* Sticky viewport container */}
      <div style={{ position: 'sticky', top: 0, height: '100vh', width: '100%', overflow: 'hidden' }}>
        
        {/* Chapter 1: Hero */}
        <motion.div 
          className="chapter" 
          style={{ opacity: c1Opacity, scale: c1Scale, position: 'absolute', top: 0, left: 0, width: '100%' }}
        >
          <div className="chapter-content">
            <motion.h1 
              className="chapter-title"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              Automate your<br/>IITM Study Routine
            </motion.h1>
            <motion.p 
              className="chapter-subtitle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              Scroll to discover the orchestration engine for curriculum extraction, <br/>Notion syncing, and Gemini insights.
            </motion.p>
          </div>
        </motion.div>

        {/* Chapter 2: The Problem */}
        <motion.div 
          className="chapter" 
          style={{ opacity: c2Opacity, x: c2X, position: 'absolute', top: 0, left: 0, width: '100%' }}
        >
          <div className="chapter-content">
            <AlertCircle color="var(--color-destructive)" size={48} style={{ margin: '0 auto 2rem auto' }} />
            <h2 className="chapter-title" style={{ fontSize: '3.5rem' }}>The Manual Grind.</h2>
            <p className="chapter-subtitle">
              Downloading PDFs, scraping transcripts, and taking notes manually takes hours every week. What if your agent did it while you slept?
            </p>
          </div>
        </motion.div>

        {/* Chapter 3: The Solution */}
        <motion.div 
          className="chapter" 
          style={{ opacity: c3Opacity, y: c3Y, position: 'absolute', top: 0, left: 0, width: '100%' }}
        >
        <div className="chapter-content">
          <h2 className="chapter-title" style={{ fontSize: '3.5rem' }}>The Solution.</h2>
          
          <div className="feature-grid">
            <div className="glass-panel" style={{ padding: '2rem', textAlign: 'left' }}>
              <BookOpen color="var(--color-accent)" size={32} style={{ marginBottom: '1rem' }} />
              <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', color: 'var(--color-foreground)' }}>Curriculum Sync</h3>
              <p style={{ color: 'var(--color-muted-foreground)', fontSize: '0.95rem' }}>Pulls the latest videos and assignments directly from the portal automatically.</p>
            </div>
            
            <div className="glass-panel" style={{ padding: '2rem', textAlign: 'left' }}>
              <Bot color="var(--color-accent)" size={32} style={{ marginBottom: '1rem' }} />
              <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', color: 'var(--color-foreground)' }}>Gemini Insights</h3>
              <p style={{ color: 'var(--color-muted-foreground)', fontSize: '0.95rem' }}>Auto-generates study notes and transcripts using vision AI directly on the web.</p>
            </div>
            
            <div className="glass-panel" style={{ padding: '2rem', textAlign: 'left' }}>
              <Clock color="var(--color-accent)" size={32} style={{ marginBottom: '1rem' }} />
              <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem', color: 'var(--color-foreground)' }}>Notion & Telegram</h3>
              <p style={{ color: 'var(--color-muted-foreground)', fontSize: '0.95rem' }}>Pushes everything to your workspace and alerts you on your phone instantly.</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Chapter 4: Climax CTA */}
      <motion.div 
        className="chapter" 
        style={{ opacity: c4Opacity, scale: c4Scale, position: 'absolute', top: 0, left: 0, width: '100%', pointerEvents: 'auto' }}
      >
        <div className="chapter-content">
          <h2 className="chapter-title" style={{ fontSize: '4rem' }}>Ready to Orchestrate?</h2>
          <p className="chapter-subtitle" style={{ marginBottom: '3rem' }}>
            Enter the control center to configure your workflow.
          </p>
          <Link to="/dashboard" className="btn btn-primary" style={{ padding: '1rem 2rem', fontSize: '1.1rem' }}>
            Initialize Dashboard <ArrowRight size={20} style={{ marginLeft: '0.5rem' }} />
          </Link>
        </div>
      </motion.div>

      </div> {/* End of sticky viewport */}
    </div>
  );
}
