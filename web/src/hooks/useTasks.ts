import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasks as tasksApi } from '../lib/api';
import type { TaskCreate, TaskUpdate, Task } from '../types/api';

export function useTasks(params?: { deal_id?: string; status?: string }) {
  return useQuery({
    queryKey: ['tasks', params],
    queryFn: () => tasksApi.list(params),
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) => tasksApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });
}

export function useUpdateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaskUpdate }) =>
      tasksApi.update(id, data),
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey: ['tasks'] });
      const queries = qc.getQueriesData<Task[]>({ queryKey: ['tasks'] });
      queries.forEach(([key, old]) => {
        if (old) {
          qc.setQueryData<Task[]>(key, old.map((t) =>
            t.id === id
              ? { ...t, ...data, completed_at: data.status === 'done' ? new Date().toISOString() : null }
              : t,
          ));
        }
      });
      return { queries };
    },
    onError: (_err, _vars, ctx) => {
      ctx?.queries.forEach(([key, old]) => {
        if (old) qc.setQueryData(key, old);
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });
}
