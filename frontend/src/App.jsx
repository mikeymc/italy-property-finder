// ABOUTME: Main app layout with two-panel zone explorer and analysis view.
// ABOUTME: Left panel browses OMI zones, right panel shows ROI analysis.

import { useState } from 'react';
import { ZoneExplorer } from './components/ZoneExplorer';
import { AnalysisPanel } from './components/AnalysisPanel';
import './App.css';

function App() {
  const [selectedZone, setSelectedZone] = useState(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Italy Real Estate Finder</h1>
      </header>
      <main className="app-main">
        <div className="panel panel-left">
          <ZoneExplorer onSelectZone={setSelectedZone} />
        </div>
        <div className="panel panel-right">
          <AnalysisPanel zone={selectedZone} />
        </div>
      </main>
    </div>
  );
}

export default App;
