// ABOUTME: Main app layout with two-panel zone explorer and analysis view.
// ABOUTME: Left panel browses OMI zones, right panel shows ROI analysis.

import { useState } from 'react';
import { ZoneExplorer } from './components/ZoneExplorer';
import { AnalysisPanel } from './components/AnalysisPanel';
import './App.css';

export const defaultParams = {
  purchase_price: 100000,
  square_meters: 60,
  nightly_rate: 80,
  occupancy_rate: 0.6,
  down_payment_pct: 0.2,
  mutuo_rate: 0.04,
  mutuo_term: 20,
  management_fee_pct: 0.2,
  platform_fee_pct: 0.15,
  cleaning_fee: 50,
  avg_stay_nights: 4,
  registro_pct: 0.09,
  notary_purchase_fee: 2500,
  notary_mutuo_fee: 1500,
  agency_fee_pct: 0.03,
  mutuo_tax_pct: 0.02,
  bank_origination_fee: 500,
  appraisal_fee: 300,
  technical_report_fee: 500,
  cadastral_and_mortgage_taxes: 100,
  imu: 1200,
  tari: 300,
  maintenance_pct: 0.01,
  insurance: 400,
  condo_fees_monthly: 50,
  electricity_monthly: 60,
  gas_monthly: 50,
  water_monthly: 20,
  internet_monthly: 30,
  accountant_fee_annual: 400,
};

function App() {
  const [selectedZone, setSelectedZone] = useState(null);
  const [zoneOverrides, setZoneOverrides] = useState({});

  return (
    <div className="app">
      <header className="app-header">
        <h1>Italy Real Estate Finder</h1>
      </header>
      <main className="app-main">
        <div className="panel panel-left">
          <ZoneExplorer
            onSelectZone={setSelectedZone}
            zoneOverrides={zoneOverrides}
            defaultParams={defaultParams}
          />
        </div>
        <div className="panel panel-right">
          <AnalysisPanel
            zone={selectedZone}
            zoneOverrides={zoneOverrides}
            setZoneOverrides={setZoneOverrides}
            defaultParams={defaultParams}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
