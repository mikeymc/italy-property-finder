// ABOUTME: ROI calculator with editable sliders for a selected OMI zone.
// ABOUTME: Computes financial analysis via the API and displays results.

import { useState, useEffect } from 'react';
import { getAnalysis } from '../api';
import { FinancialSummary } from './FinancialSummary';
import { AirbnbListings } from './AirbnbListings';

export function AnalysisPanel({ zone }) {
  const [params, setParams] = useState({
    purchase_price: 100000,
    square_meters: 60,
    nightly_rate: 80,
    occupancy_rate: 0.6,
    down_payment_pct: 0.2,
    management_fee_pct: 0.2,
    platform_fee_pct: 0.15,
    cleaning_fee: 50,
    avg_stay_nights: 4,
  });
  const [analysis, setAnalysis] = useState(null);

  // When a zone is selected, pre-fill price from OMI data
  useEffect(() => {
    if (zone) {
      const avgBuy = ((zone.buy_min || 0) + (zone.buy_max || 0)) / 2;
      setParams((p) => ({
        ...p,
        purchase_price: Math.round(avgBuy * p.square_meters),
      }));
    }
  }, [zone]);

  useEffect(() => {
    getAnalysis(params)
      .then(setAnalysis)
      .catch(() => setAnalysis(null));
  }, [params]);

  const update = (key, value) => {
    setParams((p) => ({ ...p, [key]: parseFloat(value) || 0 }));
  };

  const sliders = [
    { key: 'purchase_price', label: 'Purchase Price (€)', min: 20000, max: 1000000, step: 5000 },
    { key: 'square_meters', label: 'Size (sqm)', min: 20, max: 200, step: 5 },
    { key: 'nightly_rate', label: 'Nightly Rate (€)', min: 20, max: 500, step: 5 },
    { key: 'occupancy_rate', label: 'Occupancy Rate', min: 0.1, max: 0.95, step: 0.05 },
    { key: 'down_payment_pct', label: 'Down Payment %', min: 0.1, max: 1.0, step: 0.05 },
    { key: 'management_fee_pct', label: 'Mgmt Fee %', min: 0, max: 0.3, step: 0.05 },
  ];

  const query = zone ? `${zone.comune_name}, Italy` : null;

  return (
    <div className="analysis-panel">
      <h2>Investment Analysis</h2>
      {zone && (
        <p className="zone-label">
          {zone.comune_name} ({zone.province}) — Zone {zone.zona}
        </p>
      )}

      <div className="sliders">
        {sliders.map(({ key, label, min, max, step }) => (
          <div key={key} className="slider-row">
            <label>{label}</label>
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={params[key]}
              onChange={(e) => update(key, e.target.value)}
            />
            <span className="slider-value">
              {key.includes('pct') || key === 'occupancy_rate'
                ? `${(params[key] * 100).toFixed(0)}%`
                : key === 'square_meters'
                  ? `${params[key]} sqm`
                  : `€${params[key].toLocaleString()}`}
            </span>
          </div>
        ))}
      </div>

      <FinancialSummary analysis={analysis} />

      {query && <AirbnbListings query={query} />}
    </div>
  );
}
