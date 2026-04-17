import { api } from '@/shared/api/client';
import type { PermissionCatalogItem, User, UserPermissionsProfile, UserRole } from '@/shared/api/types';

export interface UserPayload {
  name: string;
  role: UserRole;
  active: boolean;
  username?: string;
  password?: string;
  delivery_phone?: string;
  delivery_vehicle?: string | null;
}

export interface UserPermissionsUpdatePayload {
  allow: string[];
  deny: string[];
}

const managerRole = (role?: UserRole) => role ?? 'manager';

export const userApi = {
  getUsers: (role?: UserRole): Promise<User[]> => api.managerUsers(managerRole(role)),
  getPermissionsCatalog: (role: UserRole | undefined, targetRole?: UserRole): Promise<PermissionCatalogItem[]> =>
    api.managerPermissionsCatalog(managerRole(role), targetRole),
  getUserPermissions: (role: UserRole | undefined, userId: number): Promise<UserPermissionsProfile> =>
    api.managerUserPermissions(managerRole(role), userId),
  updateUserPermissions: (
    role: UserRole | undefined,
    userId: number,
    payload: UserPermissionsUpdatePayload
  ): Promise<UserPermissionsProfile> => api.managerUpdateUserPermissions(managerRole(role), userId, payload),
  createUser: (role: UserRole | undefined, payload: UserPayload): Promise<User> =>
    api.managerCreateUser(managerRole(role), payload),
  updateUser: (role: UserRole | undefined, userId: number, payload: UserPayload): Promise<User> =>
    api.managerUpdateUser(managerRole(role), userId, payload),
  deleteUser: (role: UserRole | undefined, userId: number): Promise<void> =>
    api.managerDeleteUser(managerRole(role), userId),
};
