import type { OperationalWorkflowProfile, Order, OrderStatus, OrderType } from '../api/types';
import { parseApiDateMs } from './date';
import { resolveManagerFacingOrderStatusLabel } from './orderStatusPresentation';
import { sanitizeMojibakeText } from './textSanitizer';

export const statusClasses: Record<OrderStatus, string> = {
  CREATED: 'ui-badge-neutral',
  CONFIRMED: 'ui-badge-info',
  SENT_TO_KITCHEN: 'ui-badge-warning',
  IN_PREPARATION: 'ui-badge-primary',
  READY: 'ui-badge-success',
  OUT_FOR_DELIVERY: 'ui-badge-info',
  DELIVERED: 'ui-badge-success',
  DELIVERY_FAILED: 'ui-badge-danger',
  CANCELED: 'ui-badge-danger',
};

export function resolveOrderStatusLabel(
  status: OrderStatus,
  type?: OrderType,
  paymentStatus?: 'unpaid' | 'paid' | 'refunded' | null,
): string {
  return resolveManagerFacingOrderStatusLabel(status, type, paymentStatus);
}

export type OrderRowTone = 'success' | 'warning' | 'danger';

export function orderRowTone(status: OrderStatus): OrderRowTone {
  if (status === 'DELIVERED' || status === 'READY') {
    return 'success';
  }
  if (status === 'CANCELED' || status === 'DELIVERY_FAILED') {
    return 'danger';
  }
  return 'warning';
}

const orderTypeText: Record<OrderType, string> = {
  'dine-in': 'داخل المطعم',
  takeaway: 'استلام',
  delivery: 'توصيل',
};

const orderTypeStyle: Record<OrderType, string> = {
  'dine-in': 'ui-pill-primary',
  takeaway: 'ui-pill-info',
  delivery: 'ui-pill-success',
};

const tableStatusText: Record<'available' | 'occupied' | 'reserved', string> = {
  available: 'متاحة',
  occupied: 'مشغولة',
  reserved: 'محجوزة',
};

const ADDON_STAGE_SEQUENCE = ['base', 'kitchen', 'delivery', 'warehouse', 'finance', 'intelligence', 'reports'] as const;

export function orderTypeLabel(type: OrderType): string {
  return orderTypeText[type];
}

export function orderTypeClasses(type: OrderType): string {
  return orderTypeStyle[type];
}

export function formatOrderTrackingId(orderId: number): string {
  const normalized = Number.isFinite(orderId) ? Math.max(0, Math.trunc(orderId)) : 0;
  return `#${String(normalized).padStart(6, '0')}`;
}

export function resolveOrderDeliveryAddress(
  order: Pick<Order, 'type' | 'address' | 'delivery_location_label'>,
): string {
  if (order.type !== 'delivery') {
    return '-';
  }

  const legacyAddress = sanitizeMojibakeText(order.address, '');
  const structuredLabel = sanitizeMojibakeText(order.delivery_location_label, '');

  if (legacyAddress && !legacyAddress.includes('?')) {
    return legacyAddress;
  }
  if (structuredLabel) {
    return structuredLabel;
  }
  if (legacyAddress) {
    return legacyAddress;
  }
  return '-';
}

export function orderDateKey(value: string): string {
  const parsedMs = parseApiDateMs(value);
  if (Number.isNaN(parsedMs)) {
    return '';
  }
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(parsedMs));
}

export function tableStatusLabel(status: 'available' | 'occupied' | 'reserved'): string {
  return tableStatusText[status];
}

export function resolveOperationalWorkflowProfile(
  activationStageId: string | null | undefined,
  type: OrderType,
): OperationalWorkflowProfile {
  const normalizedStageId = (activationStageId || 'base').trim().toLowerCase();
  const safeStageId = ADDON_STAGE_SEQUENCE.includes(normalizedStageId as (typeof ADDON_STAGE_SEQUENCE)[number])
    ? (normalizedStageId as (typeof ADDON_STAGE_SEQUENCE)[number])
    : 'base';
  const sequence = ADDON_STAGE_SEQUENCE.indexOf(safeStageId);
  const kitchenSequence = ADDON_STAGE_SEQUENCE.indexOf('kitchen');
  const deliverySequence = ADDON_STAGE_SEQUENCE.indexOf('delivery');

  if (sequence >= deliverySequence && type === 'delivery') {
    return 'kitchen_delivery_managed';
  }
  if (sequence >= kitchenSequence) {
    return 'kitchen_managed';
  }
  return 'base_direct';
}

export function managerActions(
  status: OrderStatus,
  type: OrderType,
  workflowProfile: OperationalWorkflowProfile,
): Array<{ label: string; target: OrderStatus }> {
  if (workflowProfile === 'base_direct') {
    switch (status) {
      case 'CREATED':
        return [
          { label: 'تأكيد', target: 'CONFIRMED' },
          { label: 'إلغاء', target: 'CANCELED' },
        ];
      case 'CONFIRMED':
        return [
          { label: directReadyActionLabel(type), target: 'READY' },
          { label: 'إلغاء', target: 'CANCELED' },
        ];
      case 'READY':
        return [{ label: 'تسليم', target: 'DELIVERED' }];
      default:
        return [];
    }
  }

  switch (status) {
    case 'CREATED':
      return [
        { label: 'تأكيد', target: 'CONFIRMED' },
        { label: 'إلغاء', target: 'CANCELED' },
      ];
    case 'CONFIRMED':
      return [
        { label: 'إرسال للمطبخ', target: 'SENT_TO_KITCHEN' },
        { label: 'إلغاء', target: 'CANCELED' },
      ];
    case 'READY':
      if (workflowProfile === 'kitchen_delivery_managed' && type === 'delivery') {
        return [];
      }
      return [{ label: 'تسليم', target: 'DELIVERED' }];
    default:
      return [];
  }
}

export function directReadyActionLabel(type: OrderType): string {
  if (type === 'delivery') {
    return 'تجهيز للخروج';
  }
  if (type === 'dine-in') {
    return 'جاهز للتقديم';
  }
  return 'جاهز للاستلام';
}
