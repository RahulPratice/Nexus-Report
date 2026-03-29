import { useEffect, useRef, useState } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export interface LiveEvent {
  event: string;
  run_id?: string;
  total?: number;
  passed?: number;
  failed?: number;
  pass_rate?: number;
  test?: {
    id: string;
    name: string;
    suite: string;
    status: string;
    duration_ms: number;
    error_message?: string;
  };
}

export function useLiveRun(runId: string | null) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) return;

    const ws = new WebSocket(`${WS_URL}/ws/live/${runId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (e) => {
      try {
        const event: LiveEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);
      } catch {
        // ignore malformed messages
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [runId]);

  const clear = () => setEvents([]);

  return { events, connected, clear };
}

export function useProjectFeed(projectId: string | null) {
  const [latestEvent, setLatestEvent] = useState<LiveEvent | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!projectId) return;

    const ws = new WebSocket(`${WS_URL}/ws/project/${projectId}`);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      try {
        setLatestEvent(JSON.parse(e.data));
      } catch {}
    };

    return () => ws.close();
  }, [projectId]);

  return { latestEvent, connected };
}
