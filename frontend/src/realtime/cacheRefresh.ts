import { queryKeys } from "../hooks/useCoreData";

export function shouldRefreshAuthoritativeState(hasConnectedBefore: boolean) {
  return hasConnectedBefore;
}

export function authoritativeRefreshQueryKeys() {
  return [
    queryKeys.events.all,
    queryKeys.alerts.all,
    queryKeys.dashboard.all,
    queryKeys.assets.all,
    queryKeys.simulator.all,
    queryKeys.network.all,
  ] as const;
}
