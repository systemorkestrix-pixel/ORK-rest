import { useQuery } from '@tanstack/react-query';

import type { UserRole } from '@/shared/api/types';
import type { Order, OrdersPage, OrderStatus, OrderType } from './order.types';
import { orderApi, type OrdersPagedParams } from './order.api';

export function useOrdersPaged(
  role: UserRole | undefined,
  params: OrdersPagedParams,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false;
    refetchIntervalInBackground?: boolean;
    staleTime?: number;
    refetchOnWindowFocus?: boolean | 'always';
  }
) {
  return useQuery<OrdersPage>({
    queryKey: [
      'manager-orders-paged',
      params.page,
      params.search ?? '',
      params.sortBy ?? 'created_at',
      params.sortDirection ?? 'desc',
      params.status ?? 'all',
      params.orderType ?? 'all',
    ],
    queryFn: () => orderApi.getOrdersPaged(role, params),
    enabled: options?.enabled,
    refetchInterval: options?.refetchInterval,
    refetchIntervalInBackground: options?.refetchIntervalInBackground,
    staleTime: options?.staleTime,
    refetchOnWindowFocus: options?.refetchOnWindowFocus,
  });
}

export function useActiveOrders(
  role: UserRole | undefined,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false;
    refetchIntervalInBackground?: boolean;
    staleTime?: number;
    refetchOnWindowFocus?: boolean | 'always';
    limit?: number;
  }
) {
  return useQuery<Order[]>({
    queryKey: ['manager-active-orders', options?.limit ?? 200],
    queryFn: () => orderApi.getActiveOrders(role, options?.limit ?? 200),
    enabled: options?.enabled,
    refetchInterval: options?.refetchInterval,
    refetchIntervalInBackground: options?.refetchIntervalInBackground,
    staleTime: options?.staleTime,
    refetchOnWindowFocus: options?.refetchOnWindowFocus,
  });
}

export function useOperationalCapabilities(role: UserRole | undefined, enabled = true) {
  return useQuery({
    queryKey: ['manager-operational-capabilities'],
    queryFn: () => orderApi.getOperationalCapabilities(role),
    enabled,
  });
}

export function useOrdersFilters() {
  const orderStatuses: OrderStatus[] = [
    'CREATED',
    'CONFIRMED',
    'SENT_TO_KITCHEN',
    'IN_PREPARATION',
    'READY',
    'OUT_FOR_DELIVERY',
    'DELIVERED',
    'DELIVERY_FAILED',
    'CANCELED',
  ];
  const orderTypes: OrderType[] = ['dine-in', 'takeaway', 'delivery'];
  return { orderStatuses, orderTypes };
}
