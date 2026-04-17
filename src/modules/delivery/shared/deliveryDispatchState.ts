import type { Order } from '@/shared/api/types';
import { resolveOrderStatusLabel } from '@/shared/utils/order';

export function hasActiveDeliveryAssignment(order: Order): boolean {
  return order.delivery_assignment_status === 'assigned' || order.delivery_assignment_status === 'departed';
}

export function canManageDeliveryDispatch(order: Order): boolean {
  return order.type === 'delivery' && (order.status === 'IN_PREPARATION' || order.status === 'READY');
}

export function isAwaitingDispatchSelection(order: Order, autoNotifyTeam: boolean): boolean {
  return (
    canManageDeliveryDispatch(order) &&
    !autoNotifyTeam &&
    !order.delivery_team_notified_at &&
    !hasActiveDeliveryAssignment(order) &&
    order.delivery_dispatch_status !== 'offered'
  );
}

export function isAwaitingDispatchOffer(order: Order): boolean {
  return (
    canManageDeliveryDispatch(order) &&
    !!order.delivery_team_notified_at &&
    !hasActiveDeliveryAssignment(order) &&
    order.delivery_dispatch_status !== 'offered'
  );
}

export function isOfferedDispatch(order: Order): boolean {
  return (
    canManageDeliveryDispatch(order) &&
    !!order.delivery_team_notified_at &&
    !hasActiveDeliveryAssignment(order) &&
    order.delivery_dispatch_status === 'offered'
  );
}

export function isReadyAssigned(order: Order): boolean {
  return order.status === 'READY' && order.delivery_assignment_status === 'assigned';
}

export function resolveDispatchTargetLabel(order: Order): string | null {
  return order.delivery_assignment_driver_name ?? order.delivery_dispatch_driver_name ?? order.delivery_dispatch_provider_name ?? null;
}

export function resolveDeliveryDispatchStatusTag(
  order: Order,
  autoNotifyTeam: boolean,
): { label: string; className: string } | null {
  if (isAwaitingDispatchSelection(order, autoNotifyTeam)) {
    return { label: 'بانتظار تحديد الجهة', className: 'border-amber-300 bg-amber-100 text-amber-800' };
  }
  if (isAwaitingDispatchOffer(order)) {
    return { label: 'بانتظار إرسال العرض', className: 'border-orange-300 bg-orange-100 text-orange-800' };
  }
  if (isOfferedDispatch(order)) {
    return {
      label: order.delivery_dispatch_scope === 'driver' ? 'بانتظار قبول السائق' : 'بانتظار قبول الجهة',
      className: 'border-sky-300 bg-sky-100 text-sky-800',
    };
  }
  if (isReadyAssigned(order)) {
    return { label: 'جاهز مع عنصر توصيل', className: 'border-emerald-300 bg-emerald-100 text-emerald-800' };
  }
  return null;
}

export function resolveDeliveryDispatchStatusText(order: Order, autoNotifyTeam: boolean): string {
  if (order.delivery_assignment_status === 'assigned') return 'تم الالتقاط';
  if (order.delivery_assignment_status === 'departed') return 'خرج للتوصيل';
  if (order.delivery_assignment_status === 'delivered') return 'تم التسليم';
  if (order.delivery_assignment_status === 'failed') return 'فشل التوصيل';
  if (isAwaitingDispatchSelection(order, autoNotifyTeam)) return 'لم تُحدَّد جهة الاستلام بعد';
  if (isAwaitingDispatchOffer(order)) return 'الفريق مُبلّغ والطلب بانتظار إرسال العرض';
  if (isOfferedDispatch(order)) {
    return order.delivery_dispatch_scope === 'driver' ? 'العرض بانتظار قبول السائق' : 'العرض بانتظار قبول الجهة';
  }
  return '-';
}

function normalizeDeliveryStatusText(text: string): string {
  return text.replace('خارج للتوصيل', 'خرج للتوصيل').replace(/\s+/g, ' ').trim();
}

export function resolveDeliveryDispatchSupplementalTag(
  order: Order,
  autoNotifyTeam: boolean,
): { label: string; className: string } | null {
  const tag = resolveDeliveryDispatchStatusTag(order, autoNotifyTeam);
  if (!tag) return null;

  const orderStatusLabel = resolveOrderStatusLabel(order.status, order.type, order.payment_status ?? null);
  if (normalizeDeliveryStatusText(tag.label) === normalizeDeliveryStatusText(orderStatusLabel)) {
    return null;
  }

  return tag;
}

export function resolveDeliveryDispatchFollowupText(order: Order, autoNotifyTeam: boolean): string | null {
  const followupText = resolveDeliveryDispatchStatusText(order, autoNotifyTeam);
  if (followupText === '-') return null;

  const dispatchTagLabel = resolveDeliveryDispatchSupplementalTag(order, autoNotifyTeam)?.label ?? null;
  const orderStatusLabel = resolveOrderStatusLabel(order.status, order.type, order.payment_status ?? null);
  const normalizedFollowupText = normalizeDeliveryStatusText(followupText);

  if (dispatchTagLabel && normalizeDeliveryStatusText(dispatchTagLabel) === normalizedFollowupText) {
    return null;
  }

  if (normalizeDeliveryStatusText(orderStatusLabel) === normalizedFollowupText) {
    return null;
  }

  return followupText;
}
