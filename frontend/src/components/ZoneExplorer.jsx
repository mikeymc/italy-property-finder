import { useState, useEffect } from 'react';
import { getZones } from '../api';
import { ZoneFilters } from './ZoneFilters';
import { ZoneMap } from './ZoneMap';

export function grossYield(zone) {
  if (!zone.rent_min || !zone.buy_min || zone.buy_min === 0) return null;
  // Annualized rent / buy price (both per sqm)
  return ((zone.rent_min * 12) / zone.buy_min) * 100;
}

export function ZoneExplorer({ onSelectZone }) {
  const [filters, setFilters] = useState({});
  const [zones, setZones] = useState([]);
  const [sortKey, setSortKey] = useState('yield');
  const [sortAsc, setSortAsc] = useState(false);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('map'); // 'map' or 'table'

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
    <div className="zone-explorer" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>OMI Zones</h2>
        <div className="view-toggle">
          <button
            onClick={() => setViewMode('table')}
            className={viewMode === 'table' ? 'active' : ''}
          >
            Table View
          </button>
          <button
            onClick={() => setViewMode('map')}
            className={viewMode === 'map' ? 'active' : ''}
          >
            Map View
          </button>
        </div>
      </div>
      <ZoneFilters filters={filters} onChange={setFilters} />

      {loading ? (
        <p className="loading">Loading zones...</p>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <p className="zone-count">{zones.length} zones loaded</p>

          {viewMode === 'map' ? (
            <div style={{ flex: 1, position: 'relative', minHeight: '600px' }}>
              <ZoneMap zonesForLookup={zones} onSelectZone={onSelectZone} />
            </div>
          ) : (
            <div className="table-wrap" style={{ flex: 1, overflowY: 'auto' }}>
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
          )}
        </div>
      )}
    </div>
  );
}
