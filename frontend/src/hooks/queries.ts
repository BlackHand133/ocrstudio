import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export const useConfig = () =>
  useQuery({ queryKey: ['config'], queryFn: api.getConfig });

/**
 * Live OCR engine state. Only polled while the settings dialog is open, since
 * the answer only changes when the engine is (re)built.
 */
export const useEngineStatus = (enabled: boolean) =>
  useQuery({
    queryKey: ['engineStatus'],
    queryFn: api.getEngineStatus,
    enabled,
    refetchOnWindowFocus: false,
  });

export const useWorkspaces = () =>
  useQuery({ queryKey: ['workspaces'], queryFn: api.listWorkspaces });

export const useWorkspace = (id: string | null) =>
  useQuery({
    queryKey: ['workspace', id],
    queryFn: () => api.getWorkspace(id!),
    enabled: !!id,
  });

export const useImages = (ws: string | null) =>
  useQuery({
    queryKey: ['images', ws],
    queryFn: () => api.listImages(ws!),
    enabled: !!ws,
  });

export const useMissing = (ws: string | null) =>
  useQuery({
    queryKey: ['missing', ws],
    queryFn: () => api.missingImages(ws!),
    enabled: !!ws,
  });
