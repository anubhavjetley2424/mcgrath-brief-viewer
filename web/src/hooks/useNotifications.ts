import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications as notifApi } from '../lib/api';
import type { NotificationUpdate } from '../types/api';

export function useNotifications(status = 'unread') {
  return useQuery({
    queryKey: ['notifications', status],
    queryFn: () => notifApi.list(status),
    refetchInterval: 30_000,
  });
}

export function useUpdateNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: NotificationUpdate }) =>
      notifApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
}
