// ABOUTME: Filter controls for OMI zone exploration.
// ABOUTME: Region/province dropdowns and price range inputs that drive zone queries.

import { useState, useEffect } from 'react';
import { getRegions, getProvinces } from '../api';

export function ZoneFilters({ filters, onChange }) {
  const [regions, setRegions] = useState([]);
  const [provinces, setProvinces] = useState([]);

  useEffect(() => {
    getRegions().then(setRegions).catch(() => {});
  }, []);

  useEffect(() => {
    if (filters.region) {
      getProvinces(filters.region).then(setProvinces).catch(() => {});
    } else {
      setProvinces([]);
    }
  }, [filters.region]);

  const update = (key, value) => {
    onChange({ ...filters, [key]: value || undefined });
  };

  return (
    <div className="zone-filters">
      <select
        value={filters.region || ''}
        onChange={(e) => {
          update('region', e.target.value);
          update('province', undefined);
        }}
      >
        <option value="">All Regions</option>
        {regions.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>

      <select
        value={filters.province || ''}
        onChange={(e) => update('province', e.target.value)}
        disabled={!filters.region}
      >
        <option value="">All Provinces</option>
        {provinces.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      <input
        type="number"
        placeholder="Max price/sqm"
        value={filters.maxPrice || ''}
        onChange={(e) => update('maxPrice', e.target.value)}
      />

      <input
        type="number"
        placeholder="Min rent/sqm"
        step="0.5"
        value={filters.minRent || ''}
        onChange={(e) => update('minRent', e.target.value)}
      />
    </div>
  );
}
