import { api } from '@/shared/api/client';
import type { DeliveryDriver, UserRole } from '@/shared/api/types';

export interface CreateDriverPayload {
  user_id?: number | null;
  name: string;
  provider_id?: number | null;
  phone: string;
  vehicle?: string | null;
  active: boolean;
}

export interface UpdateDriverPayload {
  provider_id?: number | null;
  name: string;
  phone: string;
  vehicle?: string | null;
  active: boolean;
  status: 'available' | 'busy' | 'inactive';
}

const managerRole = (role?: UserRole) => role ?? 'manager';

export const driverApi = {
  getDrivers: (role?: UserRole): Promise<DeliveryDriver[]> => api.managerDrivers(managerRole(role)),
  createDriver: (role: UserRole | undefined, payload: CreateDriverPayload): Promise<DeliveryDriver> =>
    api.managerCreateDriver(managerRole(role), payload),
  updateDriver: (role: UserRole | undefined, driverId: number, payload: UpdateDriverPayload): Promise<DeliveryDriver> =>
    api.managerUpdateDriver(managerRole(role), driverId, payload),
};
