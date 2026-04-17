import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useRef } from 'react';

import { useAuthStore } from '@/modules/auth/store';
import { orderApi } from '@/entities/order';
import { productApi } from '@/entities/product';
import { tableApi } from '@/entities/table';
import type { CreateOrderPayload, Order, OrderStatus, OrderType } from '@/entities/order';
import type { Product } from '@/entities/product';
import type { TableInfo } from '@/entities/table';
import { api } from '@/shared/api/client';
import { AlertTriangle, ArrowDownUp, ArrowLeft, ArrowRight, CheckCircle2, ClipboardCheck, ClipboardList } from 'lucide-react';
import { Eye, PackageCheck, Plus, Printer, RotateCcw, Search, SlidersHorizontal, Trash2, Truck, XCircle } from 'lucide-react';
import { Minus } from 'lucide-react';
import { Modal } from '@/shared/ui/Modal';
import { PageShell } from '@/shared/ui/PageShell';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { TABLE_ACTION_BUTTON_BASE, TABLE_STATUS_CHIP_BORDER_BASE } from '@/shared/ui/tableAppearance';
import { TablePagination } from '@/shared/ui/TablePagination';
import { formatOrderTrackingId, orderDateKey, orderRowTone, managerActions, orderTypeClasses, orderTypeLabel, resolveOperationalWorkflowProfile, resolveOrderDeliveryAddress, tableStatusLabel } from '@/shared/utils/order';
import { parseApiDateMs } from '@/shared/utils/date';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { sanitizeMojibakeText } from '@/shared/utils/textSanitizer';
import type { DeliveryDriver, DeliveryProvider } from '@/shared/api/types';
import { DeliveryDispatchAction } from '@/modules/delivery/components/DeliveryDispatchAction';
import {
  hasActiveDeliveryAssignment,
  isAwaitingDispatchSelection,
  resolveDeliveryDispatchSupplementalTag,
} from '@/modules/delivery/shared/deliveryDispatchState';
import { ManagerDeliveryAddressSelector } from './components/ManagerDeliveryAddressSelector';

const timeOnlyFormatter = new Intl.DateTimeFormat('ar-DZ-u-nu-latn', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

function actionButtonClasses(targetStatus: OrderStatus): string {
  if (targetStatus === 'CONFIRMED') {
    return 'border-emerald-300 bg-emerald-100/80 text-emerald-900 hover:bg-emerald-100';
  }
  if (targetStatus === 'SENT_TO_KITCHEN') {
    return 'border-amber-300 bg-amber-100/80 text-amber-900 hover:bg-amber-100';
  }
  if (targetStatus === 'CANCELED') {
    return 'border-rose-300 bg-rose-100/80 text-rose-900 hover:bg-rose-100';
  }
  if (targetStatus === 'DELIVERED') {
    return 'border-cyan-300 bg-cyan-100/80 text-cyan-900 hover:bg-cyan-100';
  }
  return 'border-stone-300 bg-stone-100/80 text-stone-800 hover:bg-stone-100';
}

const rowCellBase = 'px-3 py-2.5 border-b border-[var(--console-border)] bg-[var(--surface-card)]/85 text-[13px] text-[var(--text-secondary)]';
const tablePrintIconButtonClass =
  'inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-violet-300 bg-violet-100/80 text-violet-900 transition hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-60';
const PAGE_SIZE = 12;
const LIVE_ORDERS_REFETCH_MS = 2000;
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
const activeOrderStatuses: OrderStatus[] = ['CREATED', 'CONFIRMED', 'SENT_TO_KITCHEN', 'IN_PREPARATION', 'READY', 'OUT_FOR_DELIVERY'];
const orderTypes: OrderType[] = ['dine-in', 'takeaway', 'delivery'];
const fallbackDeliveryBlockedReason = 'نظام التوصيل غير مفعّل في النسخة الحالية.';
const cancellationReasonOptions = [
  { value: 'customer_request', label: 'طلب العميل' },
  { value: 'duplicate_order', label: 'طلب مكرر' },
  { value: 'item_unavailable', label: 'نفاد صنف' },
  { value: 'payment_issue', label: 'تعذر الدفع' },
  { value: 'operational_issue', label: 'ظرف تشغيلي' },
];
const emergencyFailReasonOptions = [
  { value: 'delivery_service_disabled', label: 'تعذر تشغيل خدمة التوصيل' },
  { value: 'no_driver_available', label: 'عدم توفر سائق توصيل' },
  { value: 'address_issue', label: 'تعذر الوصول إلى العنوان' },
  { value: 'customer_unreachable', label: 'تعذر التواصل مع العميل' },
  { value: 'operational_emergency', label: 'طارئ تشغيلي' },
];

function deliverySettlementStatusLabel(status: string | null | undefined): string | null {
  if (!status) {
    return null;
  }
  switch (status) {
    case 'pending':
      return 'قيد التسوية';
    case 'partially_remitted':
      return 'توريد جزئي';
    case 'remitted':
    case 'settled':
      return 'تمت التسوية';
    case 'variance':
      return 'يوجد فرق';
    case 'reversed':
      return 'ملغاة';
    default:
      return 'تسوية التوصيل';
  }
}

function deliverySettlementStatusClasses(status: string | null | undefined): string {
  switch (status) {
    case 'settled':
    case 'remitted':
      return 'border-emerald-300 bg-emerald-100/80 text-emerald-900';
    case 'partially_remitted':
      return 'border-amber-300 bg-amber-100/80 text-amber-900';
    case 'variance':
      return 'border-rose-300 bg-rose-100/80 text-rose-900';
    case 'reversed':
      return 'border-stone-300 bg-stone-100/80 text-stone-800';
    default:
      return 'border-cyan-300 bg-cyan-100/80 text-cyan-900';
  }
}

function deliveryFailureResolutionLabel(status: string | null | undefined): string | null {
  switch (status) {
    case 'retry_delivery':
      return 'أعيد للتوصيل';
    case 'convert_to_takeaway':
      return 'تحول إلى استلام';
    case 'close_failure':
      return 'أغلق نهائيًا';
    default:
      return null;
  }
}

function deliveryFailureResolutionClasses(status: string | null | undefined): string {
  switch (status) {
    case 'retry_delivery':
      return `${TABLE_STATUS_CHIP_BORDER_BASE} border-sky-300 bg-sky-100/80 text-sky-900`;
    case 'convert_to_takeaway':
      return `${TABLE_STATUS_CHIP_BORDER_BASE} border-amber-300 bg-amber-100/80 text-amber-900`;
    case 'close_failure':
      return `${TABLE_STATUS_CHIP_BORDER_BASE} border-stone-300 bg-stone-100/80 text-stone-800`;
    default:
      return `${TABLE_STATUS_CHIP_BORDER_BASE} border-stone-300 bg-stone-100/80 text-stone-800`;
  }
}

function normalizeStatus(value: string | null): OrderStatus | 'all' {
  return value && orderStatuses.includes(value as OrderStatus) ? (value as OrderStatus) : 'all';
}

function normalizeType(value: string | null): OrderType | 'all' {
  return value && orderTypes.includes(value as OrderType) ? (value as OrderType) : 'all';
}

interface ManualOrderItemRow {
  product_id: number;
  quantity: number;
}

interface ManualSecondaryItemRow {
  product_id: number;
  quantity: number;
}

type ManualOrderStep = 'type' | 'details' | 'primary' | 'secondary' | 'review';
type ReasonDialogStep = 'reason' | 'review';

interface ReasonDialogState {
  mode: 'cancel' | 'emergency_fail';
  order: Order;
}

interface OrdersPageProps {
  scope?: 'full' | 'console';
  showCreateButton?: boolean;
  createRequestToken?: number;
}

function isActiveStatus(status: OrderStatus): boolean {
  return activeOrderStatuses.includes(status);
}

function compareOrders(a: Order, b: Order, sortBy: 'created_at' | 'total' | 'status' | 'id', sortDirection: 'asc' | 'desc'): number {
  const direction = sortDirection === 'asc' ? 1 : -1;
  if (sortBy === 'total') {
    return (a.total - b.total) * direction;
  }
  if (sortBy === 'status') {
    return a.status.localeCompare(b.status) * direction;
  }
  if (sortBy === 'id') {
    return (a.id - b.id) * direction;
  }
  return (parseApiDateMs(a.created_at) - parseApiDateMs(b.created_at)) * direction;
}

const orderHighlightMap: Partial<
  Record<
    OrderStatus,
    {
      label: string;
      cardClass: string;
      cellClass: string;
      tagClass: string;
    }
  >
> = {
  READY: {
    label: 'جاهز للتسليم',
    cardClass: 'border-emerald-300 bg-emerald-50/70',
    cellClass: 'bg-emerald-50/70',
    tagClass: 'border-emerald-300 bg-emerald-100 text-emerald-800',
  },
  OUT_FOR_DELIVERY: {
    label: 'خارج للتوصيل',
    cardClass: 'border-sky-300 bg-sky-50/70',
    cellClass: 'bg-sky-50/70',
    tagClass: 'border-sky-300 bg-sky-100 text-sky-800',
  },
  DELIVERY_FAILED: {
    label: 'بحاجة لمعالجة فشل التوصيل',
    cardClass: 'border-rose-300 bg-rose-50/70',
    cellClass: 'bg-rose-50/70',
    tagClass: 'border-rose-300 bg-rose-100 text-rose-800',
  },
};

function resolveOrderHighlight(status: OrderStatus) {
  return orderHighlightMap[status] ?? null;
}

function resolveOrderAddressSummary(order: Order): string {
  return resolveOrderDeliveryAddress(order);
}

function resolveOrderDeliveryPricingSourceLabel(order: Order): string {
  if (order.type !== 'delivery') {
    return 'غير مطبق';
  }
  return order.delivery_location_key ? 'من شجرة العناوين' : 'رسم ثابت أو سجل قديم';
}

function resolveOrderContactSummary(order: Order): { primary: string; secondary: string } {
  if (order.table_id) {
    return {
      primary: `طاولة ${order.table_id}`,
      secondary: `${order.items.length} أصناف داخل الجلسة`,
    };
  }

  if (order.phone) {
    return {
      primary: order.phone,
      secondary: order.type === 'delivery' ? 'رقم التواصل مع العميل' : 'رقم تواصل اختياري',
    };
  }

  return {
    primary: 'بدون رقم هاتف',
    secondary: order.type === 'takeaway' ? 'استلام مباشر بدون هاتف' : 'لا توجد بيانات تواصل',
  };
}

function resolveOrderLocationSummary(order: Order): { primary: string; secondary: string } {
  if (order.type === 'delivery') {
    return {
      primary: resolveOrderAddressSummary(order),
      secondary: resolveOrderDeliveryPricingSourceLabel(order),
    };
  }

  if (order.type === 'dine-in') {
    return {
      primary: order.table_id ? `داخل المطعم - طاولة ${order.table_id}` : 'داخل المطعم',
      secondary: 'تقديم مباشر داخل الصالة',
    };
  }

  return {
    primary: 'استلام من المطعم',
    secondary: 'لا يحتاج عنوان توصيل',
  };
}

function resolveOrderTicketContact(order: Order): string {
  if (order.table_id) {
    return `طاولة ${order.table_id}`;
  }
  if (order.phone) {
    return order.phone;
  }
  return '-';
}

function resolveOrderPiecesTotal(order: Order): number {
  return order.items.reduce((sum, item) => sum + item.quantity, 0);
}

function openOrderTicketPrintView(order: Order): void {
  const popup = window.open('', '_blank', 'noopener,noreferrer,width=560,height=760');
  if (!popup) {
    window.alert('تعذر فتح نافذة التذكرة. يمكنك متابعة التشغيل والمحاولة لاحقًا بعد السماح بالنوافذ المنبثقة.');
    return;
  }

  const styles = window.getComputedStyle(document.documentElement);
  const textColor = styles.getPropertyValue('--text-primary-strong').trim() || '#2f2218';
  const mutedColor = styles.getPropertyValue('--text-muted').trim() || '#6f6357';
  const borderColor = styles.getPropertyValue('--console-border').trim() || '#d6c3ab';
  const notes = sanitizeMojibakeText(order.notes, '').trim();
  const createdAt = `${orderDateKey(order.created_at)} - ${timeOnlyFormatter.format(new Date(parseApiDateMs(order.created_at)))}`;
  const piecesTotal = resolveOrderPiecesTotal(order);
  const itemsMarkup = order.items
    .map(
      (item) => `
        <tr>
          <td class="qty">${item.quantity}</td>
          <td class="name">${sanitizeMojibakeText(item.product_name)}</td>
        </tr>`,
    )
    .join('');

  popup.document.open();
  popup.document.write(`<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>تذكرة الطلب ${formatOrderTrackingId(order.id)}</title>
  <style>
    body { font-family: Cairo, Tahoma, Arial, sans-serif; margin: 0; background: #fffdf8; color: ${textColor}; }
    .page { width: 100%; max-width: 420px; margin: 0 auto; padding: 18px 16px 22px; }
    .ticket { border: 1px dashed ${borderColor}; border-radius: 22px; background: #fff; padding: 18px 16px; }
    .head { display: flex; align-items: start; justify-content: space-between; gap: 12px; padding-bottom: 14px; border-bottom: 1px dashed ${borderColor}; }
    .title { margin: 0; font-size: 22px; font-weight: 900; }
    .meta { margin-top: 6px; color: ${mutedColor}; font-size: 12px; line-height: 1.8; }
    .chip { display: inline-flex; align-items: center; justify-content: center; min-height: 34px; padding: 0 12px; border-radius: 999px; border: 1px solid ${borderColor}; background: #fff6ea; color: #9a5b24; font-size: 11px; font-weight: 800; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
    .card { border: 1px solid ${borderColor}; border-radius: 16px; padding: 10px 12px; background: #fffdf9; }
    .label { color: ${mutedColor}; font-size: 10px; font-weight: 800; }
    .value { margin-top: 6px; font-size: 14px; font-weight: 900; }
    .table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    .table th { text-align: right; color: ${mutedColor}; font-size: 10px; font-weight: 800; padding: 0 0 8px; }
    .table td { border-top: 1px dashed ${borderColor}; padding: 10px 0; vertical-align: top; font-size: 14px; font-weight: 800; }
    .table .qty { width: 64px; text-align: center; color: #9a5b24; }
    .table .name { padding-right: 8px; }
    .notes { margin-top: 16px; border: 1px dashed ${borderColor}; border-radius: 16px; padding: 10px 12px; background: #fff9ef; }
    .notes .label { color: #9a5b24; }
    .notes .value { margin-top: 6px; font-size: 13px; font-weight: 800; line-height: 1.9; }
    .footer { margin-top: 16px; padding-top: 14px; border-top: 1px dashed ${borderColor}; }
    .summary { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 15px; font-weight: 900; }
    .summary .count { color: #9a5b24; }
    .hint { margin-top: 10px; color: ${mutedColor}; font-size: 11px; line-height: 1.8; }
    @media print { body { background: #fff; } .page { padding: 0; } .ticket { border: none; border-radius: 0; } }
  </style>
</head>
<body>
  <div class="page">
    <div class="ticket">
      <div class="head">
        <div>
          <h1 class="title">${formatOrderTrackingId(order.id)}</h1>
          <div class="meta">
            <div>وقت الإنشاء: ${createdAt}</div>
            <div>نوع الطلب: ${orderTypeLabel(order.type)}</div>
          </div>
        </div>
        <span class="chip">تذكرة يدوية</span>
      </div>
      <div class="grid">
        <div class="card">
          <div class="label">${order.table_id ? 'رقم الطاولة' : 'الهاتف'}</div>
          <div class="value" dir="${order.phone && !order.table_id ? 'ltr' : 'rtl'}">${resolveOrderTicketContact(order)}</div>
        </div>
        <div class="card">
          <div class="label">إجمالي القطع</div>
          <div class="value">${piecesTotal}</div>
        </div>
      </div>
      <table class="table">
        <thead>
          <tr>
            <th class="qty">الكمية</th>
            <th class="name">العناصر</th>
          </tr>
        </thead>
        <tbody>${itemsMarkup}</tbody>
      </table>
      ${notes ? `<div class="notes"><div class="label">الملاحظات</div><div class="value">${notes}</div></div>` : ''}
      <div class="footer">
        <div class="summary">
          <span>العدد الكلي</span>
          <span class="count">${piecesTotal} قطعة</span>
        </div>
        <div class="hint">إذا تعذرت الطباعة أو ألغيت فلا يتوقف التشغيل. يمكنك إغلاق النافذة ومتابعة التنفيذ اليدوي مباشرة.</div>
      </div>
    </div>
  </div>
</body>
</html>`);
  popup.document.close();
  popup.focus();
  window.setTimeout(() => popup.print(), 250);
}

function renderOrderFollowupContent(order: Order, autoNotifyTeam: boolean) {
  const dispatchTag = resolveDeliveryDispatchSupplementalTag(order, autoNotifyTeam);
  const settlementLabel = deliverySettlementStatusLabel(order.delivery_settlement_status);
  const failureResolution = deliveryFailureResolutionLabel(order.delivery_failure_resolution_status);
  const hasFollowupState =
    (order.type === 'delivery' && order.status === 'DELIVERY_FAILED' && !order.delivery_failure_resolution_status) ||
    Boolean(dispatchTag) ||
    Boolean(failureResolution) ||
    Boolean(settlementLabel);

  return (
    <div className="flex flex-wrap justify-center gap-1.5 md:justify-start">
        {order.type === 'delivery' && order.status === 'DELIVERY_FAILED' && !order.delivery_failure_resolution_status ? (
          <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} border-rose-300 bg-rose-100 text-rose-900`}>
            قرار الإدارة مطلوب
          </span>
        ) : null}
        {dispatchTag ? (
          <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${dispatchTag.className}`}>
            {dispatchTag.label}
          </span>
        ) : null}
        {failureResolution ? (
          <span className={deliveryFailureResolutionClasses(order.delivery_failure_resolution_status)}>{failureResolution}</span>
        ) : null}
        {settlementLabel ? (
          <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${deliverySettlementStatusClasses(order.delivery_settlement_status)}`}>
            {settlementLabel}
          </span>
        ) : null}
        {!hasFollowupState ? (
          <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} border-stone-300 bg-stone-100/80 text-stone-700`}>
            لا متابعة
          </span>
        ) : null}
    </div>
  );
}

function OrderDetailsSummary({
  order,
  compact = false,
  showAll = false,
}: {
  order: Order;
  compact?: boolean;
  showAll?: boolean;
}) {
  const maxVisibleItems = showAll ? order.items.length : compact ? 2 : 4;
  const visibleItems = order.items.slice(0, maxVisibleItems);
  const hiddenItemsCount = Math.max(order.items.length - visibleItems.length, 0);

  return (
    <div className={`space-y-1 ${compact ? 'min-w-[210px] max-w-[272px]' : ''}`}>
      <div className={compact ? 'space-y-1' : 'space-y-1.5'}>
        {visibleItems.map((item) => (
          <div
            key={item.id}
            className={`flex items-center justify-between gap-2 rounded-lg border border-[var(--console-border)] bg-[var(--surface-card)] ${
              compact ? 'px-2 py-1' : 'px-2.5 py-1.5'
            }`}
          >
            <span className={`min-w-0 truncate font-semibold text-[var(--text-primary)] ${compact ? 'text-[11px]' : 'text-xs'}`}>
              {sanitizeMojibakeText(item.product_name)}
            </span>
            <span
              className={`inline-flex shrink-0 items-center justify-center rounded-full border border-[#d4a16a] bg-[#fff1dc] font-black text-[#8f5126] ${
                compact ? 'min-w-[34px] px-1.5 py-0.5 text-[10px]' : 'min-w-[38px] px-2 py-0.5 text-[11px]'
              }`}
            >
              ×{item.quantity}
            </span>
          </div>
        ))}
      </div>

      {hiddenItemsCount > 0 ? (
        <p className={`font-semibold text-[var(--text-muted)] ${compact ? 'text-[10px]' : 'text-[11px]'}`}>+{hiddenItemsCount} أصناف أخرى</p>
      ) : null}

    </div>
  );
}

function OrderDetailsPreview({
  order,
  onOpen,
  compact = false,
}: {
  order: Order;
  onOpen: (order: Order) => void;
  compact?: boolean;
}) {
  const previewItems = order.items.slice(0, 2);
  const hiddenItemsCount = Math.max(order.items.length - previewItems.length, 0);

  return (
    <div className={`space-y-2 ${compact ? 'min-w-[180px] max-w-[220px]' : ''}`}>
      <div className="space-y-1">
        {previewItems.map((item) => (
          <div key={item.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 text-right">
            <span className="min-w-0 truncate text-[11px] font-black text-[var(--text-primary-strong)]">
              {sanitizeMojibakeText(item.product_name)}
            </span>
            <span className="inline-flex min-w-[30px] shrink-0 items-center justify-center rounded-full border border-[#d8b189] bg-[#fff4e6] px-1.5 py-0.5 text-[10px] font-black text-[#8f5126]">
              ×{item.quantity}
            </span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
        <span className="min-w-0 text-right text-[10px] font-semibold text-[var(--text-muted)]">
          {hiddenItemsCount > 0 ? `+${hiddenItemsCount} أصناف أخرى` : `${order.items.length} أصناف`}
        </span>
        <button
          type="button"
          onClick={() => onOpen(order)}
          className="inline-flex min-h-[24px] flex-row-reverse items-center justify-center gap-1 rounded-full border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-2 py-0.5 text-[10px] font-black text-[var(--text-secondary)] transition hover:bg-[var(--surface-card-hover)]"
        >
          <Eye className="h-3 w-3" />
          <span>عرض الطلب</span>
        </button>
      </div>
    </div>
  );
}

function CompactOrdersStat({
  label,
  value,
  icon,
  tone = 'default',
}: {
  label: string;
  value: number;
  icon: ReactNode;
  tone?: 'default' | 'warning';
}) {
  const toneClass =
    tone === 'warning'
      ? 'border-amber-300 bg-amber-100/80 text-amber-900'
      : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]';

  return (
    <div dir="rtl" className={`flex min-h-[42px] w-full items-center justify-between gap-2 rounded-xl border px-3 sm:w-auto ${toneClass}`}>
      <div className="flex flex-col items-end text-right leading-none">
        <span className="text-[10px] font-bold opacity-80">{label}</span>
        <span className="mt-1 text-sm font-black">{value}</span>
      </div>
      <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-current/15 bg-white/40">
        {icon}
      </span>
    </div>
  );
}

export function OrdersPage({ scope = 'full', showCreateButton = true, createRequestToken = 0 }: OrdersPageProps) {
  const isConsoleScope = scope === 'console';
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [searchDraft, setSearchDraft] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'all'>(() =>
    isConsoleScope ? 'all' : normalizeStatus(searchParams.get('status'))
  );
  const [typeFilter, setTypeFilter] = useState<OrderType | 'all'>(() =>
    isConsoleScope ? 'all' : normalizeType(searchParams.get('order_type'))
  );
  const [page, setPage] = useState(1);
  const [amountReceived, setAmountReceived] = useState<Record<number, number>>({});
  const [tableSettlementAmounts, setTableSettlementAmounts] = useState<Record<number, string>>({});
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [manualStep, setManualStep] = useState<ManualOrderStep>('type');
  const [manualType, setManualType] = useState<OrderType | null>(null);
  const [manualTableId, setManualTableId] = useState<number | ''>('');
  const [manualPhone, setManualPhone] = useState('');
  const [manualNotes, setManualNotes] = useState('');
  const [manualDeliveryRootId, setManualDeliveryRootId] = useState<number | undefined>(undefined);
  const [manualDeliveryLevel2Id, setManualDeliveryLevel2Id] = useState<number | undefined>(undefined);
  const [manualDeliveryLocalityId, setManualDeliveryLocalityId] = useState<number | undefined>(undefined);
  const [manualDeliverySublocalityId, setManualDeliverySublocalityId] = useState<number | undefined>(undefined);
  const [manualItems, setManualItems] = useState<ManualOrderItemRow[]>([{ product_id: 0, quantity: 1 }]);
  const [manualSecondaryItems, setManualSecondaryItems] = useState<ManualSecondaryItemRow[]>([]);
  const [manualError, setManualError] = useState('');
  const [reasonDialog, setReasonDialog] = useState<ReasonDialogState | null>(null);
  const [reasonStep, setReasonStep] = useState<ReasonDialogStep>('reason');
  const [reasonCode, setReasonCode] = useState('');
  const [reasonNote, setReasonNote] = useState('');
  const [detailsOrder, setDetailsOrder] = useState<Order | null>(null);
  const [dispatchTargetByOrder, setDispatchTargetByOrder] = useState<Record<number, string>>({});
  const lastCreateRequestTokenRef = useRef(createRequestToken);

  const invalidateOperationalQueries = () => {
    const keys: string[] = [
      'manager-orders-paged',
      'manager-active-orders',
      'manager-tables',
      'manager-dashboard-operational-heart',
      'manager-dashboard-smart-orders',
      'manager-kitchen-monitor-paged',
      'manager-financial',
      'manager-delivery-settlements',
      'manager-table-sessions',
      'manager-cashbox-movements',
      'manager-orders-delivery',
      'delivery-orders',
      'delivery-assignments',
      'manager-drivers',
      'manager-delivery-providers',
      'manager-delivery-policies',
      'manager-operational-capabilities',
      'public-operational-capabilities',
      'public-tables',
    ];
    for (const key of keys) {
      queryClient.invalidateQueries({ queryKey: [key] });
    }
    queryClient.invalidateQueries({ queryKey: ['public-table-session'] });
  };

  const resetReasonDialog = () => {
    setReasonDialog(null);
    setReasonStep('reason');
    setReasonCode('');
    setReasonNote('');
  };

  const applySearch = () => {
    setSearch(searchDraft.trim());
    setPage(1);
  };

  const resetOrderFilters = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('status');
    nextParams.delete('order_type');
    setSearch('');
    setSearchDraft('');
    setPage(1);
    setSearchParams(nextParams, { replace: true });
  };

  const openReasonDialog = (mode: ReasonDialogState['mode'], order: Order) => {
    const defaults = mode === 'cancel' ? cancellationReasonOptions : emergencyFailReasonOptions;
    setReasonDialog({ mode, order });
    setReasonStep('reason');
    setReasonCode(defaults[0]?.value ?? '');
    setReasonNote('');
  };

  const consoleNeedsPagedResults =
    !isConsoleScope ||
    search.trim().length > 0 ||
    (statusFilter !== 'all' && !isActiveStatus(statusFilter));

  const ordersQuery = useQuery({
    queryKey: ['manager-orders-paged', page, search, sortBy, sortDirection, statusFilter, typeFilter],
    queryFn: () =>
      orderApi.getOrdersPaged(role ?? 'manager', {
        page,
        pageSize: PAGE_SIZE,
        search,
        sortBy: sortBy as 'created_at' | 'total' | 'status' | 'id',
        sortDirection,
        status: statusFilter === 'all' ? undefined : statusFilter,
        orderType: typeFilter === 'all' ? undefined : typeFilter,
      }),
    enabled: role === 'manager' && consoleNeedsPagedResults,
    // Orders board must keep refreshing continuously in operational console mode.
    refetchInterval: LIVE_ORDERS_REFETCH_MS,
    refetchIntervalInBackground: true,
    staleTime: 0,
    refetchOnWindowFocus: 'always',
  });

  const activeOrdersQuery = useQuery({
    queryKey: ['manager-active-orders', typeFilter, sortBy, sortDirection],
    queryFn: () => orderApi.getActiveOrders(role ?? 'manager', 200),
    enabled: role === 'manager' && isConsoleScope && !consoleNeedsPagedResults,
    refetchInterval: LIVE_ORDERS_REFETCH_MS,
    refetchIntervalInBackground: true,
    staleTime: 0,
    refetchOnWindowFocus: 'always',
  });

  const capabilitiesQuery = useQuery({
    queryKey: ['manager-operational-capabilities'],
    queryFn: () => orderApi.getOperationalCapabilities(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(3000),
  });

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context'],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });

  const deliveryChannelEnabled =
    tenantContextQuery.isSuccess && (tenantContextQuery.data?.channel_modes?.delivery ?? 'disabled') === 'core';

  const deliveryPoliciesQuery = useQuery({
    queryKey: ['manager-delivery-policies'],
    queryFn: () => api.managerDeliveryPolicies(role ?? 'manager'),
    enabled: role === 'manager' && deliveryChannelEnabled,
  });

  const deliveryProvidersQuery = useQuery({
    queryKey: ['manager-delivery-providers'],
    queryFn: () => api.managerDeliveryProviders(role ?? 'manager'),
    enabled: role === 'manager' && deliveryChannelEnabled,
  });

  const deliveryDriversQuery = useQuery({
    queryKey: ['manager-drivers'],
    queryFn: () => api.managerDrivers(role ?? 'manager'),
    enabled: role === 'manager' && deliveryChannelEnabled,
  });

  const productsQuery = useQuery({
    queryKey: ['manager-products', 'all'],
    queryFn: () => productApi.getManagerProducts(role ?? 'manager', 'all'),
    enabled: role === 'manager',
  });

  const tablesQuery = useQuery({
    queryKey: ['public-tables'],
    queryFn: () => tableApi.getPublicTables(),
    enabled: role === 'manager',
  });

  const deliverySettingsQuery = useQuery({
    queryKey: ['manager-delivery-settings'],
    queryFn: () => api.managerDeliverySettings(role ?? 'manager'),
    enabled: role === 'manager' && deliveryChannelEnabled,
  });

  const manualDeliveryRootNodesQuery = useQuery({
    queryKey: ['manager-delivery-address-nodes', 'manual-order-root'],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager'),
    enabled: role === 'manager' && deliveryChannelEnabled && isManualModalOpen && manualType === 'delivery',
  });

  const manualDeliveryLevel2NodesQuery = useQuery({
    queryKey: ['manager-delivery-address-nodes', 'manual-order-level2', manualDeliveryRootId],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager', manualDeliveryRootId),
    enabled:
      role === 'manager' &&
      deliveryChannelEnabled &&
      isManualModalOpen &&
      manualType === 'delivery' &&
      manualDeliveryRootId !== undefined,
  });

  const manualDeliveryLocalityNodesQuery = useQuery({
    queryKey: ['manager-delivery-address-nodes', 'manual-order-locality', manualDeliveryLevel2Id],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager', manualDeliveryLevel2Id),
    enabled:
      role === 'manager' &&
      deliveryChannelEnabled &&
      isManualModalOpen &&
      manualType === 'delivery' &&
      manualDeliveryLevel2Id !== undefined,
  });

  const manualDeliverySublocalityNodesQuery = useQuery({
    queryKey: ['manager-delivery-address-nodes', 'manual-order-sublocality', manualDeliveryLocalityId],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager', manualDeliveryLocalityId),
    enabled:
      role === 'manager' &&
      deliveryChannelEnabled &&
      isManualModalOpen &&
      manualType === 'delivery' &&
      manualDeliveryLocalityId !== undefined,
  });

  const transitionMutation = useMutation({
    mutationFn: ({
      orderId,
      targetStatus,
      amount,
      collectPayment,
      reasonCode,
      reasonNote,
    }: {
      orderId: number;
      targetStatus: OrderStatus;
      amount?: number;
      collectPayment?: boolean;
      reasonCode?: string;
      reasonNote?: string;
    }) => orderApi.transitionOrder(role ?? 'manager', orderId, targetStatus, amount, collectPayment, reasonCode, reasonNote),
    onSuccess: () => {
      invalidateOperationalQueries();
      resetReasonDialog();
    },
  });

  const notifyTeamMutation = useMutation({
    mutationFn: (orderId: number) => orderApi.notifyDeliveryTeam(role ?? 'manager', orderId),
    onSuccess: invalidateOperationalQueries,
  });

  const createDispatchMutation = useMutation({
    mutationFn: (payload: { order_id: number; provider_id?: number; driver_id?: number }) =>
      api.managerCreateDeliveryDispatch(role ?? 'manager', payload),
    onSuccess: invalidateOperationalQueries,
  });

  const cancelDispatchMutation = useMutation({
    mutationFn: (dispatchId: number) => api.managerCancelDeliveryDispatch(role ?? 'manager', dispatchId),
    onSuccess: invalidateOperationalQueries,
  });

  const emergencyDeliveryFailMutation = useMutation({
    mutationFn: ({
      orderId,
      reasonCode,
      reasonNote,
    }: {
      orderId: number;
      reasonCode: string;
      reasonNote?: string;
    }) => orderApi.emergencyDeliveryFail(role ?? 'manager', orderId, reasonCode, reasonNote),
    onSuccess: () => {
      invalidateOperationalQueries();
      resetReasonDialog();
    },
  });

  const collectPaymentMutation = useMutation({
    mutationFn: ({ orderId, amount }: { orderId: number; amount?: number }) =>
      orderApi.collectOrderPayment(role ?? 'manager', orderId, amount),
    onSuccess: invalidateOperationalQueries,
    onError: invalidateOperationalQueries,
  });

  const settleDeliveryMutation = useMutation({
    mutationFn: (orderId: number) => orderApi.settleDeliveryOrder(role ?? 'manager', orderId),
    onSuccess: invalidateOperationalQueries,
  });

  const resolveDeliveryFailureMutation = useMutation({
    mutationFn: ({
      orderId,
      resolutionAction,
    }: {
      orderId: number;
      resolutionAction: 'retry_delivery' | 'convert_to_takeaway' | 'close_failure';
    }) => orderApi.resolveDeliveryFailure(role ?? 'manager', orderId, resolutionAction),
    onSuccess: invalidateOperationalQueries,
  });

  const settleTableSessionMutation = useMutation({
    mutationFn: ({ tableId, amount }: { tableId: number; amount?: number }) =>
      tableApi.settleTableSession(role ?? 'manager', tableId, amount),
    onSuccess: (result) => {
      invalidateOperationalQueries();
      setTableSettlementAmounts((prev) => {
        const next = { ...prev };
        delete next[result.table_id];
        return next;
      });
    },
  });

  const resetManualForm = () => {
    setManualStep('type');
    setManualType(null);
    setManualTableId('');
    setManualPhone('');
    setManualNotes('');
    setManualDeliveryRootId(undefined);
    setManualDeliveryLevel2Id(undefined);
    setManualDeliveryLocalityId(undefined);
    setManualDeliverySublocalityId(undefined);
    setManualItems([{ product_id: 0, quantity: 1 }]);
    setManualSecondaryItems([]);
    setManualError('');
  };

  const operationalCapabilities = capabilitiesQuery.data;
  const activationStageId = tenantContextQuery.data?.activation_stage_id ?? operationalCapabilities?.activation_stage_id ?? 'base';
  const deliveryFeatureEnabled = operationalCapabilities?.delivery_feature_enabled ?? false;
  const deliveryEnabled = deliveryChannelEnabled && (operationalCapabilities?.delivery_enabled ?? false);
  const deliveryRuntimeBlocked = deliveryFeatureEnabled && !deliveryEnabled;
  const autoNotifyTeam = deliveryPoliciesQuery.data?.auto_notify_team ?? false;
  const deliveryProviders: DeliveryProvider[] = deliveryProvidersQuery.data ?? [];
  const deliveryDrivers: DeliveryDriver[] = deliveryDriversQuery.data ?? [];
  const deliveryBlockedReason = sanitizeMojibakeText(
    deliveryChannelEnabled ? operationalCapabilities?.delivery_block_reason : 'نظام التوصيل غير مفعّل في النسخة الحالية.',
    fallbackDeliveryBlockedReason
  );

  const submitDispatchFromOrders = async (order: Order, dispatchValue: string) => {
    const [targetType, rawId] = dispatchValue.split(':');
    const targetId = Number(rawId);
    if (!targetType || !Number.isFinite(targetId)) {
      return;
    }
    if (isAwaitingDispatchSelection(order, autoNotifyTeam)) {
      await notifyTeamMutation.mutateAsync(order.id);
    }
    await createDispatchMutation.mutateAsync({
      order_id: order.id,
      provider_id: targetType === 'provider' ? targetId : undefined,
      driver_id: targetType === 'driver' ? targetId : undefined,
    });
  };

  const openManualModal = () => {
    resetManualForm();
    setIsManualModalOpen(true);
  };

  const closeManualModal = () => {
    setIsManualModalOpen(false);
    resetManualForm();
  };

  useEffect(() => {
    setSearchDraft(search);
  }, [search]);

  useEffect(() => {
    if (searchDraft.trim().length === 0 && search.trim().length > 0) {
      setSearch('');
      setPage(1);
    }
  }, [searchDraft, search]);

  useEffect(() => {
    if (isConsoleScope) {
      return;
    }
    const nextStatus = normalizeStatus(searchParams.get('status'));
    if (nextStatus !== statusFilter) {
      setStatusFilter(nextStatus);
      setPage(1);
    }

    const nextType = normalizeType(searchParams.get('order_type'));
    if (nextType !== typeFilter) {
      setTypeFilter(nextType);
      setPage(1);
    }

    if (searchParams.get('new') === '1') {
      resetManualForm();
      setIsManualModalOpen(true);
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('new');
      setSearchParams(nextParams, { replace: true });
    }
  }, [isConsoleScope, searchParams, setSearchParams, statusFilter, typeFilter]);

  useEffect(() => {
    if (!deliveryEnabled && manualType === 'delivery') {
      setManualType(null);
    }
  }, [deliveryEnabled, manualType]);

  useEffect(() => {
    if (createRequestToken <= 0 || createRequestToken === lastCreateRequestTokenRef.current) {
      return;
    }
    lastCreateRequestTokenRef.current = createRequestToken;
    openManualModal();
  }, [createRequestToken]);

  const manualCreateMutation = useMutation({
    mutationFn: (payload: CreateOrderPayload) => orderApi.createManualOrder(role ?? 'manager', payload),
    onSuccess: () => {
      invalidateOperationalQueries();
      closeManualModal();
    },
    onError: (error) => {
      setManualError(error instanceof Error ? error.message : 'تعذر إنشاء الطلب يدويًا.');
    },
  });

  const availableManualProducts = useMemo<Product[]>(
    () => (productsQuery.data ?? []).filter((product) => product.available && !product.is_archived),
    [productsQuery.data]
  );
  const availableManualPrimaryProducts = useMemo<Product[]>(
    () => availableManualProducts.filter((product) => product.kind === 'primary'),
    [availableManualProducts]
  );
  const availableManualSecondaryProducts = useMemo<Product[]>(
    () => availableManualProducts.filter((product) => product.kind === 'secondary'),
    [availableManualProducts]
  );
  const availableManualProductsMap = useMemo(
    () => new Map<number, Product>(availableManualProducts.map((product) => [product.id, product])),
    [availableManualProducts]
  );

  const tableOptions = useMemo<TableInfo[]>(() => {
    const rows = tablesQuery.data ?? [];
    return rows.filter((table) => table.status !== 'occupied' || table.id === manualTableId);
  }, [manualTableId, tablesQuery.data]);

  const manualDeliveryRootNodes = manualDeliveryRootNodesQuery.data?.items ?? [];
  const manualDeliveryLevel2Nodes = manualDeliveryLevel2NodesQuery.data?.items ?? [];
  const manualDeliveryLocalityNodes = manualDeliveryLocalityNodesQuery.data?.items ?? [];
  const manualDeliverySublocalityNodes = manualDeliverySublocalityNodesQuery.data?.items ?? [];

  const selectedManualRootNode =
    manualDeliveryRootNodes.find((node) => node.id === manualDeliveryRootId) ?? null;
  const selectedManualLevel2Node =
    manualDeliveryLevel2Nodes.find((node) => node.id === manualDeliveryLevel2Id) ?? null;
  const selectedManualLocalityNode =
    manualDeliveryLocalityNodes.find((node) => node.id === manualDeliveryLocalityId) ?? null;
  const selectedManualSublocalityNode =
    manualDeliverySublocalityNodes.find((node) => node.id === manualDeliverySublocalityId) ?? null;

  const selectedManualDeliveryNode =
    selectedManualSublocalityNode ??
    selectedManualLocalityNode ??
    selectedManualLevel2Node ??
    selectedManualRootNode;

  const manualDeliveryAddressSummary = [
    selectedManualRootNode,
    selectedManualLevel2Node,
    selectedManualLocalityNode,
    selectedManualSublocalityNode,
  ]
    .filter(Boolean)
    .map((node) => node!.display_name)
    .join(' / ');

  const manualDeliverySelectionIncomplete =
    (selectedManualRootNode?.can_expand === true && !selectedManualLevel2Node) ||
    (selectedManualLevel2Node?.can_expand === true && !selectedManualLocalityNode) ||
    (selectedManualLocalityNode?.can_expand === true && !selectedManualSublocalityNode);

  const manualDeliveryQuoteQuery = useQuery({
    queryKey: ['manager-delivery-address-pricing-quote', 'manual-order', selectedManualDeliveryNode?.id],
    queryFn: () => api.managerQuoteDeliveryAddressPricing(role ?? 'manager', selectedManualDeliveryNode?.id),
    enabled: role === 'manager' && isManualModalOpen && manualType === 'delivery' && selectedManualDeliveryNode !== null,
  });

  const manualTotal = useMemo(() => {
    const primaryTotal = manualItems.reduce((sum, item) => {
      const product = availableManualProductsMap.get(item.product_id);
      if (!product || item.quantity <= 0) {
        return sum;
      }
      return sum + product.price * item.quantity;
    }, 0);
    const secondaryTotal = manualSecondaryItems.reduce((sum, item) => {
      const product = availableManualProductsMap.get(item.product_id);
      if (!product || product.kind !== 'secondary' || item.quantity <= 0) {
        return sum;
      }
      return sum + product.price * item.quantity;
    }, 0);
    return primaryTotal + secondaryTotal;
  }, [availableManualProductsMap, manualItems, manualSecondaryItems]);

  const validManualPrimaryItemsCount = useMemo(
    () =>
      manualItems.filter((item) => {
        const selectedProduct = availableManualProductsMap.get(item.product_id);
        return Boolean(selectedProduct && selectedProduct.kind === 'primary' && item.quantity > 0);
      }).length,
    [availableManualProductsMap, manualItems],
  );

  const manualHasSecondaryStage = availableManualSecondaryProducts.length > 0;

  const validateManualDetails = (): string | null => {
    if (!manualType) {
      return 'يرجى اختيار نوع الطلب أولاً.';
    }

    if (manualType === 'delivery' && !deliveryEnabled) {
      return deliveryBlockedReason;
    }

    if (manualType === 'dine-in') {
      if (!manualTableId) {
        return 'اختر الطاولة أولاً.';
      }
      return null;
    }

    const phone = manualPhone.trim();
    if (manualType === 'delivery' && !phone) {
      return 'رقم الهاتف مطلوب لطلبات التوصيل.';
    }

    if (manualType === 'delivery') {
      if (!deliverySettingsQuery.data?.structured_locations_enabled) {
        return 'لا يمكن إنشاء طلب توصيل قبل ضبط شجرة العناوين في إعدادات التوصيل.';
      }
      if (manualDeliveryRootNodes.length === 0) {
        return 'لا توجد عناوين توصيل منشورة بعد.';
      }
      if (!selectedManualDeliveryNode || !manualDeliveryAddressSummary) {
        return 'اختر عنوان التوصيل من الشجرة.';
      }
      if (manualDeliverySelectionIncomplete) {
        return 'أكمل اختيار العنوان حتى تصل إلى آخر عقدة مناسبة.';
      }
      if (manualDeliveryQuoteQuery.isLoading) {
        return 'انتظر حتى يتم احتساب رسوم التوصيل لهذا العنوان.';
      }
      if (!manualDeliveryQuoteQuery.data?.available || !manualDeliveryQuoteQuery.data.location_key) {
        return sanitizeMojibakeText(
          manualDeliveryQuoteQuery.data?.message,
          'هذا العنوان غير مغطى ضمن قواعد التوصيل الحالية.',
        );
      }
    }

    return null;
  };

  const validateManualItems = (): string | null => {
    if (validManualPrimaryItemsCount === 0) {
      return 'أضف منتجًا أساسيًا واحدًا على الأقل مع كمية صحيحة.';
    }
    return null;
  };

  const buildManualOrderPayload = (): { payload: CreateOrderPayload | null; error: string | null } => {
    const detailsError = validateManualDetails();
    if (detailsError) {
      return { payload: null, error: detailsError };
    }

    const itemsError = validateManualItems();
    if (itemsError) {
      return { payload: null, error: itemsError };
    }

    if (!manualType) {
      return { payload: null, error: 'يرجى اختيار نوع الطلب أولاً.' };
    }

    const primaryRows = manualItems.flatMap((item) => {
      if (item.product_id <= 0 || item.quantity <= 0) {
        return [];
      }

      const selectedProduct = availableManualProductsMap.get(item.product_id);
      if (!selectedProduct || selectedProduct.kind !== 'primary') {
        return [];
      }

      return [{
        product_id: item.product_id,
        quantity: item.quantity,
      }];
    });

    const secondaryRows = manualSecondaryItems.flatMap((item) => {
      if (item.product_id <= 0 || item.quantity <= 0) {
        return [];
      }

      const selectedProduct = availableManualProductsMap.get(item.product_id);
      if (!selectedProduct || selectedProduct.kind !== 'secondary') {
        return [];
      }

      return [{
        product_id: item.product_id,
        quantity: item.quantity,
      }];
    });

    const payload: CreateOrderPayload = {
      type: manualType,
      items: [...primaryRows, ...secondaryRows],
      notes: manualNotes.trim() || undefined,
    };

    if (manualType === 'dine-in') {
      payload.table_id = Number(manualTableId);
    } else {
      const phone = manualPhone.trim();
      if (phone) {
        payload.phone = phone;
      }
    }

    if (manualType === 'delivery' && manualDeliveryQuoteQuery.data?.location_key) {
      payload.address = manualDeliveryAddressSummary;
      payload.delivery_location_key = manualDeliveryQuoteQuery.data.location_key;
    }

    return { payload, error: null };
  };

  const manualDetailsError = manualType ? validateManualDetails() : null;
  const manualItemsError = manualType ? validateManualItems() : null;
  const manualDetailsReady = manualType ? !manualDetailsError : false;
  const manualItemsReady = manualType ? !manualItemsError : false;
  const manualReviewState = manualType ? buildManualOrderPayload() : { payload: null, error: null };

  const activeRows = useMemo(() => {
    if (!isConsoleScope || consoleNeedsPagedResults) {
      return [];
    }
    const source = activeOrdersQuery.data ?? [];
    const filtered = source.filter((order) => {
      if (statusFilter !== 'all' && order.status !== statusFilter) {
        return false;
      }
      if (typeFilter !== 'all' && order.type !== typeFilter) {
        return false;
      }
      return true;
    });
    return [...filtered].sort((a, b) =>
      compareOrders(a, b, sortBy as 'created_at' | 'total' | 'status' | 'id', sortDirection)
    );
  }, [activeOrdersQuery.data, consoleNeedsPagedResults, isConsoleScope, sortBy, sortDirection, statusFilter, typeFilter]);

  const activeRowsPage = useMemo(() => {
    const offset = (page - 1) * PAGE_SIZE;
    return activeRows.slice(offset, offset + PAGE_SIZE);
  }, [activeRows, page]);

  const rows = consoleNeedsPagedResults
    ? ordersQuery.data?.items ?? []
    : activeRowsPage;
  const totalRows = consoleNeedsPagedResults ? ordersQuery.data?.total ?? 0 : activeRows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / PAGE_SIZE));
  const visibleOrders = consoleNeedsPagedResults ? ordersQuery.data?.items ?? [] : activeRows;
  const deliveryPendingCount = rows.filter(
    (order) => order.type === 'delivery' && order.delivery_settlement_status === 'pending'
  ).length;
  const unresolvedDeliveryFailureCount = visibleOrders.filter(
    (order) =>
      order.type === 'delivery' &&
      order.status === 'DELIVERY_FAILED' &&
      !order.delivery_failure_resolution_status,
  ).length;

  const syncFilterParam = (key: 'status' | 'order_type', value: string) => {
    if (isConsoleScope) {
      if (key === 'status') {
        setStatusFilter(value && value !== 'all' ? (value as OrderStatus) : 'all');
      } else {
        setTypeFilter(value && value !== 'all' ? (value as OrderType) : 'all');
      }
      setPage(1);
      return;
    }
    const nextParams = new URLSearchParams(searchParams);
    if (!value || value === 'all') {
      nextParams.delete(key);
    } else {
      nextParams.set(key, value);
    }
    setSearchParams(nextParams, { replace: true });
  };

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const submitManualOrder = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setManualError('');
    const { payload, error } = buildManualOrderPayload();
    if (!payload) {
      setManualError(error ?? 'تعذر تجهيز الطلب.');
      return;
    }

    manualCreateMutation.mutate(payload);
  };

  const activeReasonOptions = reasonDialog?.mode === 'emergency_fail' ? emergencyFailReasonOptions : cancellationReasonOptions;

  const submitReasonAction = () => {
    if (!reasonDialog || !reasonCode) {
      return;
    }
    const normalizedNote = reasonNote.trim() || undefined;
    if (reasonDialog.mode === 'cancel') {
      transitionMutation.mutate({
        orderId: reasonDialog.order.id,
        targetStatus: 'CANCELED',
        reasonCode,
        reasonNote: normalizedNote,
      });
      return;
    }
    emergencyDeliveryFailMutation.mutate({
      orderId: reasonDialog.order.id,
      reasonCode,
      reasonNote: normalizedNote,
    });
  };

  const renderOrderActions = (order: Order) => {
    const primaryActions: ReactNode[] = [];
    const controlBlocks: ReactNode[] = [];
    const helperNotes: ReactNode[] = [];
    let printAction: ReactNode | null = null;

    const workflowProfile = resolveOperationalWorkflowProfile(activationStageId, order.type);
    const normalizedManagerActions = managerActions(order.status, order.type, workflowProfile);

    normalizedManagerActions.forEach((action) => {
      const button = (
        <button
          key={`transition-${order.id}-${action.target}`}
          type="button"
          disabled={transitionMutation.isPending}
          onClick={() => {
            if (action.target === 'CANCELED') {
              openReasonDialog('cancel', order);
              return;
            }
            transitionMutation.mutate({
              orderId: order.id,
              targetStatus: action.target,
              amount: action.target === 'DELIVERED' && order.type === 'takeaway' ? amountReceived[order.id] ?? order.total : undefined,
            });
          }}
          className={`${TABLE_ACTION_BUTTON_BASE} ${actionButtonClasses(action.target)}`}
        >
          <span>{action.label}</span>
        </button>
      );
      primaryActions.push(button);
    });

    if (
      order.type === 'delivery' &&
      (order.status === 'IN_PREPARATION' || order.status === 'READY') &&
      !order.delivery_team_notified_at &&
      deliveryEnabled &&
      autoNotifyTeam &&
      !hasActiveDeliveryAssignment(order)
    ) {
      primaryActions.push(
        <button
          key={`notify-team-${order.id}`}
          type="button"
          disabled={notifyTeamMutation.isPending}
          onClick={() => notifyTeamMutation.mutate(order.id)}
          className={`${TABLE_ACTION_BUTTON_BASE} border-cyan-300 bg-cyan-100/80 text-cyan-900 hover:bg-cyan-100`}
        >
          <span>{notifyTeamMutation.isPending ? 'جارٍ التبليغ...' : 'تبليغ فريق التوصيل'}</span>
        </button>,
      );
    }

    if (order.type === 'delivery' && deliveryEnabled) {
      controlBlocks.push(
        <DeliveryDispatchAction
          order={order}
          providers={deliveryProviders}
          drivers={deliveryDrivers}
          autoNotifyTeam={autoNotifyTeam}
          selectedValue={dispatchTargetByOrder[order.id] ?? ''}
          onSelectedValueChange={(value) =>
            setDispatchTargetByOrder((prev) => ({
              ...prev,
              [order.id]: value,
            }))
          }
          onSubmit={() => void submitDispatchFromOrders(order, dispatchTargetByOrder[order.id] ?? '')}
          onCancel={(dispatchId) => cancelDispatchMutation.mutate(dispatchId)}
          submitPending={notifyTeamMutation.isPending || createDispatchMutation.isPending}
          cancelPending={cancelDispatchMutation.isPending}
          compact
        />,
      );
    }

    if (
      order.type === 'delivery' &&
      !deliveryEnabled &&
      (order.status === 'IN_PREPARATION' || order.status === 'READY' || order.status === 'OUT_FOR_DELIVERY')
    ) {
      primaryActions.push(
        <button
          key={`emergency-delivery-fail-${order.id}`}
          type="button"
          disabled={emergencyDeliveryFailMutation.isPending}
          onClick={() => openReasonDialog('emergency_fail', order)}
          className={`${TABLE_ACTION_BUTTON_BASE} border-rose-300 bg-rose-100/80 text-rose-900 hover:bg-rose-100`}
        >
          <span>{emergencyDeliveryFailMutation.isPending ? 'جارٍ الإغلاق...' : 'إغلاق طارئ (فشل توصيل)'}</span>
        </button>,
      );
    }

    if (order.status === 'READY' && order.type === 'takeaway') {
      controlBlocks.push(
        <label
          key={`amount-received-${order.id}`}
          className="flex w-full flex-col gap-1 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-right"
        >
          <span className="text-[11px] font-bold text-[var(--text-secondary)]">المبلغ المستلم</span>
          <input
            type="number"
            min={0.01}
            step="0.1"
            value={amountReceived[order.id] ?? order.total}
            onChange={(event) => setAmountReceived((prev) => ({ ...prev, [order.id]: Number(event.target.value) }))}
            className="form-input ui-size-sm w-full"
          />
        </label>,
      );
      primaryActions.push(
        <button
          key={`deliver-without-collect-${order.id}`}
          type="button"
          disabled={transitionMutation.isPending}
          onClick={() =>
            transitionMutation.mutate({
              orderId: order.id,
              targetStatus: 'DELIVERED',
              collectPayment: false,
            })
          }
          className={`${TABLE_ACTION_BUTTON_BASE} border-stone-300 bg-stone-100/80 text-stone-800 hover:bg-stone-100`}
        >
          <span>تسليم بدون تحصيل</span>
        </button>,
      );
    }

    if (order.status === 'DELIVERED' && order.type !== 'dine-in' && order.payment_status !== 'paid') {
      controlBlocks.push(
        <div key={`collect-payment-${order.id}`} className="flex w-full flex-col gap-2 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-2.5 md:flex-row md:items-end">
          <label className="flex min-w-0 flex-1 flex-col gap-1 text-right">
            <span className="text-[11px] font-bold text-[var(--text-secondary)]">تحصيل لاحق</span>
            <input
              type="number"
              min={0.01}
              step="0.1"
              value={amountReceived[order.id] ?? order.total}
              onChange={(event) => setAmountReceived((prev) => ({ ...prev, [order.id]: Number(event.target.value) }))}
              className="form-input ui-size-sm w-full"
            />
          </label>
          <button
            type="button"
            disabled={collectPaymentMutation.isPending}
            onClick={() =>
              collectPaymentMutation.mutate({
                orderId: order.id,
                amount: amountReceived[order.id] ?? order.total,
              })
            }
            className={`${TABLE_ACTION_BUTTON_BASE} border-emerald-300 bg-emerald-100/80 text-emerald-900 hover:bg-emerald-100`}
          >
            <span>{collectPaymentMutation.isPending ? 'جارٍ التحصيل...' : 'تحصيل الآن'}</span>
          </button>
        </div>,
      );
    }

    if (order.type === 'dine-in' && order.status === 'DELIVERED' && order.payment_status !== 'paid' && order.table_id) {
      controlBlocks.push(
        <div key={`settle-table-${order.id}`} className="flex w-full flex-col gap-2 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-2.5 md:flex-row md:items-end">
          <label className="flex min-w-0 flex-1 flex-col gap-1 text-right">
            <span className="text-[11px] font-bold text-[var(--text-secondary)]">مبلغ الجلسة</span>
            <input
              type="number"
              min={order.total}
              step="0.1"
              value={tableSettlementAmounts[order.table_id] ?? ''}
              onChange={(event) =>
                setTableSettlementAmounts((prev) => ({
                  ...prev,
                  [order.table_id!]: event.target.value,
                }))
              }
              className="form-input ui-size-sm w-full"
              placeholder="اختياري"
            />
          </label>
          <button
            type="button"
            disabled={settleTableSessionMutation.isPending}
            onClick={() => {
              const value = tableSettlementAmounts[order.table_id!];
              const parsed = Number(value);
              const amount = value && Number.isFinite(parsed) ? parsed : undefined;
              settleTableSessionMutation.mutate({ tableId: order.table_id!, amount });
            }}
            className={`${TABLE_ACTION_BUTTON_BASE} border-emerald-300 bg-emerald-100/80 text-emerald-900 hover:bg-emerald-100`}
          >
            <span>{settleTableSessionMutation.isPending ? 'جارٍ تسوية الجلسة...' : `تسوية الطاولة ${order.table_id}`}</span>
          </button>
        </div>,
      );
    }

    if (order.type === 'delivery' && order.status === 'DELIVERY_FAILED' && !order.delivery_failure_resolution_status) {
      primaryActions.push(
        <button
          key={`resolve-delivery-retry-${order.id}`}
          type="button"
          disabled={resolveDeliveryFailureMutation.isPending}
          onClick={() =>
            resolveDeliveryFailureMutation.mutate({
              orderId: order.id,
              resolutionAction: 'retry_delivery',
            })
          }
          className={`${TABLE_ACTION_BUTTON_BASE} border-sky-300 bg-sky-100/80 text-sky-900 hover:bg-sky-100`}
        >
          <span>{resolveDeliveryFailureMutation.isPending ? 'جارٍ التنفيذ...' : 'إعادة التوصيل'}</span>
        </button>,
      );
      primaryActions.push(
        <button
          key={`resolve-delivery-convert-${order.id}`}
          type="button"
          disabled={resolveDeliveryFailureMutation.isPending}
          onClick={() =>
            resolveDeliveryFailureMutation.mutate({
              orderId: order.id,
              resolutionAction: 'convert_to_takeaway',
            })
          }
          className={`${TABLE_ACTION_BUTTON_BASE} border-amber-300 bg-amber-100/80 text-amber-900 hover:bg-amber-100`}
        >
          <span>{resolveDeliveryFailureMutation.isPending ? 'جارٍ التنفيذ...' : 'تحويل إلى استلام'}</span>
        </button>,
      );
      primaryActions.push(
        <button
          key={`resolve-delivery-close-${order.id}`}
          type="button"
          disabled={resolveDeliveryFailureMutation.isPending}
          onClick={() =>
            resolveDeliveryFailureMutation.mutate({
              orderId: order.id,
              resolutionAction: 'close_failure',
            })
          }
          className={`${TABLE_ACTION_BUTTON_BASE} border-stone-300 bg-stone-100/80 text-stone-800 hover:bg-stone-100`}
        >
          <span>{resolveDeliveryFailureMutation.isPending ? 'جارٍ الإغلاق...' : 'إغلاق نهائي'}</span>
        </button>,
      );
    }

    if (
      order.type === 'delivery' &&
      order.status === 'DELIVERED' &&
      order.delivery_settlement_id &&
      order.delivery_settlement_status !== 'settled' &&
      order.delivery_settlement_status !== 'reversed'
    ) {
      primaryActions.push(
        <button
          key={`settle-delivery-${order.id}`}
          type="button"
          disabled={settleDeliveryMutation.isPending}
          onClick={() => settleDeliveryMutation.mutate(order.id)}
          className={`${TABLE_ACTION_BUTTON_BASE} border-violet-300 bg-violet-100/80 text-violet-900 hover:bg-violet-100`}
        >
          <span>{settleDeliveryMutation.isPending ? 'جارٍ تسوية التوصيل...' : 'تسوية التوصيل'}</span>
        </button>,
      );
    }

    if (workflowProfile === 'base_direct' && order.status !== 'CANCELED') {
      printAction = (
        <button
          key={`print-ticket-${order.id}`}
          type="button"
          onClick={() => openOrderTicketPrintView(order)}
          className={tablePrintIconButtonClass}
          aria-label="طباعة"
          title="طباعة"
        >
          <Printer className="h-4 w-4" />
        </button>
      );
    }

    if (!primaryActions.length && !controlBlocks.length && !printAction) {
      helperNotes.push(
        <span
          key={`note-${order.id}`}
          className={`${TABLE_STATUS_CHIP_BORDER_BASE} border-stone-300 bg-stone-100/80 text-stone-700`}
        >
          لا إجراء الآن
        </span>,
      );
    }

    if (!primaryActions.length && !controlBlocks.length && !printAction && helperNotes.length) {
      return <div className="flex w-full items-center justify-center">{helperNotes}</div>;
    }

    return (
      <div className="flex w-full min-w-0 flex-col gap-2 md:min-w-[280px] md:max-w-[340px]">
        {primaryActions.length || printAction ? (
          <div className="flex w-full flex-wrap items-center gap-2">
            {primaryActions.map((action, index) => (
              <div
                key={`primary-action-${order.id}-${index}`}
                className="min-w-0 flex-1 basis-[104px] [&>*]:w-full [&>*]:justify-center [&>*]:text-center [&>*]:whitespace-nowrap [&>*]:leading-none"
              >
                {action}
              </div>
            ))}
            {printAction ? <div className="shrink-0">{printAction}</div> : null}
          </div>
        ) : null}
        {controlBlocks.length ? (
          <div className={`grid w-full gap-2 ${primaryActions.length || printAction ? 'border-t border-[#ead7bf] pt-2' : ''}`}>
            {controlBlocks.map((action, index) => (
              <div
                key={`control-action-${order.id}-${index}`}
                className="min-w-0"
              >
                {action}
              </div>
            ))}
          </div>
        ) : null}
        {helperNotes.length ? <div className="flex w-full flex-wrap items-center justify-center gap-2">{helperNotes}</div> : null}
      </div>
    );
  };

  if ((consoleNeedsPagedResults ? ordersQuery.isLoading : activeOrdersQuery.isLoading) && !rows.length) {
    return <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-secondary)]">جارٍ تحميل الطلبات...</div>;
  }

  if (consoleNeedsPagedResults ? ordersQuery.isError : activeOrdersQuery.isError) {
    return <div className="rounded-2xl border border-rose-300 bg-rose-100/80 p-5 text-sm text-rose-900">تعذر تحميل الطلبات.</div>;
  }

  return (
    <PageShell
      className="admin-page orders-modern-surface"
      header={
        <div dir="rtl" className="space-y-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)]/70 px-3 py-3 text-right md:px-4">
          <div className={`grid grid-cols-1 gap-2 ${showCreateButton ? 'xl:grid-cols-[minmax(200px,220px)_minmax(0,1fr)]' : ''}`}>
            {showCreateButton ? (
              <button
                type="button"
                onClick={openManualModal}
                className="btn-primary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
              >
                <Plus className="h-4 w-4" />
                <span>إنشاء طلب جديد</span>
              </button>
            ) : null}

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <CompactOrdersStat
                label="إجمالي النتائج"
                value={totalRows}
                icon={<PackageCheck className="h-4 w-4" />}
              />
              <CompactOrdersStat
                label="بانتظار التسوية"
                value={deliveryPendingCount}
                icon={<Truck className="h-4 w-4" />}
                tone={deliveryPendingCount > 0 ? 'warning' : 'default'}
              />
            </div>
          </div>

          {unresolvedDeliveryFailureCount > 0 ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-300 bg-rose-100/80 px-3 py-2 text-sm font-semibold text-rose-900">
              <span>يوجد {unresolvedDeliveryFailureCount} طلب توصيل فشل ويحتاج قرار معالجة الآن.</span>
                <button
                  type="button"
                  onClick={() => {
                    syncFilterParam('status', 'DELIVERY_FAILED');
                    syncFilterParam('order_type', 'delivery');
                  }}
                className="inline-flex items-center gap-1 rounded-lg border border-rose-300 bg-[var(--surface-card)] px-3 py-1 text-xs font-bold text-rose-900 hover:bg-[var(--surface-card-soft)]"
                >
                  <Eye className="h-3.5 w-3.5" />
                  عرضها الآن
                </button>
              </div>
            ) : null}

          <div className="ops-surface-soft hidden rounded-2xl border p-3 md:block">
            <form
              className="grid gap-2 xl:grid-cols-[minmax(260px,1.2fr)_120px_170px_140px_170px_170px_120px]"
              onSubmit={(event) => {
                event.preventDefault();
                applySearch();
              }}
            >
              <label>
                <span className="form-label">حقل البحث</span>
                <div className="flex min-h-[42px] items-center gap-2 rounded-xl border border-[#d5c3a6] bg-[var(--surface-card)] px-3">
                  <Search className="h-4 w-4 text-[var(--text-secondary)]" />
                  <input
                    value={searchDraft}
                    onChange={(event) => setSearchDraft(event.target.value)}
                    placeholder="ابحث برقم الطلب أو الاسم أو الهاتف"
                    className="w-full border-0 bg-transparent p-0 text-right text-sm font-semibold text-[var(--text-primary)] placeholder:text-[var(--text-secondary)]/75 focus:outline-none"
                  />
                </div>
              </label>

              <div>
                <span className="form-label">تنفيذ</span>
                <button type="submit" className="btn-primary inline-flex min-h-[42px] w-full items-center justify-center gap-2">
                  <Search className="h-4 w-4" />
                  <span>بحث</span>
                </button>
              </div>

              <label>
                <span className="form-label">الترتيب حسب</span>
                <select
                  value={sortBy}
                  onChange={(event) => setSortBy(event.target.value)}
                  className="form-select min-h-[42px] w-full rounded-xl"
                >
                  <option value="created_at">الوقت</option>
                  <option value="status">الحالة</option>
                  <option value="total">المبلغ</option>
                  <option value="id">رقم الطلب</option>
                </select>
              </label>

              <div>
                <span className="form-label">اتجاه الترتيب</span>
                <button
                  type="button"
                  onClick={() => setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))}
                  className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
                >
                  <ArrowDownUp className="h-4 w-4" />
                  <span>{sortDirection === 'asc' ? 'تصاعدي' : 'تنازلي'}</span>
                </button>
              </div>

              <label>
                <span className="form-label">تصفية الحالة</span>
                <select
                  value={statusFilter}
                  onChange={(event) => syncFilterParam('status', event.target.value)}
                  className="form-select min-h-[42px] w-full rounded-xl"
                >
                  <option value="all">كل الحالات</option>
                  <option value="CREATED">تم الإنشاء</option>
                  <option value="CONFIRMED">تم التأكيد</option>
                  <option value="SENT_TO_KITCHEN">أُرسل للمطبخ</option>
                  <option value="IN_PREPARATION">قيد التحضير</option>
                  <option value="READY">جاهز</option>
                  <option value="OUT_FOR_DELIVERY">خرج للتوصيل</option>
                  <option value="DELIVERED">تم التسليم</option>
                  <option value="DELIVERY_FAILED">فشل التوصيل</option>
                  <option value="CANCELED">ملغى</option>
                </select>
              </label>

              <label>
                <span className="form-label">تصفية النوع</span>
                <select
                  value={typeFilter}
                  onChange={(event) => syncFilterParam('order_type', event.target.value)}
                  className="form-select min-h-[42px] w-full rounded-xl"
                >
                  <option value="all">كل الأنواع</option>
                  <option value="dine-in">داخل المطعم</option>
                  <option value="takeaway">استلام</option>
                  <option value="delivery">توصيل</option>
                </select>
              </label>

              <div>
                <span className="form-label">إعادة الضبط</span>
                <button
                  type="button"
                  className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
                  onClick={resetOrderFilters}
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>مسح</span>
                </button>
              </div>
            </form>
          </div>

          <div className="ops-surface-soft rounded-2xl border p-3 md:hidden">
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                applySearch();
              }}
            >
              <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                <div className="flex min-h-[42px] items-center gap-2 rounded-xl border border-[#d5c3a6] bg-[var(--surface-card)] px-3">
                  <Search className="h-4 w-4 text-[var(--text-secondary)]" />
                  <input
                    value={searchDraft}
                    onChange={(event) => setSearchDraft(event.target.value)}
                    placeholder="ابحث برقم الطلب أو الاسم أو الهاتف"
                    className="w-full border-0 bg-transparent p-0 text-right text-sm font-semibold text-[var(--text-primary)] placeholder:text-[var(--text-secondary)]/75 focus:outline-none"
                  />
                </div>
                <button type="submit" className="btn-primary ui-size-sm inline-flex items-center gap-2 whitespace-nowrap">
                  <Search className="h-4 w-4" />
                  <span>بحث</span>
                </button>
              </div>

              <button
                type="button"
                className="btn-secondary ui-size-sm inline-flex w-full items-center justify-center gap-2"
                onClick={() => setShowAdvancedFilters((current) => !current)}
              >
                <SlidersHorizontal className="h-4 w-4" />
                <span>{showAdvancedFilters ? 'إخفاء الفلاتر المتقدمة' : 'إظهار الفلاتر المتقدمة'}</span>
              </button>
            </form>

            {showAdvancedFilters ? (
              <div className="grid gap-2 pt-1">
                <label className="w-full">
                  <span className="form-label">الترتيب حسب</span>
                  <select
                    value={sortBy}
                    onChange={(event) => setSortBy(event.target.value)}
                    className="form-select min-h-[42px] w-full rounded-xl"
                  >
                    <option value="created_at">الوقت</option>
                    <option value="status">الحالة</option>
                    <option value="total">المبلغ</option>
                    <option value="id">رقم الطلب</option>
                  </select>
                </label>

                <button
                  type="button"
                  onClick={() => setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))}
                  className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
                >
                  <ArrowDownUp className="h-4 w-4" />
                  <span>{sortDirection === 'asc' ? 'اتجاه الترتيب: تصاعدي' : 'اتجاه الترتيب: تنازلي'}</span>
                </button>

                <label className="w-full">
                  <span className="form-label">تصفية الحالة</span>
                  <select
                    value={statusFilter}
                    onChange={(event) => syncFilterParam('status', event.target.value)}
                    className="form-select min-h-[42px] w-full rounded-xl"
                  >
                    <option value="all">كل الحالات</option>
                    <option value="CREATED">تم الإنشاء</option>
                    <option value="CONFIRMED">تم التأكيد</option>
                    <option value="SENT_TO_KITCHEN">أُرسل للمطبخ</option>
                    <option value="IN_PREPARATION">قيد التحضير</option>
                    <option value="READY">جاهز</option>
                    <option value="OUT_FOR_DELIVERY">خرج للتوصيل</option>
                    <option value="DELIVERED">تم التسليم</option>
                    <option value="DELIVERY_FAILED">فشل التوصيل</option>
                    <option value="CANCELED">ملغى</option>
                  </select>
                </label>

                <label className="w-full">
                  <span className="form-label">تصفية النوع</span>
                  <select
                    value={typeFilter}
                    onChange={(event) => syncFilterParam('order_type', event.target.value)}
                    className="form-select min-h-[42px] w-full rounded-xl"
                  >
                    <option value="all">كل الأنواع</option>
                    <option value="dine-in">داخل المطعم</option>
                    <option value="takeaway">استلام</option>
                    <option value="delivery">توصيل</option>
                  </select>
                </label>

                <button
                  type="button"
                  className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
                  onClick={() => {
                    resetOrderFilters();
                  }}
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>مسح</span>
                </button>
              </div>
            ) : null}
          </div>
        </div>
      }
    >
      <div dir="rtl" className="space-y-4 text-right md:space-y-5">
      <section className="admin-table-shell orders-table-modern shadow-[0_12px_32px_rgba(66,45,24,0.10)]">
        {transitionMutation.isError ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {transitionMutation.error instanceof Error
              ? transitionMutation.error.message
              : 'تعذر تنفيذ الإجراء على الطلب. تحقق من حالة الطلب ثم أعد المحاولة.'}
          </div>
        ) : null}
        {notifyTeamMutation.isError ? (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
            {notifyTeamMutation.error instanceof Error ? notifyTeamMutation.error.message : 'تعذر تبليغ فريق التوصيل.'}
          </div>
        ) : null}
        {createDispatchMutation.isError ? (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
            {createDispatchMutation.error instanceof Error ? createDispatchMutation.error.message : 'تعذر إرسال العرض إلى جهة التوصيل.'}
          </div>
        ) : null}
        {cancelDispatchMutation.isError ? (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
            {cancelDispatchMutation.error instanceof Error ? cancelDispatchMutation.error.message : 'تعذر إلغاء عرض التوصيل.'}
          </div>
        ) : null}
        {emergencyDeliveryFailMutation.isError ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {emergencyDeliveryFailMutation.error instanceof Error
              ? emergencyDeliveryFailMutation.error.message
              : 'تعذر تنفيذ الإغلاق الطارئ لطلب التوصيل.'}
          </div>
        ) : null}
        {collectPaymentMutation.isError ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {collectPaymentMutation.error instanceof Error ? collectPaymentMutation.error.message : 'تعذر تسجيل التحصيل.'}
          </div>
        ) : null}
        {settleDeliveryMutation.isError ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {settleDeliveryMutation.error instanceof Error ? settleDeliveryMutation.error.message : 'تعذر إغلاق تسوية التوصيل.'}
          </div>
        ) : null}
        {settleTableSessionMutation.isError ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {settleTableSessionMutation.error instanceof Error ? settleTableSessionMutation.error.message : 'تعذر تنفيذ تسوية جلسة الطاولة.'}
          </div>
        ) : null}

        <div className="space-y-3 p-3 md:hidden">
          {rows.map((order) => {
            const highlight = resolveOrderHighlight(order.status);
            const dayKey = orderDateKey(order.created_at);
            const contactSummary = resolveOrderContactSummary(order);
            const locationSummary = resolveOrderLocationSummary(order);
            return (
              <article
                key={order.id}
                className={`console-surface-transition rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-3 shadow-[0_8px_22px_rgba(66,45,24,0.08)] ${
                  highlight ? highlight.cardClass : ''
                }`}
              >
                <div className="space-y-3 text-right">
                  <div className="ops-surface-card rounded-2xl border p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex flex-col items-start gap-2">
                        <StatusBadge status={order.status} orderType={order.type} paymentStatus={order.payment_status ?? null} />
                        <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${orderTypeClasses(order.type)}`}>
                          {orderTypeLabel(order.type)}
                        </span>
                      </div>
                      <div className="min-w-0 space-y-1 text-right">
                        <p className="ops-title-strong text-base font-black">{formatOrderTrackingId(order.id)}</p>
                        <p className="ops-text-muted text-[11px] font-medium">
                          {dayKey} - {timeOnlyFormatter.format(new Date(parseApiDateMs(order.created_at)))}
                        </p>
                        <p className="pt-1 text-lg font-black text-brand-700">{order.total.toFixed(2)} د.ج</p>
                      </div>
                    </div>
                  </div>

                  <div className="ops-surface-card rounded-2xl border p-3">
                    <OrderDetailsPreview order={order} onOpen={setDetailsOrder} />
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="ops-surface-card rounded-xl border px-3 py-2.5 text-right">
                      <p className="ops-text-muted text-[10px] font-black">العميل/الجلسة</p>
                      <p className="ops-title mt-1 text-[12px] font-black" dir={order.phone ? 'ltr' : undefined}>
                        {contactSummary.primary}
                      </p>
                    </div>
                    <div className="ops-surface-card rounded-xl border px-3 py-2.5 text-right">
                      <p className="ops-text-muted text-[10px] font-black">الموقع</p>
                      <p className="ops-title mt-1 text-[12px] font-black">{locationSummary.primary}</p>
                    </div>
                  </div>

                  <div className="ops-surface-card rounded-xl border p-3 text-right">
                    <p className="ops-title mb-1 text-[11px] font-black">المتابعة</p>
                    {renderOrderFollowupContent(order, autoNotifyTeam)}
                  </div>
                </div>

                <div className="mt-3 w-full">{renderOrderActions(order)}</div>
              </article>
            );
          })}
          {rows.length === 0 && <div className="ops-surface-card rounded-xl border px-4 py-10 text-center text-[var(--text-muted)]">لا توجد نتائج.</div>}
        </div>

        <div className="adaptive-table orders-table-scroll hidden overflow-x-auto md:block">
          <table className="table-unified orders-table-modern-grid min-w-full border-collapse text-[13px]">
            <thead className="bg-[var(--surface-card-subtle)] text-gray-700">
              <tr>
                <th className="w-[150px] px-3 py-2.5 text-[13px] font-bold">رقم الطلب</th>
                <th className="w-[250px] px-3 py-2.5 text-[13px] font-bold">الطلب</th>
                <th className="w-[132px] px-3 py-2.5 text-[13px] font-bold">النوع</th>
                <th className="w-[150px] px-3 py-2.5 text-[13px] font-bold">الحالة</th>
                <th className="w-[170px] px-3 py-2.5 text-[13px] font-bold">المتابعة</th>
                <th className="w-[110px] px-3 py-2.5 text-[13px] font-bold">المبلغ</th>
                <th className="w-[230px] px-3 py-2.5 text-[13px] font-bold">العميل/الجلسة</th>
                <th className="w-[240px] px-3 py-2.5 text-[13px] font-bold">الموقع</th>
                <th className="w-[300px] px-3 py-2.5 text-[13px] font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((order) => {
                const highlight = resolveOrderHighlight(order.status);
                const rowCellClass = `${rowCellBase} ${highlight ? highlight.cellClass : ''}`;
                const dayKey = orderDateKey(order.created_at);
                const contactSummary = resolveOrderContactSummary(order);
                const locationSummary = resolveOrderLocationSummary(order);
                return (
                  <tr
                    key={order.id}
                    className={`align-top transition-colors hover:bg-[var(--surface-card-hover)] table-row--${orderRowTone(order.status)}`}
                  >
                    <td data-label="رقم الطلب" className={rowCellClass}>
                      <div className="space-y-1">
                        <p className="text-sm font-black text-[var(--text-primary-strong)]">{formatOrderTrackingId(order.id)}</p>
                        <p className="text-xs font-medium text-[var(--text-muted)]">{dayKey}</p>
                        <p className="text-xs font-medium text-[var(--text-muted)]">{timeOnlyFormatter.format(new Date(parseApiDateMs(order.created_at)))}</p>
                      </div>
                    </td>
                    <td data-label="الطلب" className={rowCellClass}>
                      <OrderDetailsPreview order={order} onOpen={setDetailsOrder} compact />
                    </td>
                    <td data-label="النوع" className={`${rowCellClass} min-w-[126px]`}>
                      <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${orderTypeClasses(order.type)}`}>
                        {orderTypeLabel(order.type)}
                      </span>
                    </td>
                    <td data-label="الحالة" className={rowCellClass}>
                      <div className="flex min-w-[120px] items-center">
                        <StatusBadge status={order.status} orderType={order.type} paymentStatus={order.payment_status ?? null} />
                      </div>
                    </td>
                    <td data-label="المتابعة" className={rowCellClass}>
                      {renderOrderFollowupContent(order, autoNotifyTeam)}
                    </td>
                    <td data-label="المبلغ" className={`${rowCellClass} whitespace-nowrap font-bold text-brand-700`}>
                      {order.total.toFixed(2)} د.ج
                    </td>
                    <td data-label="العميل/الجلسة" className={`${rowCellClass} text-xs font-semibold text-[var(--text-secondary)]`}>
                      <div className="space-y-1">
                        <p className="text-sm font-black text-[var(--text-primary)] md:text-[15px]" dir={order.phone ? 'ltr' : undefined}>
                          {contactSummary.primary}
                        </p>
                        <p className="leading-6 text-[var(--text-muted)]">{contactSummary.secondary}</p>
                      </div>
                    </td>
                    <td data-label="الموقع" className={`${rowCellClass} text-xs font-semibold text-[var(--text-secondary)]`}>
                      <div className="space-y-1">
                        <p className="font-black text-[var(--text-primary)]">{locationSummary.primary}</p>
                        <p className="leading-6 text-[var(--text-muted)]">{locationSummary.secondary}</p>
                      </div>
                    </td>
                    <td data-label="الإجراءات" className={`${rowCellClass} min-w-[300px]`}>
                      {renderOrderActions(order)}
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    لا توجد نتائج.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="px-3 pb-3 pt-4 md:px-4 md:pb-4 md:pt-5">
          <TablePagination page={page} totalPages={totalPages} totalRows={totalRows} onPageChange={setPage} />
        </div>
      </section>

      <Modal
        open={isManualModalOpen}
        onClose={closeManualModal}
        title={
          <span className="inline-flex items-center gap-2">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-brand-300 bg-brand-50 text-brand-700">
              <Plus className="h-5 w-5" />
            </span>
            <span>الطلب</span>
          </span>
        }
        description={undefined}
      >
        <form className="space-y-4" onSubmit={submitManualOrder}>
          <div className="grid gap-2 sm:grid-cols-4">
              {([
              { id: 'type', label: '1. نوع الطلب', ready: true },
              { id: 'details', label: '2. البيانات', ready: Boolean(manualType) },
              { id: 'primary', label: '3. المنتجات الأساسية', ready: manualDetailsReady },
              { id: 'secondary', label: '4. المنتجات الثانوية', ready: manualDetailsReady && manualItemsReady && manualHasSecondaryStage },
              { id: 'review', label: '5. المراجعة', ready: manualDetailsReady && manualItemsReady },
            ] as Array<{ id: ManualOrderStep; label: string; ready: boolean }>).map((stepCard) => {
              const isActive = manualStep === stepCard.id;
              const isDone =
                (stepCard.id === 'type' && Boolean(manualType) && manualStep !== 'type') ||
                (stepCard.id === 'details' && manualDetailsReady && ['primary', 'secondary', 'review'].includes(manualStep)) ||
                (stepCard.id === 'primary' && manualItemsReady && ['secondary', 'review'].includes(manualStep)) ||
                (stepCard.id === 'secondary' &&
                  manualHasSecondaryStage &&
                  manualStep === 'review');

              return (
                <button
                  key={stepCard.id}
                  type="button"
                  disabled={!stepCard.ready}
                  onClick={() => setManualStep(stepCard.id)}
                  className={`rounded-2xl border px-3 py-3 text-right transition ${
                    isActive
                      ? 'border-brand-500 bg-brand-50 text-brand-800'
                      : isDone
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                        : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]'
                  } ${!stepCard.ready ? 'cursor-not-allowed opacity-55' : ''}`}
                >
                  <p className="text-sm font-black">{stepCard.label}</p>
                </button>
              );
            })}
          </div>

          {manualStep === 'type' || !manualType ? (
            <div className="space-y-2">
              <span className="form-label">اختر نوع الطلب</span>
              <div className="grid gap-3 sm:grid-cols-3">
                {([
                  { id: 'takeaway', label: 'استلام', hint: 'جاهز للاستلام', enabled: true, icon: PackageCheck },
                  { id: 'delivery', label: 'توصيل', hint: 'تسليم للعنوان', enabled: deliveryEnabled, icon: Truck },
                  { id: 'dine-in', label: 'طاولة', hint: 'طلب داخل المطعم', enabled: true, icon: ClipboardList },
                ] as const)
                  .filter((card) => card.id !== 'delivery' || deliveryChannelEnabled)
                  .map((card) => {
                  const isSelected = manualType === card.id;
                  const Icon = card.icon;
                  return (
                    <button
                      key={card.id}
                      type="button"
                      onClick={() => {
                        if (!card.enabled) {
                          return;
                        }
                        setManualType(card.id);
                        setManualStep('details');
                        if (card.id !== 'dine-in') {
                          setManualTableId('');
                        }
                        setManualDeliveryRootId(undefined);
                        setManualDeliveryLevel2Id(undefined);
                        setManualDeliveryLocalityId(undefined);
                        setManualDeliverySublocalityId(undefined);
                      }}
                      disabled={!card.enabled}
                      className={`flex min-h-[132px] flex-col items-center justify-center gap-2 rounded-2xl border px-4 py-4 text-center transition ${
                        isSelected
                          ? 'border-brand-500 bg-brand-50 text-brand-800 shadow-[0_8px_18px_rgba(121,83,47,0.18)]'
                          : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-primary)] hover:border-brand-300 hover:text-brand-700'
                      } ${!card.enabled ? 'cursor-not-allowed opacity-60 hover:border-[var(--console-border)] hover:text-[var(--text-primary)]' : ''}`}
                    >
                      <Icon className="h-10 w-10" />
                      <span className="text-base font-black">{card.label}</span>
                      <span className="text-xs font-semibold text-[var(--text-muted)]">{card.hint}</span>
                    </button>
                  );
                })}
              </div>
              {deliveryRuntimeBlocked ? <p className="text-xs font-semibold text-amber-700">{deliveryBlockedReason}</p> : null}
            </div>
          ) : (
            <div className="ops-surface-card flex items-center justify-between gap-3 rounded-2xl border px-4 py-3">
              <div>
                <p className="ops-text-muted text-xs font-bold">نوع الطلب المختار</p>
                <p className="ops-title mt-1 text-sm font-black">{orderTypeLabel(manualType)}</p>
              </div>
              <button type="button" className="btn-secondary ui-size-sm" onClick={() => setManualStep('type')}>
                <ClipboardList className="h-4 w-4" />
                <span>تغيير النوع</span>
              </button>
            </div>
          )}

          {manualType && manualStep === 'details' ? (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                {manualType === 'dine-in' ? (
                  <label className="space-y-1">
                    <span className="form-label">رقم الطاولة</span>
                    <select
                      value={manualTableId}
                      onChange={(event) => setManualTableId(event.target.value ? Number(event.target.value) : '')}
                      className="form-select"
                      required
                    >
                      <option value="">اختر الطاولة</option>
                      {tableOptions.map((table) => (
                        <option key={table.id} value={table.id}>
                          طاولة {table.id} ({tableStatusLabel(table.status)})
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <label className="space-y-1">
                    <span className="form-label">رقم الهاتف</span>
                    <input
                      value={manualPhone}
                      onChange={(event) => setManualPhone(event.target.value)}
                      className="form-input"
                      placeholder={manualType === 'takeaway' ? 'اختياري لطلبات الاستلام (مثال: 0550123456)' : 'مطلوب لطلبات التوصيل (مثال: 0550123456)'}
                      required={manualType === 'delivery'}
                    />
                  </label>
                )}

                {manualType === 'delivery' ? (
                  <div className="md:col-span-2">
                    <ManagerDeliveryAddressSelector
                      rootNodes={manualDeliveryRootNodes}
                      level2Nodes={manualDeliveryLevel2Nodes}
                      localityNodes={manualDeliveryLocalityNodes}
                      sublocalityNodes={manualDeliverySublocalityNodes}
                      selectedRootId={manualDeliveryRootId}
                      selectedLevel2Id={manualDeliveryLevel2Id}
                      selectedLocalityId={manualDeliveryLocalityId}
                      selectedSublocalityId={manualDeliverySublocalityId}
                      addressSummary={manualDeliveryAddressSummary}
                      quote={manualDeliveryQuoteQuery.data}
                      quoteLoading={manualDeliveryQuoteQuery.isLoading}
                      selectionIncomplete={Boolean(manualDeliverySelectionIncomplete)}
                      structuredReady={Boolean(
                        deliverySettingsQuery.data?.structured_locations_enabled && manualDeliveryRootNodes.length > 0
                      )}
                      onRootChange={(value) => {
                        setManualDeliveryRootId(value);
                        setManualDeliveryLevel2Id(undefined);
                        setManualDeliveryLocalityId(undefined);
                        setManualDeliverySublocalityId(undefined);
                      }}
                      onLevel2Change={(value) => {
                        setManualDeliveryLevel2Id(value);
                        setManualDeliveryLocalityId(undefined);
                        setManualDeliverySublocalityId(undefined);
                      }}
                      onLocalityChange={(value) => {
                        setManualDeliveryLocalityId(value);
                        setManualDeliverySublocalityId(undefined);
                      }}
                      onSublocalityChange={setManualDeliverySublocalityId}
                    />
                  </div>
                ) : null}

                <label className="space-y-1 md:col-span-2">
                  <span className="form-label">ملاحظات الطلب (اختياري)</span>
                  <textarea
                    value={manualNotes}
                    onChange={(event) => setManualNotes(event.target.value)}
                    className="form-textarea min-h-[80px]"
                    placeholder="أي تعليمات تشغيلية إضافية تخص هذا الطلب"
                  />
                </label>
              </div>
              <div className="grid gap-2 sm:grid-cols-1">
                <button
                  type="button"
                  className="btn-primary inline-flex min-h-[46px] w-full items-center justify-center gap-2"
                  onClick={() => {
                    const error = validateManualDetails();
                    if (error) {
                      setManualError(error);
                      return;
                    }
                    setManualError('');
                    setManualStep('primary');
                  }}
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>متابعة إلى المنتجات الأساسية</span>
                </button>
              </div>
            </>
          ) : null}

          {manualType && manualStep === 'primary' ? (
            <>
              <div className="ops-surface-soft rounded-2xl border p-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="ops-title text-sm font-black">المنتجات الأساسية في الطلب</p>
                    <p className="ops-text-muted text-[11px] font-semibold">أضف المنتجات الأساسية.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setManualItems((prev) => [...prev, { product_id: 0, quantity: 1 }])}
                    className="btn-secondary ui-size-sm inline-flex items-center"
                    aria-label="إضافة عنصر"
                    title="إضافة عنصر"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>

                <div className="ops-text-muted mb-1 hidden gap-2 text-xs font-bold md:grid md:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_88px]">
                  <span className="text-right">المنتج</span>
                  <span className="text-right">الكمية</span>
                  <span className="text-right">الإجراءات</span>
                </div>

                <div className="space-y-2">
                  {manualItems.map((item, index) => {
                    return (
                      <div
                        key={`${index}-${item.product_id}-${item.quantity}`}
                        className="ops-surface-card space-y-2 rounded-2xl border p-3"
                      >
                        <div className="grid gap-2 md:items-end md:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_88px]">
                          <label className="space-y-1">
                            <span className="form-label md:hidden">المنتج الأساسي</span>
                            <select
                              aria-label="اختيار المنتج الأساسي"
                              value={item.product_id}
                              onChange={(event) => {
                                const nextProductId = Number(event.target.value);
                                setManualItems((prev) =>
                                  prev.map((current, i) =>
                                    i === index
                                      ? {
                                          ...current,
                                          product_id: nextProductId,
                                        }
                                      : current
                                  )
                                );
                              }}
                              className="form-select"
                            >
                              <option value={0}>اختر المنتج الأساسي من القائمة</option>
                              {availableManualPrimaryProducts.map((product) => (
                                <option key={product.id} value={product.id}>
                                  {product.name} - {product.price.toFixed(2)} د.ج
                                </option>
                              ))}
                            </select>
                          </label>

                          <label className="space-y-1">
                            <span className="form-label md:hidden">الكمية</span>
                            <input
                              type="number"
                              aria-label="كمية العنصر"
                              min={1}
                              step={1}
                              value={item.quantity}
                              onChange={(event) => {
                                const nextQuantity = Number(event.target.value);
                                setManualItems((prev) =>
                                  prev.map((current, i) =>
                                    i === index ? { ...current, quantity: Number.isFinite(nextQuantity) ? nextQuantity : 1 } : current
                                  )
                                );
                              }}
                              className="form-input"
                              placeholder="مثال: 2"
                            />
                          </label>

                          <div className="space-y-1 text-right">
                            <span className="form-label md:hidden">الإجراءات</span>
                            <button
                              type="button"
                              onClick={() =>
                                setManualItems((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev))
                              }
                              className="btn-danger ui-size-sm w-full inline-flex items-center justify-center"
                              aria-label="حذف"
                              title="حذف"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>

                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <button
                  type="button"
                  className="btn-secondary inline-flex min-h-[46px] w-full items-center justify-center gap-2"
                  onClick={() => setManualStep('details')}
                >
                  <ArrowRight className="h-4 w-4" />
                  <span>العودة إلى البيانات</span>
                </button>
                <button
                  type="button"
                  className="btn-primary inline-flex min-h-[46px] w-full items-center justify-center gap-2"
                  onClick={() => {
                    const error = validateManualItems();
                    if (error) {
                      setManualError(error);
                      return;
                    }
                    setManualError('');
                    setManualStep(manualHasSecondaryStage ? 'secondary' : 'review');
                  }}
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>{manualHasSecondaryStage ? 'متابعة إلى المرحلة الثانية' : 'متابعة إلى المراجعة'}</span>
                </button>
              </div>
            </>
          ) : null}

          {manualType && manualStep === 'secondary' ? (
            <>
              <div className="ops-surface-soft rounded-2xl border p-3">
                <div className="mb-3 space-y-1">
                  <p className="ops-title text-sm font-black">المنتجات الثانوية في الطلب</p>
                  <p className="ops-text-muted text-[11px] font-semibold">اختر المنتجات الثانوية المناسبة للطلب.</p>
                </div>

                {availableManualSecondaryProducts.length > 0 ? (
                  <div className="space-y-3">
                    {availableManualSecondaryProducts.map((product) => {
                      const selectedSecondary =
                        manualSecondaryItems.find((secondaryItem) => secondaryItem.product_id === product.id) ?? null;
                      const currentQuantity = selectedSecondary?.quantity ?? 0;

                      return (
                        <div
                          key={`secondary-option-${product.id}`}
                          className="ops-surface-card grid gap-3 rounded-2xl border p-3 md:grid-cols-[minmax(0,1fr)_auto]"
                        >
                          <div className="space-y-1">
                            <p className="ops-title text-sm font-black">{product.name}</p>
                            <p className="ops-text-muted text-xs font-semibold">{product.price.toFixed(2)} د.ج</p>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() =>
                                setManualSecondaryItems((prev) =>
                                  prev
                                    .map((item) =>
                                      item.product_id === product.id ? { ...item, quantity: item.quantity - 1 } : item,
                                    )
                                    .filter((item) => item.quantity > 0),
                                )
                              }
                              className="btn-secondary ui-size-sm inline-flex h-10 w-10 items-center justify-center rounded-xl p-0"
                              aria-label={`تقليل كمية ${product.name}`}
                            >
                              <Minus className="h-4 w-4" />
                            </button>

                            <span className="inline-flex min-w-10 items-center justify-center text-sm font-black text-[var(--text-primary)]">
                              {currentQuantity}
                            </span>

                            <button
                              type="button"
                              onClick={() =>
                                setManualSecondaryItems((prev) => {
                                  const existing = prev.find((item) => item.product_id === product.id) ?? null;
                                  const nextQuantity = (existing?.quantity ?? 0) + 1;
                                  const next = prev.filter((item) => item.product_id !== product.id);
                                  next.push({ product_id: product.id, quantity: nextQuantity });
                                  return next;
                                })
                              }
                              className="btn-primary ui-size-sm inline-flex h-10 w-10 items-center justify-center rounded-xl p-0"
                              aria-label={`زيادة كمية ${product.name}`}
                            >
                              <Plus className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="ops-surface-card rounded-2xl border px-4 py-5 text-sm font-semibold text-[var(--text-muted)]">
                    لا توجد منتجات ثانوية عامة مفعلة حاليًا.
                  </div>
                )}
              </div>

              <div className="grid gap-2 md:grid-cols-2">
                <button
                  type="button"
                  className="btn-secondary inline-flex min-h-[46px] w-full items-center justify-center gap-2"
                  onClick={() => setManualStep('primary')}
                >
                  <ArrowRight className="h-4 w-4" />
                  <span>العودة إلى المنتجات الأساسية</span>
                </button>
                <button
                  type="button"
                  className="btn-primary inline-flex min-h-[46px] w-full items-center justify-center gap-2"
                  onClick={() => {
                    setManualError('');
                    setManualStep('review');
                  }}
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>متابعة إلى المراجعة</span>
                </button>
              </div>
            </>
          ) : null}

          {manualType && manualStep === 'review' ? (
            <div className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="ops-surface-card rounded-2xl border p-4">
                  <p className="ops-text-muted text-xs font-bold">نوع الطلب</p>
                  <p className="ops-title mt-1 text-sm font-black">{orderTypeLabel(manualType)}</p>
                </div>
                <div className="ops-surface-card rounded-2xl border p-4">
                  <p className="ops-text-muted text-xs font-bold">التواصل / الموقع</p>
                  <p className="ops-title mt-1 text-sm font-black">
                    {manualType === 'dine-in'
                      ? `طاولة ${manualTableId || '-'}`
                      : manualType === 'delivery'
                        ? manualDeliveryAddressSummary || '-'
                        : manualPhone.trim() || 'بدون رقم هاتف'}
                  </p>
                  <p className="ops-text-muted mt-1 text-xs font-semibold">
                    {manualType === 'delivery'
                      ? manualPhone.trim() || 'بدون رقم هاتف'
                      : manualType === 'takeaway'
                        ? manualPhone.trim() || 'الاستلام بدون هاتف'
                        : 'طلب داخل المطعم'}
                  </p>
                </div>
              </div>

              <div className="ops-surface-card rounded-2xl border p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="ops-title text-sm font-black">الأصناف المختارة</p>
                    <span className="ops-text-muted text-xs font-semibold">{validManualPrimaryItemsCount} أصناف أساسية</span>
                </div>
                <div className="space-y-2">
                  {manualItems
                    .filter((item) => {
                      const selectedProduct = availableManualProductsMap.get(item.product_id);
                      return Boolean(selectedProduct && selectedProduct.kind === 'primary' && item.quantity > 0);
                    })
                    .map((item, index) => {
                      const product = availableManualProductsMap.get(item.product_id);
                      if (!product) return null;
                      return (
                        <div key={`review-${index}-${item.product_id}`} className="ops-surface-card rounded-xl border px-3 py-2">
                          <div className="flex items-center justify-between gap-2">
                            <p className="ops-title text-sm font-black">{product.name}</p>
                            <span className="text-xs font-bold text-[#8f5126]">×{item.quantity}</span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              {manualSecondaryItems.length > 0 ? (
                <div className="ops-surface-card rounded-2xl border p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="ops-title text-sm font-black">المنتجات الثانوية المختارة</p>
                    <span className="ops-text-muted text-xs font-semibold">
                      {manualSecondaryItems.reduce((sum, item) => sum + item.quantity, 0)} عناصر ثانوية
                    </span>
                  </div>
                  <div className="space-y-2">
                    {manualSecondaryItems.map((item) => {
                      const product = availableManualProductsMap.get(item.product_id);
                      if (!product) return null;
                      return (
                        <div key={`review-secondary-${item.product_id}`} className="ops-surface-card rounded-xl border px-3 py-2">
                          <div className="flex items-center justify-between gap-2">
                            <p className="ops-title text-sm font-black">{product.name}</p>
                            <span className="text-xs font-bold text-[#8f5126]">×{item.quantity}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              <div className="rounded-xl bg-brand-50 px-3 py-2 text-sm font-black text-brand-700">
                إجمالي الطلب: {manualTotal.toFixed(2)} د.ج
              </div>
            </div>
          ) : null}

          {!manualType ? (
            <div className="ops-surface-card rounded-2xl border px-4 py-5 text-sm font-semibold text-[var(--text-muted)]">
              حدد نوع الطلب.
            </div>
          ) : null}

          {manualError ? (
            <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{manualError}</p>
          ) : null}

          {manualStep === 'review' ? (
            <div className="grid gap-2 md:grid-cols-2">
              <button
                type="button"
                className="btn-secondary inline-flex min-h-[46px] w-full items-center justify-center gap-2"
                onClick={() => setManualStep(manualHasSecondaryStage ? 'secondary' : 'primary')}
              >
                <ArrowRight className="h-4 w-4" />
                <span>{manualHasSecondaryStage ? 'العودة إلى المنتجات الثانوية' : 'العودة إلى المنتجات الأساسية'}</span>
              </button>
              <button
                type="submit"
                disabled={manualCreateMutation.isPending || !manualReviewState.payload}
                className="btn-primary inline-flex min-h-[46px] w-full items-center justify-center gap-2"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{manualCreateMutation.isPending ? 'جارٍ إنشاء الطلب...' : 'تأكيد إنشاء الطلب'}</span>
              </button>
            </div>
          ) : null}
        </form>
      </Modal>

      <Modal
        open={!!detailsOrder}
        onClose={() => setDetailsOrder(null)}
        title={
          <span className="inline-flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-sky-300 bg-sky-50 text-sky-700">
              <Eye className="h-5 w-5" />
            </span>
            <span className="min-w-0">
              <span className="block text-[11px] font-bold text-[var(--text-muted)]">عرض الطلب</span>
              <span className="block truncate">{detailsOrder ? formatOrderTrackingId(detailsOrder.id) : 'الطلب'}</span>
            </span>
          </span>
        }
        headerActions={
          detailsOrder && resolveOperationalWorkflowProfile(activationStageId, detailsOrder.type) === 'base_direct' ? (
            <button
              type="button"
              onClick={() => openOrderTicketPrintView(detailsOrder)}
              className={tablePrintIconButtonClass}
              aria-label="طباعة"
              title="طباعة"
            >
              <Printer className="h-4 w-4" />
            </button>
          ) : undefined
        }
        description={undefined}
      >
        {detailsOrder ? (
          <div className="space-y-3.5">
            <div className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-[minmax(0,1.5fr)_repeat(4,minmax(0,0.72fr))]">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/95 p-3.5">
                <p className="text-[11px] font-bold text-[var(--text-muted)]">كود التتبع</p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-base font-black tracking-[0.04em] text-[var(--text-primary)] md:text-lg" dir="ltr">
                    {detailsOrder.tracking_code}
                  </p>
                  <span className="inline-flex min-h-[32px] items-center justify-center rounded-full border border-[#d6b184] bg-[#fff4e5] px-3 py-1 text-[11px] font-black text-[#9a5b24]">
                    مرجع العميل
                  </span>
                </div>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/95 p-3.5">
                <p className="text-[11px] font-bold text-[var(--text-muted)]">الحالة</p>
                <div className="mt-2">
                  <StatusBadge
                    status={detailsOrder.status}
                    orderType={detailsOrder.type}
                    paymentStatus={detailsOrder.payment_status ?? null}
                  />
                </div>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/95 p-3.5">
                <p className="text-[11px] font-bold text-[var(--text-muted)]">إجمالي الطلب</p>
                <p className="mt-2 text-base font-black text-[#f2b277] md:text-lg">{detailsOrder.total.toFixed(2)} د.ج</p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/95 p-3.5">
                <p className="text-[11px] font-bold text-[var(--text-muted)]">نوع الطلب</p>
                <div className="mt-2">
                  <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold ${orderTypeClasses(detailsOrder.type)}`}>
                    {orderTypeLabel(detailsOrder.type)}
                  </span>
                </div>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/95 p-3.5">
                <p className="text-[11px] font-bold text-[var(--text-muted)]">وقت الإنشاء</p>
                <p className="mt-2 text-[13px] font-bold leading-6 text-[var(--text-primary)]">
                  {orderDateKey(detailsOrder.created_at)} - {timeOnlyFormatter.format(new Date(parseApiDateMs(detailsOrder.created_at)))}
                </p>
              </div>
            </div>

            {sanitizeMojibakeText(detailsOrder.notes, '').trim() ? (
              <div className="rounded-2xl border border-amber-300/60 bg-amber-50/95 p-3.5 shadow-[0_10px_24px_rgba(146,93,23,0.08)]">
                <p className="text-[11px] font-black text-amber-800">ملاحظة الطلب</p>
                <p className="mt-1.5 text-[14px] font-semibold leading-7 text-[#5c3a17]">
                  {sanitizeMojibakeText(detailsOrder.notes, '').trim()}
                </p>
              </div>
            ) : null}

            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(290px,0.85fr)]">
              <section className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/95 p-3.5">
                <div className="mb-2.5 flex items-center justify-between gap-2">
                  <h4 className="text-sm font-black text-[var(--text-primary)]">عناصر الطلب</h4>
                  <span className="inline-flex min-h-[32px] items-center justify-center rounded-full border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-1 text-[11px] font-black text-[var(--text-secondary)]">
                    {detailsOrder.items.length} أصناف
                  </span>
                </div>
                <div className="space-y-2 md:max-h-[320px] md:overflow-y-auto md:pr-1">
                  {detailsOrder.items.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between gap-3 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-black text-[var(--text-primary)]">{sanitizeMojibakeText(item.product_name)}</p>
                        <p className="text-[11px] font-semibold text-[var(--text-secondary)]">
                          سعر الوحدة: {item.price.toFixed(2)} د.ج
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="inline-flex min-h-[30px] min-w-[46px] items-center justify-center rounded-full border border-[#e0bf8f] bg-[#fff4e5] px-2.5 py-0.5 text-[11px] font-black text-[#9a5b24]">
                          ×{item.quantity}
                        </span>
                        <span className="text-[13px] font-black text-brand-700">
                          {(item.price * item.quantity).toFixed(2)} د.ج
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="space-y-3">
                <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/95 p-3.5">
                  <h4 className="text-sm font-black text-[var(--text-primary)]">ملخص التشغيل</h4>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
                    <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2">
                      <p className="text-[10px] font-bold text-[var(--text-muted)]">التواصل</p>
                      <p className="mt-1 text-[13px] font-black text-[var(--text-primary)]" dir={detailsOrder.phone ? 'ltr' : undefined}>
                        {detailsOrder.table_id ? `طاولة ${detailsOrder.table_id}` : detailsOrder.phone ?? '-'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2">
                      <p className="text-[10px] font-bold text-[var(--text-muted)]">الموقع</p>
                      <p className="mt-1 text-[13px] font-black text-[var(--text-primary)]">
                        {detailsOrder.type === 'delivery' ? resolveOrderAddressSummary(detailsOrder) : 'لا يوجد عنوان'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2">
                      <p className="text-[10px] font-bold text-[var(--text-muted)]">مصدر الرسم</p>
                      <p className="mt-1 text-[13px] font-black text-[var(--text-primary)]">
                        {resolveOrderDeliveryPricingSourceLabel(detailsOrder)}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2">
                      <p className="text-[10px] font-bold text-[var(--text-muted)]">قبل الرسوم</p>
                      <p className="mt-1 text-[13px] font-black text-[var(--text-primary)]">{detailsOrder.subtotal.toFixed(2)} د.ج</p>
                    </div>
                    <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2">
                      <p className="text-[10px] font-bold text-[var(--text-muted)]">رسوم التوصيل</p>
                      <p className="mt-1 text-[13px] font-black text-[var(--text-primary)]">{detailsOrder.delivery_fee.toFixed(2)} د.ج</p>
                    </div>
                  </div>
                </div>

              </section>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        open={!!reasonDialog}
        onClose={resetReasonDialog}
        title={
          <span className="inline-flex items-center gap-2">
            <span
              className={`inline-flex h-10 w-10 items-center justify-center rounded-xl border ${
                reasonDialog?.mode === 'cancel'
                  ? 'border-rose-300 bg-rose-50 text-rose-700'
                  : 'border-amber-300 bg-amber-50 text-amber-700'
              }`}
            >
              {reasonDialog?.mode === 'cancel' ? <XCircle className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
            </span>
            <span>{reasonDialog?.mode === 'cancel' ? 'إلغاء الطلب' : 'فشل التوصيل'}</span>
          </span>
        }
        description={undefined}
        footer={(
          <div className="flex flex-wrap items-center gap-2">
            {reasonStep === 'review' ? (
              <button
                type="button"
                className="btn-secondary inline-flex items-center gap-2"
                onClick={() => setReasonStep('reason')}
                disabled={transitionMutation.isPending || emergencyDeliveryFailMutation.isPending}
              >
                <ArrowRight className="h-4 w-4" />
                <span>رجوع</span>
              </button>
            ) : null}
            {reasonStep === 'reason' ? (
              <button
                type="button"
                className="btn-primary inline-flex items-center gap-2"
                disabled={!reasonCode}
                onClick={() => setReasonStep('review')}
              >
                <ClipboardCheck className="h-4 w-4" />
                <span>مراجعة التنفيذ</span>
              </button>
            ) : null}
            {reasonStep === 'review' ? (
              <button
                type="button"
                className="btn-primary inline-flex items-center gap-2"
                disabled={transitionMutation.isPending || emergencyDeliveryFailMutation.isPending || !reasonCode}
                onClick={submitReasonAction}
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{transitionMutation.isPending || emergencyDeliveryFailMutation.isPending ? 'جارٍ التنفيذ...' : 'تأكيد التنفيذ'}</span>
              </button>
            ) : null}
          </div>
        )}
      >
        <div className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-2">
            {(
              [
                { id: 'reason', label: '1. اختيار السبب' },
                { id: 'review', label: '2. مراجعة التنفيذ' },
              ] as Array<{ id: ReasonDialogStep; label: string }>
            ).map((stepCard) => {
              const active = reasonStep === stepCard.id;
              return (
                <button
                  key={stepCard.id}
                  type="button"
                  onClick={() => {
                    if (stepCard.id === 'review' && !reasonCode) {
                      return;
                    }
                    setReasonStep(stepCard.id);
                  }}
                  className={`rounded-2xl border px-3 py-3 text-right transition ${
                    active
                      ? 'border-[var(--accent-strong)] bg-[var(--surface-card-soft)] text-[var(--text-primary-strong)]'
                      : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]'
                  }`}
                >
                  <span className="block text-sm font-black">{stepCard.label}</span>
                </button>
              );
            })}
          </div>

          <div className="rounded-xl border border-brand-100 bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-700">
            الطلب: {reasonDialog ? formatOrderTrackingId(reasonDialog.order.id) : '-'}
          </div>

          {reasonStep === 'reason' ? (
            <>
              <label className="space-y-1">
                <span className="form-label">السبب المعياري</span>
                <select
                  className="form-select"
                  value={reasonCode}
                  onChange={(event) => setReasonCode(event.target.value)}
                >
                  {activeReasonOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="form-label">ملاحظة إضافية (اختياري)</span>
                <textarea
                  className="form-textarea min-h-[84px]"
                  value={reasonNote}
                  onChange={(event) => setReasonNote(event.target.value)}
                  placeholder="معلومة إضافية قصيرة تدعم سبب الإجراء"
                />
              </label>
            </>
          ) : null}

          {reasonStep === 'review' ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                <p className="text-xs font-bold text-[var(--text-muted)]">الإجراء</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                  {reasonDialog?.mode === 'cancel' ? 'إلغاء الطلب' : 'إغلاق طارئ لطلب التوصيل'}
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                <p className="text-xs font-bold text-[var(--text-muted)]">السبب المحدد</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                  {activeReasonOptions.find((option) => option.value === reasonCode)?.label || '—'}
                </p>
                <p className="mt-2 text-xs text-[var(--text-muted)]">{reasonNote.trim() || 'بدون ملاحظة إضافية'}</p>
              </div>
            </div>
          ) : null}
        </div>
      </Modal>
      </div>
    </PageShell>
  );
}

