import { api } from '@/shared/api/client';
import type {
  UserRole,
  WarehouseDashboard,
  WarehouseInboundVoucher,
  WarehouseItem,
  WarehouseLedgerRow,
  WarehouseOutboundReason,
  WarehouseOutboundVoucher,
  WarehouseStockBalance,
  WarehouseStockCount,
  WarehouseSupplier,
} from '@/shared/api/types';

export interface WarehouseSupplierPayload {
  name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  payment_term_days: number;
  credit_limit?: number | null;
  quality_rating: number;
  lead_time_days: number;
  notes?: string | null;
  active: boolean;
  supplied_item_ids: number[];
}

export interface WarehouseItemPayload {
  name: string;
  unit: string;
  alert_threshold: number;
  active: boolean;
}

export interface WarehouseInboundVoucherPayload {
  supplier_id: number;
  reference_no?: string | null;
  note?: string | null;
  idempotency_key?: string | null;
  items: Array<{
    item_id: number;
    quantity: number;
    unit_cost: number;
  }>;
}

export interface WarehouseOutboundVoucherPayload {
  reason_code: string;
  reason_note?: string | null;
  note?: string | null;
  idempotency_key?: string | null;
  items: Array<{
    item_id: number;
    quantity: number;
  }>;
}

export interface WarehouseStockCountPayload {
  note?: string | null;
  idempotency_key?: string | null;
  items: Array<{
    item_id: number;
    counted_quantity: number;
  }>;
}

export interface WarehouseLedgerParams {
  limit?: number;
  itemId?: number;
  movementKind?: 'inbound' | 'outbound';
}

const managerRole = (role?: UserRole) => role ?? 'manager';

export const stockApi = {
  getDashboard: (role?: UserRole): Promise<WarehouseDashboard> => api.managerWarehouseDashboard(managerRole(role)),
  getSuppliers: (role?: UserRole): Promise<WarehouseSupplier[]> => api.managerWarehouseSuppliers(managerRole(role)),
  createSupplier: (role: UserRole | undefined, payload: WarehouseSupplierPayload): Promise<WarehouseSupplier> =>
    api.managerCreateWarehouseSupplier(managerRole(role), payload),
  updateSupplier: (role: UserRole | undefined, supplierId: number, payload: WarehouseSupplierPayload): Promise<WarehouseSupplier> =>
    api.managerUpdateWarehouseSupplier(managerRole(role), supplierId, payload),
  getItems: (role?: UserRole): Promise<WarehouseItem[]> => api.managerWarehouseItems(managerRole(role)),
  createItem: (role: UserRole | undefined, payload: WarehouseItemPayload): Promise<WarehouseItem> =>
    api.managerCreateWarehouseItem(managerRole(role), payload),
  updateItem: (role: UserRole | undefined, itemId: number, payload: WarehouseItemPayload): Promise<WarehouseItem> =>
    api.managerUpdateWarehouseItem(managerRole(role), itemId, payload),
  getBalances: (role?: UserRole, onlyLow = false): Promise<WarehouseStockBalance[]> =>
    api.managerWarehouseBalances(managerRole(role), onlyLow),
  getLedger: (role: UserRole | undefined, params?: WarehouseLedgerParams): Promise<WarehouseLedgerRow[]> =>
    api.managerWarehouseLedger(managerRole(role), params),
  getInboundVouchers: (role?: UserRole, limit = 100): Promise<WarehouseInboundVoucher[]> =>
    api.managerWarehouseInboundVouchers(managerRole(role), limit),
  createInboundVoucher: (role: UserRole | undefined, payload: WarehouseInboundVoucherPayload): Promise<WarehouseInboundVoucher> =>
    api.managerCreateWarehouseInboundVoucher(managerRole(role), payload),
  getOutboundVouchers: (role?: UserRole, limit = 100): Promise<WarehouseOutboundVoucher[]> =>
    api.managerWarehouseOutboundVouchers(managerRole(role), limit),
  getOutboundReasons: (role?: UserRole): Promise<WarehouseOutboundReason[]> =>
    api.managerWarehouseOutboundReasons(managerRole(role)),
  createOutboundVoucher: (role: UserRole | undefined, payload: WarehouseOutboundVoucherPayload): Promise<WarehouseOutboundVoucher> =>
    api.managerCreateWarehouseOutboundVoucher(managerRole(role), payload),
  getStockCounts: (role?: UserRole, limit = 100): Promise<WarehouseStockCount[]> =>
    api.managerWarehouseStockCounts(managerRole(role), limit),
  createStockCount: (role: UserRole | undefined, payload: WarehouseStockCountPayload): Promise<WarehouseStockCount> =>
    api.managerCreateWarehouseStockCount(managerRole(role), payload),
  settleStockCount: (role: UserRole | undefined, countId: number): Promise<WarehouseStockCount> =>
    api.managerSettleWarehouseStockCount(managerRole(role), countId),
};
