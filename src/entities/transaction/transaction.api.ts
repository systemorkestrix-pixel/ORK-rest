import { api } from '@/shared/api/client';
import type {
  CashboxMovement,
  DeliveryAccountingBackfillResult,
  DeliveryAccountingMigrationStatus,
  DeliverySettlement,
  FinancialTransaction,
  ShiftClosure,
  UserRole,
} from '@/shared/api/types';

export interface ShiftClosurePayload {
  opening_cash: number;
  actual_cash: number;
  note?: string | null;
}

export interface DeliveryAccountingBackfillPayload {
  limit?: number;
  dry_run?: boolean;
}

const managerRole = (role?: UserRole) => role ?? 'manager';

export const transactionApi = {
  getFinancialTransactions: (role?: UserRole): Promise<FinancialTransaction[]> =>
    api.managerFinancialTransactions(managerRole(role)),
  getDeliverySettlements: (role?: UserRole): Promise<DeliverySettlement[]> =>
    api.managerDeliverySettlements(managerRole(role)),
  getCashboxMovements: (role?: UserRole): Promise<CashboxMovement[]> =>
    api.managerCashboxMovements(managerRole(role)),
  getShiftClosures: (role?: UserRole): Promise<ShiftClosure[]> => api.managerShiftClosures(managerRole(role)),
  createShiftClosure: (role: UserRole | undefined, payload: ShiftClosurePayload): Promise<ShiftClosure> =>
    api.managerCreateShiftClosure(managerRole(role), payload),
  getDeliveryAccountingMigrationStatus: (role?: UserRole): Promise<DeliveryAccountingMigrationStatus> =>
    api.managerDeliveryAccountingMigrationStatus(managerRole(role)),
  runDeliveryAccountingBackfill: (
    role: UserRole | undefined,
    payload?: DeliveryAccountingBackfillPayload
  ): Promise<DeliveryAccountingBackfillResult> => api.managerRunDeliveryAccountingBackfill(managerRole(role), payload),
};
