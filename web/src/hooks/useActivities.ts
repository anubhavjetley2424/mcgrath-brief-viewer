import { useQuery } from '@tanstack/react-query';
import { activities as activitiesApi } from '../lib/api';

export function useActivities(params?: { deal_id?: string; limit?: number }) {
  return useQuery({
    queryKey: ['activities', params],
    queryFn: () => activitiesApi.list(params),
  });
}
