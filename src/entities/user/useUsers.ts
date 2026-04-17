import { useQuery } from '@tanstack/react-query';

import type { UserRole } from '@/shared/api/types';
import type { User } from './user.types';
import { userApi } from './user.api';

export function useUsers(role: UserRole | undefined, enabled = true) {
  return useQuery<User[]>({
    queryKey: ['manager-users'],
    queryFn: () => userApi.getUsers(role),
    enabled,
  });
}
