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
  });
  const [analysis, setAnalysis] = useState(null);

  // When a zone is selected, pre-fill price from OMI data and nightly rate from STR metrics
  useEffect(() => {
    if (zone) {
      const avgBuy = ((zone.buy_min || 0) + (zone.buy_max || 0)) / 2;
      setParams((p) => ({
        ...p,
        purchase_price: Math.round(avgBuy * p.square_meters),
        // Use sampled median nightly rate if available, otherwise keep current value
        ...(zone.median_nightly_rate ? { nightly_rate: Math.round(zone.median_nightly_rate) } : {}),
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

  const renderSlider = ({ key, label, min, max, step }) => (
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
        {key.includes('pct') || key === 'occupancy_rate' || key === 'mutuo_rate' || key === 'registro_pct'
          ? `${(params[key] * 100).toFixed(key === 'mutuo_rate' || key === 'mutuo_tax_pct' || key === 'maintenance_pct' ? 2 : 0)}%`
          : key === 'square_meters'
            ? `${params[key]} sqm`
            : key === 'mutuo_term' || key === 'avg_stay_nights'
              ? `${params[key]} yrs/nts`
              : `€${params[key].toLocaleString()}`}
      </span>
    </div>
  );

  const mainSliders = [
    { key: 'purchase_price', label: 'Purchase Price (€)', min: 20000, max: 1000000, step: 5000 },
    { key: 'square_meters', label: 'Size (sqm)', min: 20, max: 200, step: 5 },
    { key: 'down_payment_pct', label: 'Down Payment %', min: 0.1, max: 1.0, step: 0.05 },
    { key: 'mutuo_rate', label: 'Mutuo Rate %', min: 0.01, max: 0.10, step: 0.005 },
    { key: 'mutuo_term', label: 'Mutuo Term (yrs)', min: 5, max: 30, step: 1 },
  ];

  const strSliders = [
    { key: 'nightly_rate', label: 'Nightly Rate (€)', min: 20, max: 500, step: 5 },
    { key: 'occupancy_rate', label: 'Occupancy Rate', min: 0.1, max: 0.95, step: 0.05 },
    { key: 'management_fee_pct', label: 'Mgmt Fee %', min: 0, max: 0.3, step: 0.05 },
    { key: 'cleaning_fee', label: 'Cleaning Fee (€)', min: 20, max: 150, step: 5 },
    { key: 'avg_stay_nights', label: 'Avg Stay (nights)', min: 1, max: 14, step: 1 },
  ];

  const acqSliders = [
    { key: 'registro_pct', label: 'Registro Tax %', min: 0.02, max: 0.09, step: 0.07 },
    { key: 'agency_fee_pct', label: 'Agency Fee %', min: 0.0, max: 0.06, step: 0.01 },
    { key: 'notary_purchase_fee', label: 'Notary (Purchase) (€)', min: 500, max: 5000, step: 100 },
    { key: 'notary_mutuo_fee', label: 'Notary (Mutuo) (€)', min: 0, max: 3000, step: 100 },
    { key: 'bank_origination_fee', label: 'Bank Origination (€)', min: 0, max: 2000, step: 100 },
    { key: 'technical_report_fee', label: 'Tech Report (€)', min: 0, max: 1500, step: 100 },
  ];

  const annualSliders = [
    { key: 'imu', label: 'IMU (€/yr)', min: 0, max: 3000, step: 100 },
    { key: 'tari', label: 'TARI (€/yr)', min: 100, max: 1000, step: 50 },
    { key: 'condo_fees_monthly', label: 'Condo Fee (€/mo)', min: 0, max: 500, step: 10 },
    { key: 'insurance', label: 'Insurance (€/yr)', min: 0, max: 1000, step: 50 },
    { key: 'accountant_fee_annual', label: 'Accountant (€/yr)', min: 0, max: 1000, step: 50 },
    { key: 'electricity_monthly', label: 'Electricity (€/mo)', min: 20, max: 300, step: 10 },
    { key: 'gas_monthly', label: 'Gas (€/mo)', min: 0, max: 200, step: 10 },
    { key: 'internet_monthly', label: 'Internet (€/mo)', min: 0, max: 100, step: 5 },
  ];

  const query = zone ? `${zone.comune_name}, Italy` : null;

  return (
    <div className="analysis-panel">
      <h2>Investment Analysis</h2>
      {zone && (
        <p className="zone-label">
          {zone.comune_name} ({zone.province}) — Zone {zone.zona}
          {zone.has_str_data && (
            <span className="str-badge sampled">● Sampled STR data</span>
          )}
          {zone && !zone.has_str_data && (
            <span className="str-badge estimated">○ Estimated</span>
          )}
        </p>
      )}

      <div className="sliders-container">
        <div className="sliders-section">
          <div className="section-header-inline">
            <h3>Property & Loan</h3>
            {analysis && (
              <span className="header-summary">
                €{(params.purchase_price / params.square_meters).toFixed(0)}/sqm,
                €{(params.purchase_price / (params.square_meters * 10.7639)).toFixed(0)}/sqft
              </span>
            )}
          </div>
          <div className="sliders">
            {mainSliders.map(renderSlider)}
          </div>
        </div>

        <div className="sliders-section">
          <div className="section-header-inline">
            <h3>Acquisition Costs</h3>
            {analysis && (
              <span className="header-summary">
                €{analysis.total_acquisition_cost.toLocaleString()}
              </span>
            )}
          </div>
          <div className="sliders">
            {acqSliders.map(renderSlider)}
          </div>
        </div>

        <div className="sliders-section">
          <div className="section-header-inline">
            <h3>Annual & Monthly Costs</h3>
            {analysis && (
              <span className="header-summary">
                €{analysis.annual_expenses.toLocaleString()}/yr,
                €{(analysis.annual_expenses / 12).toLocaleString(undefined, { maximumFractionDigits: 0 })}/mo
              </span>
            )}
          </div>
          <div className="sliders">
            {annualSliders.map(renderSlider)}
          </div>
        </div>

        <div className="sliders-section">
          <div className="section-header-inline">
            <h3>STR Estimates</h3>
            {analysis && (
              <span className="header-summary">
                €{analysis.gross_rental_income.toLocaleString()}/yr
              </span>
            )}
          </div>
          <div className="sliders">
            {strSliders.map(renderSlider)}
          </div>
        </div>
      </div>

      <FinancialSummary analysis={analysis} />

      {query && <AirbnbListings query={query} />}
    </div>
  );
}
