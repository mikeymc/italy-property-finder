// ABOUTME: Fetch wrappers for all backend API calls.
// ABOUTME: Handles JSON parsing and error responses for the zone explorer UI.

const BASE = '/api';

async function fetchJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(err.error || resp.statusText);
  }
  return resp.json();
}

export async function getZones({ region, province, maxPrice, minRent, q } = {}) {
  const params = new URLSearchParams();
  if (region) params.set('region', region);
  if (province) params.set('province', province);
  if (maxPrice) params.set('max_price', maxPrice);
  if (minRent) params.set('min_rent', minRent);
  if (q) params.set('q', q);
  return fetchJson(`${BASE}/zones?${params}`);
}

export async function getRegions() {
  return fetchJson(`${BASE}/zones/regions`);
}

export async function getProvinces(region) {
  return fetchJson(`${BASE}/zones/provinces?region=${encodeURIComponent(region)}`);
}

export async function getAnalysis(params) {
  const qs = new URLSearchParams(params);
  return fetchJson(`${BASE}/analysis?${qs}`);
}

export async function startScrape({ query, checkin, checkout }) {
  const resp = await fetch(`${BASE}/scrape/airbnb`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, checkin, checkout }),
  });
  if (!resp.ok) throw new Error('Failed to start scrape');
  return resp.json();
}

export async function getScrapeStatus(jobId) {
  return fetchJson(`${BASE}/scrape/airbnb/${jobId}`);
}

export async function getAirbnbListings(query) {
  return fetchJson(`${BASE}/airbnb-listings?query=${encodeURIComponent(query)}`);
}

export async function startSampling({ province, region } = {}) {
  const resp = await fetch(`${BASE}/sample/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ province, region }),
  });
  if (!resp.ok) throw new Error('Failed to start sampling');
  return resp.json();
}

export async function getSamplingStatus() {
  return fetchJson(`${BASE}/sample/status`);
}

export async function stopSampling() {
  const resp = await fetch(`${BASE}/sample/stop`, { method: 'POST' });
  if (!resp.ok) throw new Error('Failed to stop sampling');
  return resp.json();
}
