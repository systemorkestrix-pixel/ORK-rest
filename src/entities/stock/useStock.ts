import { useQuery } from '@tanstack/react-query';

import type { UserRole } from '@/shared/api/types';
import type {
  WarehouseDashboard,
  WarehouseItem,
  WarehouseLedgerRow,
  WarehouseStockBalance,
  WarehouseSupplier,
} from './stock.types';
import { stockApi, type WarehouseLedgerParams } from './stock.api';

export function useWarehouseDashboard(role: UserRole | undefined, enabled = true) {
  return useQuery<WarehouseDashboard>({
    queryKey: ['manager-warehouse-dashboard'],
    queryFn: () => stockApi.getDashboard(role),
    enabled,
  });
}

export function useWarehouseSuppliers(role: UserRole | undefined, enabled = true) {
  return useQuery<WarehouseSupplier[]>({
    queryKey: ['manager-warehouse-suppliers'],
    queryFn: () => stockApi.getSuppliers(role),
    enabled,
  });
}

export function useWarehouseItems(role: UserRole | undefined, enabled = true) {
  return useQuery<WarehouseItem[]>({
    queryKey: ['manager-warehouse-items'],
    queryFn: () => stockApi.getItems(role),
    enabled,
  });
}

export function useWarehouseBalances(role: UserRole | undefined, onlyLow = false, enabled = true) {
  return useQuery<WarehouseStockBalance[]>({
    queryKey: ['manager-warehouse-balances', onlyLow],
    queryFn: () => stockApi.getBalances(role, onlyLow),
    enabled,
  });
}

export function useWarehouseLedger(role: UserRole | undefined, params?: WarehouseLedgerParams, enabled = true) {
  return useQuery<WarehouseLedgerRow[]>({
    queryKey: ['manager-warehouse-ledger', params?.limit ?? 200, params?.itemId ?? 0, params?.movementKind ?? 'all'],
    queryFn: () => stockApi.getLedger(role, params),
    enabled,
  });
}
