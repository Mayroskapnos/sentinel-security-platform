import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../api/client";

export function useHealth() {
  return useQuery({
    queryKey: ["system-health"],
    queryFn: getHealth,
    refetchInterval: 10_000,
    retry: 2,
  });
}
