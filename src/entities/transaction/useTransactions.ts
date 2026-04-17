import { useQuery } from '@tanstack/react-query';

import type { UserRole } from '@/shared/api/types';
import type { CashboxMovement, DeliverySettlement, FinancialTransaction, ShiftClosure } from './transaction.types';
import { transactionApi } from './transaction.api';

export function useFinancialTransactions(role: UserRole | undefined, enabled = true) {
  return useQuery<FinancialTransaction[]>({
    queryKey: ['manager-financial-transactions'],
    queryFn: () => transactionApi.getFinancialTransactions(role),
    enabled,
  });
}

export function useDeliverySettlements(role: UserRole | undefined, enabled = true) {
  return useQuery<DeliverySettlement[]>({
    queryKey: ['manager-delivery-settlements'],
    queryFn: () => transactionApi.getDeliverySettlements(role),
    enabled,
  });
}

export function useCashboxMovements(role: UserRole | undefined, enabled = true) {
  return useQuery<CashboxMovement[]>({
    queryKey: ['manager-cashbox-movements'],
    queryFn: () => transactionApi.getCashboxMovements(role),
    enabled,
  });
}

export function useShiftClosures(role: UserRole | undefined, enabled = true) {
  return useQuery<ShiftClosure[]>({
    queryKey: ['manager-shift-closures'],
    queryFn: () => transactionApi.getShiftClosures(role),
    enabled,
  });
}
