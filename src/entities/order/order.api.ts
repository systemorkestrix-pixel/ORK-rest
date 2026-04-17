import { api } from '@/shared/api/client';
import type {
  CreateOrderPayload,
  DeliveryFailureResolutionAction,
  DeliverySettlement,
  OperationalCapabilities,
  Order,
  OrdersPage,
  OrderStatus,
  OrderType,
  UserRole,
} from '@/shared/api/types';

export interface OrdersPagedParams {
  page: number;
  pageSize: number;
  search?: string;
  sortBy?: 'created_at' | 'total' | 'status' | 'id';
  sortDirection?: 'asc' | 'desc';
  status?: OrderStatus;
  orderType?: OrderType;
}

const managerRole = (role?: UserRole) => role ?? 'manager';

export const orderApi = {
  getOrders: (role?: UserRole): Promise<Order[]> => api.managerOrders(managerRole(role)),
  getOrdersPaged: (role: UserRole | undefined, params: OrdersPagedParams): Promise<OrdersPage> =>
    api.managerOrdersPaged(managerRole(role), params),
  getActiveOrders: (role?: UserRole, limit = 200): Promise<Order[]> =>
    api.managerActiveOrders(managerRole(role), limit),
  getOperationalCapabilities: (role?: UserRole): Promise<OperationalCapabilities> =>
    api.managerOperationalCapabilities(managerRole(role)),
  transitionOrder: (
    role: UserRole | undefined,
    orderId: number,
    targetStatus: OrderStatus,
    amountReceived?: number,
    collectPayment?: boolean,
    reasonCode?: string,
    reasonNote?: string
  ): Promise<Order> =>
    api.managerTransitionOrder(
      managerRole(role),
      orderId,
      targetStatus,
      amountReceived,
      collectPayment,
      reasonCode,
      reasonNote
    ),
  notifyDeliveryTeam: (role: UserRole | undefined, orderId: number): Promise<Order> =>
    api.managerNotifyDeliveryTeam(managerRole(role), orderId),
  emergencyDeliveryFail: (
    role: UserRole | undefined,
    orderId: number,
    reasonCode: string,
    reasonNote?: string
  ): Promise<Order> => api.managerEmergencyDeliveryFail(managerRole(role), orderId, reasonCode, reasonNote),
  resolveDeliveryFailure: (
    role: UserRole | undefined,
    orderId: number,
    resolutionAction: DeliveryFailureResolutionAction,
    resolutionNote?: string
  ): Promise<Order> => api.managerResolveDeliveryFailure(managerRole(role), orderId, resolutionAction, resolutionNote),
  collectOrderPayment: (role: UserRole | undefined, orderId: number, amountReceived?: number): Promise<Order> =>
    api.managerCollectOrderPayment(managerRole(role), orderId, amountReceived),
  settleDeliveryOrder: (role: UserRole | undefined, orderId: number): Promise<DeliverySettlement> =>
    api.managerSettleDeliveryOrder(managerRole(role), orderId),
  createManualOrder: (role: UserRole | undefined, payload: CreateOrderPayload): Promise<Order> =>
    api.managerCreateManualOrder(managerRole(role), payload),
};
