import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { drafts as draftsApi } from '../lib/api';
import type { DraftEdit } from '../types/api';

export function useDrafts(status = 'pending_approval') {
  return useQuery({
    queryKey: ['drafts', status],
    queryFn: () => draftsApi.list(status),
  });
}

export function useDraft(id: string) {
  return useQuery({
    queryKey: ['drafts', 'detail', id],
    queryFn: () => draftsApi.get(id),
    enabled: !!id,
  });
}

export function useApproveDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => draftsApi.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['drafts'] });
    },
  });
}

export function useEditSendDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DraftEdit }) =>
      draftsApi.editSend(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['drafts'] });
    },
  });
}

export function useDiscardDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => draftsApi.discard(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['drafts'] });
    },
  });
}
