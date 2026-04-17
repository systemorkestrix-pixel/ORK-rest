import type {
  OrderPaymentStatus,
  OrderStatus,
  OrderType,
  PublicWorkflowProfile,
} from '../api/types';

export type CustomerTrackingStage = 'received' | 'confirmed' | 'preparing' | 'ready' | 'out' | 'done' | 'canceled' | 'failed';

const baseOrderStatusLabel: Record<OrderStatus, string> = {
  CREATED: 'تم الإنشاء',
  CONFIRMED: 'تم التأكيد',
  SENT_TO_KITCHEN: 'أرسل للمطبخ',
  IN_PREPARATION: 'قيد التحضير',
  READY: 'جاهز',
  OUT_FOR_DELIVERY: 'خرج للتوصيل',
  DELIVERED: 'تم التسليم',
  DELIVERY_FAILED: 'فشل التوصيل',
  CANCELED: 'ملغى',
};

export function resolveManagerFacingOrderStatusLabel(
  status: OrderStatus,
  type?: OrderType,
  paymentStatus?: OrderPaymentStatus | null,
): string {
  if (status !== 'DELIVERED') {
    return baseOrderStatusLabel[status];
  }

  if (type === 'dine-in') {
    return paymentStatus === 'paid' ? 'تمت التسوية' : 'تم التقديم';
  }

  if (type === 'takeaway') {
    return 'تم الاستلام';
  }

  return 'تم التسليم';
}

export function resolveCustomerFacingOrderStatusLabel(
  status: OrderStatus,
  type: OrderType,
  paymentStatus?: OrderPaymentStatus | null,
): string {
  if (status === 'CREATED') {
    return 'تم استلام الطلب';
  }

  if (status === 'CONFIRMED' || status === 'SENT_TO_KITCHEN') {
    return 'تم تأكيد الطلبية';
  }

  if (status === 'IN_PREPARATION') {
    return 'قيد التحضير';
  }

  if (status === 'READY') {
    if (type === 'delivery') return 'جاهز للخروج';
    if (type === 'dine-in') return 'جاهز للتقديم';
    return 'جاهز للاستلام';
  }

  if (status === 'OUT_FOR_DELIVERY') {
    return 'خرج للتوصيل';
  }

  if (status === 'DELIVERED') {
    return resolveManagerFacingOrderStatusLabel(status, type, paymentStatus);
  }

  if (status === 'DELIVERY_FAILED') {
    return 'تعذر التوصيل';
  }

  return 'ملغى';
}

export function resolveCustomerTrackingStage(
  status: OrderStatus,
  workflowProfile: PublicWorkflowProfile,
): CustomerTrackingStage {
  if (status === 'CANCELED') {
    return 'canceled';
  }

  if (status === 'DELIVERY_FAILED') {
    return 'failed';
  }

  if (status === 'CREATED') {
    return 'received';
  }

  if (status === 'CONFIRMED' || status === 'SENT_TO_KITCHEN') {
    return 'confirmed';
  }

  if (status === 'IN_PREPARATION') {
    return workflowProfile === 'kitchen_managed' ? 'preparing' : 'ready';
  }

  if (status === 'READY') {
    return 'ready';
  }

  if (status === 'OUT_FOR_DELIVERY') {
    return 'out';
  }

  return 'done';
}

export function resolveDriverFacingTaskStatusLabel(params: {
  orderStatus: OrderStatus;
  assignmentStatus?: string | null;
  dispatchStatus?: string | null;
}): string {
  const { orderStatus, assignmentStatus, dispatchStatus } = params;

  if (dispatchStatus === 'offered') {
    return 'عرض جديد';
  }
  if (assignmentStatus === 'assigned') {
    return 'جاهز للانطلاق';
  }
  if (assignmentStatus === 'departed' || orderStatus === 'OUT_FOR_DELIVERY') {
    return 'خرج للتوصيل';
  }
  if (assignmentStatus === 'delivered' || orderStatus === 'DELIVERED') {
    return 'تم التسليم';
  }
  if (assignmentStatus === 'failed' || orderStatus === 'DELIVERY_FAILED') {
    return 'فشل التوصيل';
  }
  return 'بانتظار الإجراء التالي';
}
