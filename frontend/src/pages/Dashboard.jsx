import { useState } from 'react';
import TaskControls from '../components/TaskControls';
import SettingsForm from '../components/SettingsForm';
import DebugConsole from '../components/DebugConsole';
import { Settings, PlayCircle } from 'lucide-react';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('controls');
  const [taskId, setTaskId] = useState(null);

  return (
    <div className="dashboard-layout">
      <div className="tabs-header">
        <button 
          className={`tab-btn ${activeTab === 'controls' ? 'active' : ''}`}
          onClick={() => setActiveTab('controls')}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <PlayCircle size={18} /> Control Center
        </button>
        <button 
          className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <Settings size={18} /> Settings
        </button>
      </div>

      <div className="dashboard-grid">
        {activeTab === 'controls' && (
          <>
            <TaskControls onTaskStart={(id) => setTaskId(id)} />
            <DebugConsole taskId={taskId} />
          </>
        )}
        
        {activeTab === 'settings' && (
          <div style={{ gridColumn: '1 / -1', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
            <SettingsForm />
          </div>
        )}
      </div>
    </div>
  );
}
