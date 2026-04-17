import { useQuery } from '@tanstack/react-query';

import type { UserRole } from '@/shared/api/types';
import type { ManagerTable, TableInfo, TableSession } from './table.types';
import { tableApi } from './table.api';

export function useManagerTables(role: UserRole | undefined, enabled = true) {
  return useQuery<ManagerTable[]>({
    queryKey: ['manager-tables'],
    queryFn: () => tableApi.getManagerTables(role),
    enabled,
  });
}

export function usePublicTables(enabled = true) {
  return useQuery<TableInfo[]>({
    queryKey: ['public-tables'],
    queryFn: () => tableApi.getPublicTables(),
    enabled,
  });
}

export function usePublicTableSession(tableId: number | null | undefined, enabled = true) {
  return useQuery<TableSession>({
    queryKey: ['public-table-session', tableId ?? 0],
    queryFn: () => tableApi.getPublicTableSession(tableId ?? 0),
    enabled: enabled && typeof tableId === 'number' && tableId > 0,
  });
}
