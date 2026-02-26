// ABOUTME: Filterable, sortable table of OMI zones with computed gross yield.
// ABOUTME: Selecting a zone passes it to the analysis panel for ROI calculation.

import { useState, useEffect } from 'react';
import { getZones } from '../api';
import { ZoneFilters } from './ZoneFilters';

function grossYield(zone) {
  if (!zone.rent_min || !zone.buy_min || zone.buy_min === 0) return null;
  // Annualized rent / buy price (both per sqm)
  return ((zone.rent_min * 12) / zone.buy_min) * 100;
}

export function ZoneExplorer({ onSelectZone }) {
  const [filters, setFilters] = useState({});
  const [zones, setZones] = useState([]);
  const [sortKey, setSortKey] = useState('buy_min');
  const [sortAsc, setSortAsc] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getZones(filters)
      .then(setZones)
      .catch(() => setZones([]))
      .finally(() => setLoading(false));
  }, [filters]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sorted = [...zones].sort((a, b) => {
    let aVal = sortKey === 'yield' ? grossYield(a) : a[sortKey];
    let bVal = sortKey === 'yield' ? grossYield(b) : b[sortKey];
    aVal = aVal ?? -Infinity;
    bVal = bVal ?? -Infinity;
    return sortAsc ? aVal - bVal : bVal - aVal;
  });

  const SortHeader = ({ label, field }) => (
    <th onClick={() => handleSort(field)} style={{ cursor: 'pointer' }}>
      {label} {sortKey === field ? (sortAsc ? '↑' : '↓') : ''}
    </th>
  );

  return (
    <div className="zone-explorer">
      <h2>OMI Zones</h2>
      <ZoneFilters filters={filters} onChange={setFilters} />
      {loading ? (
        <p className="loading">Loading zones...</p>
      ) : (
        <>
          <p className="zone-count">{zones.length} zones found</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Region</th>
                  <th>Province</th>
                  <th>Comune</th>
                  <th>Zone</th>
                  <SortHeader label="Buy Min" field="buy_min" />
                  <SortHeader label="Buy Max" field="buy_max" />
                  <SortHeader label="Rent Min" field="rent_min" />
                  <SortHeader label="Rent Max" field="rent_max" />
                  <SortHeader label="Yield %" field="yield" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((z, i) => {
                  const yld = grossYield(z);
                  return (
                    <tr
                      key={i}
                      onClick={() => onSelectZone(z)}
                      className="zone-row"
                    >
                      <td>{z.region}</td>
                      <td>{z.province}</td>
                      <td>{z.comune_name}</td>
                      <td title={z.zona_desc}>{z.zona}</td>
                      <td>€{z.buy_min?.toFixed(0)}</td>
                      <td>€{z.buy_max?.toFixed(0)}</td>
                      <td>€{z.rent_min?.toFixed(2)}</td>
                      <td>€{z.rent_max?.toFixed(2)}</td>
                      <td className={yld > 5 ? 'yield-good' : ''}>
                        {yld ? yld.toFixed(1) + '%' : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
