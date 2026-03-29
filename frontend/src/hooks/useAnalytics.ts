import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { PassRateTrend, FlakyTest, ErrorBreakdown } from '../types';

export function usePassRateTrend(projectId: string, days = 30, branch?: string) {
  return useQuery<PassRateTrend[]>({
    queryKey: ['pass-rate-trend', projectId, days, branch],
    queryFn: async () => {
      const { data } = await api.get('/analytics/pass-rate-trend', {
        params: { project_id: projectId, days, branch },
      });
      return data;
    },
    enabled: !!projectId,
    refetchInterval: 30_000,
  });
}

export function useFlakyTests(projectId: string, limit = 20) {
  return useQuery<FlakyTest[]>({
    queryKey: ['flaky-tests', projectId, limit],
    queryFn: async () => {
      const { data } = await api.get('/analytics/flaky-tests', {
        params: { project_id: projectId, limit },
      });
      return data;
    },
    enabled: !!projectId,
  });
}

export function useErrorBreakdown(projectId: string, days = 14) {
  return useQuery<ErrorBreakdown[]>({
    queryKey: ['error-breakdown', projectId, days],
    queryFn: async () => {
      const { data } = await api.get('/analytics/error-breakdown', {
        params: { project_id: projectId, days },
      });
      return data;
    },
    enabled: !!projectId,
  });
}

export function useRuns(projectId: string, filters?: {
  branch?: string;
  tool?: string;
  environment?: string;
}) {
  return useQuery({
    queryKey: ['runs', projectId, filters],
    queryFn: async () => {
      const { data } = await api.get('/runs', {
        params: { project_id: projectId, ...filters },
      });
      return data;
    },
    enabled: !!projectId,
    refetchInterval: 15_000,
  });
}

export function useRunResults(runId: string, filters?: {
  status?: string;
  search?: string;
}) {
  return useQuery({
    queryKey: ['run-results', runId, filters],
    queryFn: async () => {
      const { data } = await api.get(`/runs/${runId}/results`, {
        params: filters,
      });
      return data;
    },
    enabled: !!runId,
  });
}
