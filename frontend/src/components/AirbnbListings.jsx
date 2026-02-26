// ABOUTME: Airbnb scrape trigger and listing cards for a given location.
// ABOUTME: Manages scrape jobs via polling and displays cached results.

import { useState, useEffect } from 'react';
import { startScrape, getAirbnbListings } from '../api';
import { useScrapeJob } from '../hooks/useScrapeJob';

export function AirbnbListings({ query }) {
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
        .catch(() => {});
    }
  }, [job?.status, query]);

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
          {listings.map((l) => (
            <div key={l.id} className="listing-card">
              <div className="listing-header">
                <strong>{l.title || l.name}</strong>
                {l.is_guest_favorite ? <span className="badge">Guest Favorite</span> : null}
              </div>
              <div className="listing-details">
                {l.nightly_rate && <span>€{l.nightly_rate.toFixed(0)}/night</span>}
                {l.bedrooms && <span>{l.bedrooms} bed</span>}
                {l.rating && <span>{l.rating} ({l.review_count})</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
