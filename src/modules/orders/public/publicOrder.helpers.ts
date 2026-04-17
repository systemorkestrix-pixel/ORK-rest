import type { OrderType, PublicJourneyProduct, PublicSecondaryOption } from '@/shared/api/types';

export interface CartSecondarySelection {
  option: PublicSecondaryOption;
  quantity: number;
}

export interface CartRow {
  product: PublicJourneyProduct;
  quantity: number;
}

export const orderTypeOptions: Array<{ value: OrderType; label: string }> = [
  { value: 'takeaway', label: 'استلام من المطعم' },
  { value: 'delivery', label: 'توصيل للمنزل' },
  { value: 'dine-in', label: 'طلب من الطاولة' },
];

export const fallbackDeliveryBlockedReason =
  'خدمة التوصيل غير متاحة حاليًا. يرجى اختيار الاستلام أو الطلب من الطاولة.';

export const backendOrigin =
  (import.meta.env.VITE_BACKEND_ORIGIN as string | undefined)?.replace(/\/$/, '') ?? 'http://127.0.0.1:8124';

export const timeFormatter = new Intl.DateTimeFormat('ar-DZ-u-nu-latn', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

export const orderTypeLabelMap: Record<OrderType, string> = {
  'dine-in': 'طلب من الطاولة',
  takeaway: 'استلام من المطعم',
  delivery: 'توصيل',
};

export function resolveImageUrl(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (import.meta.env.DEV && normalizedPath.startsWith('/static/')) {
    return normalizedPath;
  }
  return `${backendOrigin}${normalizedPath}`;
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return fallback;
}

export function getCartRowTotal(row: CartRow): number {
  return row.product.price * row.quantity;
}
