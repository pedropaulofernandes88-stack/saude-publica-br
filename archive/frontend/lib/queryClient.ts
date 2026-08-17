"use client";

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Dados do SUS são atualizados mensalmente — cache longo
      staleTime: 1000 * 60 * 10,       // 10 min
      gcTime: 1000 * 60 * 60,          // 1 hora
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});
