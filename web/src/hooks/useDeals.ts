import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deals as dealsApi } from '../lib/api';
import type { DealCreate, DealUpdate, StageUpdate, Deal } from '../types/api';

export function useDeals() {
  return useQuery({ queryKey: ['deals'], queryFn: dealsApi.list });
}

export function useDeal(id: string) {
  return useQuery({
    queryKey: ['deals', id],
    queryFn: () => dealsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DealCreate) => dealsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deals'] }),
  });
}

export function useUpdateDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DealUpdate }) =>
      dealsApi.update(id, data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['deals'] });
      qc.invalidateQueries({ queryKey: ['deals', vars.id] });
    },
  });
}

export function useUpdateStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: StageUpdate }) =>
      dealsApi.updateStage(id, data),
    /** Optimistic update: move card immediately in the cache */
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey: ['deals'] });
      const prev = qc.getQueryData<Deal[]>(['deals']);
      qc.setQueryData<Deal[]>(['deals'], (old) =>
        old?.map((d) => (d.id === id ? { ...d, stage: data.new_stage } : d)),
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(['deals'], ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['deals'] }),
  });
}
