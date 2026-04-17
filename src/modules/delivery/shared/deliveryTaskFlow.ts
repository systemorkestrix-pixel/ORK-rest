import type { Order } from '@/shared/api/types';

export function canDriverAcceptOrClaimOrder(order: Order): boolean {
  return (
    (order.status === 'IN_PREPARATION' || order.status === 'READY') &&
    !order.delivery_assignment_status &&
    (!order.delivery_dispatch_status || order.delivery_dispatch_scope === 'driver')
  );
}

export function canDriverRejectOfferedDispatch(order: Order): boolean {
  return (
    order.delivery_dispatch_status === 'offered' &&
    order.delivery_dispatch_scope === 'driver' &&
    !order.delivery_assignment_status
  );
}

export function isDriverWaitingForOrderReady(order: Order): boolean {
  return order.status === 'IN_PREPARATION' && order.delivery_assignment_status === 'assigned';
}

export function canDriverStartDelivery(order: Order): boolean {
  return order.status === 'READY' && order.delivery_assignment_status === 'assigned';
}

export function canDriverResolveDelivery(order: Order): boolean {
  return order.status === 'OUT_FOR_DELIVERY' && order.delivery_assignment_status === 'departed';
}
