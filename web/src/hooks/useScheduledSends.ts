import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scheduledSends as sendsApi } from '../lib/api';

export function useScheduledSends(params?: { deal_id?: string; status?: string }) {
  return useQuery({
    queryKey: ['scheduled-sends', params],
    queryFn: () => sendsApi.list(params),
  });
}

export function useCancelScheduledSend() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => sendsApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scheduled-sends'] }),
  });
}
