import { api } from '@/shared/api/client';
import type { ManagerTable, TableInfo, TableSession, TableSessionSettlement, UserRole } from '@/shared/api/types';

export type TableStatus = ManagerTable['status'];

const managerRole = (role?: UserRole) => role ?? 'manager';

export const tableApi = {
  getManagerTables: (role?: UserRole): Promise<ManagerTable[]> => api.managerTables(managerRole(role)),
  createTable: (role: UserRole | undefined, status: TableStatus): Promise<ManagerTable> =>
    api.managerCreateTable(managerRole(role), { status }),
  updateTable: (role: UserRole | undefined, tableId: number, status: TableStatus): Promise<ManagerTable> =>
    api.managerUpdateTable(managerRole(role), tableId, { status }),
  deleteTable: (role: UserRole | undefined, tableId: number): Promise<void> =>
    api.managerDeleteTable(managerRole(role), tableId),
  settleTableSession: (
    role: UserRole | undefined,
    tableId: number,
    amountReceived?: number
  ): Promise<TableSessionSettlement> => api.managerSettleTableSession(managerRole(role), tableId, amountReceived),
  getPublicTables: (): Promise<TableInfo[]> => api.publicTables(),
  getPublicTableSession: (tableId: number): Promise<TableSession> => api.publicTableSession(tableId),
};
