import { motion, useScroll, useTransform } from 'framer-motion';
import { BookOpen, Bot, Code, LineChart, PlayCircle, GraduationCap } from 'lucide-react';

export default function DynamicBackground() {
  const { scrollYProgress } = useScroll();

  // Different parallax speeds for different elements
  // We map the scroll progress (0 to 1) to vertical pixel translations
  const y1 = useTransform(scrollYProgress, [0, 1], [0, -300]);
  const y2 = useTransform(scrollYProgress, [0, 1], [0, -150]);
  const y3 = useTransform(scrollYProgress, [0, 1], [0, -500]);
  const y4 = useTransform(scrollYProgress, [0, 1], [0, -200]);
  const y5 = useTransform(scrollYProgress, [0, 1], [0, -400]);
  const y6 = useTransform(scrollYProgress, [0, 1], [0, -600]);

  // Subtle rotation tied to scroll
  const r1 = useTransform(scrollYProgress, [0, 1], [0, 180]);
  const r2 = useTransform(scrollYProgress, [0, 1], [0, -180]);

  return (
    <div className="dynamic-background">
      {/* Background glowing orbs that scroll slowly */}
      <motion.div 
        style={{ y: y1, opacity: 0.4 }} 
        className="bg-glow top-glow" 
      />
      <motion.div 
        style={{ y: y2, opacity: 0.3 }} 
        className="bg-glow bottom-glow" 
      />

      {/* Parallax Icons */}
      <motion.div className="parallax-el" style={{ top: '15%', left: '10%', y: y3, rotate: r1 }}>
        <BookOpen size={80} />
      </motion.div>
      <motion.div className="parallax-el" style={{ top: '65%', left: '15%', y: y1, rotate: r2 }}>
        <Bot size={120} />
      </motion.div>
      <motion.div className="parallax-el" style={{ top: '25%', left: '85%', y: y4, rotate: r1 }}>
        <Code size={100} />
      </motion.div>
      <motion.div className="parallax-el" style={{ top: '85%', left: '80%', y: y6, rotate: r2 }}>
        <LineChart size={90} />
      </motion.div>
      <motion.div className="parallax-el" style={{ top: '45%', left: '50%', y: y5, rotate: r1 }}>
        <PlayCircle size={150} />
      </motion.div>
      <motion.div className="parallax-el" style={{ top: '10%', left: '50%', y: y2, rotate: r2 }}>
        <GraduationCap size={70} />
      </motion.div>
    </div>
  );
}
