// ABOUTME: Airbnb scrape trigger and listing cards for a given location.
// ABOUTME: Manages scrape jobs via polling and displays cached results.

import { useState, useEffect } from 'react';
import { startScrape, getAirbnbListings } from '../api';
import { useScrapeJob } from '../hooks/useScrapeJob';

export function AirbnbListings({ query, onScrapeComplete }) {
  const [listings, setListings] = useState([]);
  const [jobId, setJobId] = useState(null);
  const [checkin, setCheckin] = useState('2025-07-01');
  const [checkout, setCheckout] = useState('2025-07-06');
  const job = useScrapeJob(jobId);

  // Load cached listings when query changes
  useEffect(() => {
    setJobId(null);
    getAirbnbListings(query)
      .then(setListings)
      .catch(() => setListings([]));
  }, [query]);

  // Reload listings when scrape completes
  useEffect(() => {
    if (job?.status === 'completed') {
      getAirbnbListings(query)
        .then(setListings)
        .catch(() => { });
      if (onScrapeComplete) {
        onScrapeComplete();
      }
    }
  }, [job?.status, query, onScrapeComplete]);

  const handleScrape = async () => {
    try {
      const { job_id } = await startScrape({ query, checkin, checkout });
      setJobId(job_id);
    } catch {
      // Scrape start failed
    }
  };

  const isRunning = job && (job.status === 'pending' || job.status === 'running');

  return (
    <div className="airbnb-section">
      <h3>Airbnb Listings</h3>

      <div className="scrape-controls">
        <input type="date" value={checkin} onChange={(e) => setCheckin(e.target.value)} />
        <input type="date" value={checkout} onChange={(e) => setCheckout(e.target.value)} />
        <button onClick={handleScrape} disabled={isRunning}>
          {isRunning ? 'Scraping...' : listings.length > 0 ? 'Re-scrape' : 'Scrape Airbnb'}
        </button>
      </div>

      {job?.status === 'failed' && (
        <p className="error">Scrape failed: {job.error}</p>
      )}
      {job?.status === 'completed' && (
        <p className="success">Found {job.result_count} listings</p>
      )}

      {listings.length > 0 && (
        <div className="listing-cards">
          {listings.map((l) => {
            const isExcluded = l.review_count == null || l.review_count < 3 || l.rating == null || l.rating < 4.85;
            return (
              <a key={l.id || l.listing_id} href={`https://www.airbnb.com/rooms/${l.listing_id}`} target="_blank" rel="noopener noreferrer" className={`listing-card ${isExcluded ? 'excluded' : ''}`} style={{ textDecoration: 'none', color: 'inherit', opacity: isExcluded ? 0.55 : 1 }}>
                <div className="listing-header">
                  <strong>{l.title || l.name}</strong>
                  {l.is_guest_favorite ? <span className="badge">Guest Favorite</span> : null}
                  {isExcluded ? <span className="badge badge-excluded" style={{ backgroundColor: '#666', color: '#fff', marginLeft: 'auto' }}>Not used in Yield</span> : null}
                </div>
                <div className="listing-details">
                  {l.nightly_rate && <span>€{l.nightly_rate.toFixed(0)}/night</span>}
                  {l.bedrooms != null && <span>{l.bedrooms} bed</span>}
                  {l.rating != null && <span>{l.rating} ({l.review_count})</span>}
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
