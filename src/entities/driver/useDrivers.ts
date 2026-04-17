import { useQuery } from '@tanstack/react-query';

import type { UserRole } from '@/shared/api/types';
import type { DeliveryDriver } from './driver.types';
import { driverApi } from './driver.api';

export function useDrivers(role: UserRole | undefined, enabled = true) {
  return useQuery<DeliveryDriver[]>({
    queryKey: ['manager-drivers'],
    queryFn: () => driverApi.getDrivers(role),
    enabled,
  });
}
