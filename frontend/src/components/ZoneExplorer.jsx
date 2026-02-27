import { useState, useEffect, useCallback } from 'react';
import { getZones, startSampling, getSamplingStatus, stopSampling } from '../api';
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
  const [samplingStatus, setSamplingStatus] = useState(null);
  const [samplingError, setSamplingError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getZones(filters)
      .then(setZones)
      .catch(() => setZones([]))
      .finally(() => setLoading(false));
  }, [filters]);

  // Poll sampling status when active
  useEffect(() => {
    getSamplingStatus().then(setSamplingStatus).catch(() => {});
  }, []);

  useEffect(() => {
    if (!samplingStatus?.active) return;
    const interval = setInterval(() => {
      getSamplingStatus()
        .then((s) => {
          setSamplingStatus(s);
          // Refresh zones when sampling completes to pick up new has_str_data flags
          if (!s.active) {
            getZones(filters).then(setZones).catch(() => {});
          }
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [samplingStatus?.active, filters]);

  const handleStartSampling = useCallback(() => {
    setSamplingError(null);
    startSampling({ province: filters.province, region: filters.region })
      .then((result) => {
        setSamplingStatus((s) => ({ ...s, active: true, zones_queued: result.zones_queued }));
      })
      .catch((err) => setSamplingError(err.message));
  }, [filters.province, filters.region]);

  const handleStopSampling = useCallback(() => {
    stopSampling().then(() => setSamplingStatus((s) => ({ ...s, active: false }))).catch(() => {});
  }, []);

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

      <div className="sampling-controls">
        {samplingStatus && (
          <span className="sampling-progress">
            STR sampled: {samplingStatus.sampled}/{samplingStatus.total} zones
            {samplingStatus.active && ' (running…)'}
          </span>
        )}
        {samplingStatus?.active ? (
          <button className="btn-stop" onClick={handleStopSampling}>Stop Sampling</button>
        ) : (
          <button
            className="btn-sample"
            onClick={handleStartSampling}
            disabled={!filters.province && !filters.region}
            title={!filters.province && !filters.region ? 'Select a region or province first' : 'Sample Airbnb data for visible zones'}
          >
            Sample Airbnb Data
          </button>
        )}
        {samplingError && <span className="sampling-error">{samplingError}</span>}
      </div>

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
