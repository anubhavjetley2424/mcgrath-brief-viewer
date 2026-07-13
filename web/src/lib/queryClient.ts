import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,       // 15s before refetch
      refetchInterval: 30_000, // auto-poll every 30s
      retry: 2,
    },
    mutations: {
      retry: 1,
    },
  },
});
