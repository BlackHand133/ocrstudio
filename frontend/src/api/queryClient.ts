import { QueryClient } from '@tanstack/react-query';

// Single QueryClient shared by the provider (main.tsx) and the imperative
// controller (controller.ts) so both read/write the same cache.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
