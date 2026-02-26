// ABOUTME: Hook that polls a scrape job status until completion or failure.
// ABOUTME: Returns job state and triggers callback with results when done.

import { useState, useEffect, useRef } from 'react';
import { getScrapeStatus } from '../api';

const POLL_INTERVAL_MS = 3000;

export function useScrapeJob(jobId) {
  const [job, setJob] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }

    const poll = async () => {
      try {
        const data = await getScrapeStatus(jobId);
        setJob(data);
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(intervalRef.current);
        }
      } catch {
        clearInterval(intervalRef.current);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => clearInterval(intervalRef.current);
  }, [jobId]);

  return job;
}
