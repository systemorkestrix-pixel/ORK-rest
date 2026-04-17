import type { FormEvent } from 'react';
import { CheckCircle2, Clock3, ShoppingBag, X } from 'lucide-react';

import type { Order, OrderType, TableSession, TableInfo } from '@/shared/api/types';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { parseApiDateMs } from '@/shared/utils/date';
import { formatOrderTrackingId, tableStatusLabel } from '@/shared/utils/order';
import type { CartRow } from '../publicOrder.helpers';

interface PublicOrderSidebarProps {
  tableId?: number;
  orderType: OrderType;
  cartItems: CartRow[];
  total: number;
  subtotal: number;
  fixedDeliveryFee: number;
  minDeliveryOrderAmount: number;
  phone: string;
  address: string;
  notes: string;
  selectedTable?: number;
  availablePublicTables: TableInfo[];
  lastCreatedOrder: Order | null;
  showCreatedOrderCard: boolean;
  hasActiveTableSession: boolean;
  showTableComposer: boolean;
  tableSession?: TableSession;
  tableSessionLoading: boolean;
  submitPending: boolean;
  submitSuccess: boolean;
  submitDisabled: boolean;
  error: string;
  createdOrderTypeLabel: string | null;
  onHideCreatedOrderCard: () => void;
  onShowTableComposer: () => void;
  onHideTableComposer: () => void;
  onPhoneChange: (value: string) => void;
  onAddressChange: (value: string) => void;
  onNotesChange: (value: string) => void;
  onSelectedTableChange: (value: number | undefined) => void;
  onSubmitOrder: (event: FormEvent<HTMLFormElement>) => void;
}

const timeFormatter = new Intl.DateTimeFormat('ar-DZ-u-nu-latn', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

export function PublicOrderSidebar({
  tableId,
  orderType,
  cartItems,
  total,
  subtotal,
  fixedDeliveryFee,
  minDeliveryOrderAmount,
  phone,
  address,
  notes,
  selectedTable,
  availablePublicTables,
  lastCreatedOrder,
  showCreatedOrderCard,
  hasActiveTableSession,
  showTableComposer,
  tableSession,
  tableSessionLoading,
  submitPending,
  submitSuccess,
  submitDisabled,
  error,
  createdOrderTypeLabel,
  onHideCreatedOrderCard,
  onShowTableComposer,
  onHideTableComposer,
  onPhoneChange,
  onAddressChange,
  onNotesChange,
  onSelectedTableChange,
  onSubmitOrder,
}: PublicOrderSidebarProps) {
  return (
    <aside className="admin-card h-fit p-4 md:p-6 tablet:sticky tablet:top-6">
      <h3 className="text-lg font-black text-gray-900">ملخص الطلب</h3>

      {submitPending ? (
        <div className="mt-3 rounded-xl border border-sky-300 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-700">
          <span className="inline-flex items-center gap-2">
            <Clock3 className="h-4 w-4" />
            جارٍ إرسال الطلب إلى النظام...
          </span>
        </div>
      ) : null}

      {showCreatedOrderCard && lastCreatedOrder ? (
        <article className="mt-3 rounded-2xl border border-emerald-300 bg-emerald-50 p-3">
          <div className="mb-2 flex items-start justify-between gap-2">
            <div className="space-y-1">
              <p className="inline-flex items-center gap-2 text-sm font-black text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                تم إنشاء الطلب بنجاح
              </p>
              <p className="text-xs font-semibold text-emerald-800">{formatOrderTrackingId(lastCreatedOrder.id)}</p>
            </div>
            <button
              type="button"
              onClick={onHideCreatedOrderCard}
              className="btn-secondary ui-size-sm h-8 w-8 p-0"
              aria-label="إخفاء بطاقة التتبع"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="space-y-1 text-xs text-gray-700">
            <p className="flex items-center justify-between gap-2">
              <span>الحالة الحالية</span>
              <StatusBadge
                status={lastCreatedOrder.status}
                orderType={lastCreatedOrder.type}
                paymentStatus={lastCreatedOrder.payment_status ?? null}
              />
            </p>
            <p className="flex items-center justify-between gap-2">
              <span>نوع الطلب</span>
              <span className="font-bold">{createdOrderTypeLabel}</span>
            </p>
            <p className="flex items-center justify-between gap-2">
              <span>وقت الإنشاء</span>
              <span className="font-bold">{timeFormatter.format(new Date(parseApiDateMs(lastCreatedOrder.created_at)))}</span>
            </p>
            <p className="flex items-center justify-between gap-2">
              <span>الإجمالي</span>
              <span className="font-black text-emerald-700">{lastCreatedOrder.total.toFixed(2)} د.ج</span>
            </p>
          </div>
        </article>
      ) : null}

      <div className="mt-4 space-y-3">
        {cartItems.length === 0 ? (
          <p className="rounded-xl border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-600">لم يتم اختيار أي صنف بعد.</p>
        ) : null}
        {cartItems.map((item) => (
          <div key={item.product.id} className="flex items-center justify-between text-sm">
            <span className="break-words">
              {item.product.name} x {item.quantity}
            </span>
            <span className="font-bold">{(item.product.price * item.quantity).toFixed(2)} د.ج</span>
          </div>
        ))}
      </div>

      {tableId && tableSessionLoading ? (
        <p className="mt-4 rounded-xl border border-sky-300 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-700">
          جارٍ تحميل حالة الطاولة...
        </p>
      ) : null}

      {tableId && tableSession && hasActiveTableSession && !showTableComposer ? (
        <div className="mt-5 space-y-3">
          <div className="rounded-2xl border border-brand-100 bg-brand-50 p-3">
            <p className="text-sm font-black text-brand-700">جلسة الطاولة نشطة</p>
            <p className="text-xs text-gray-600">طلبات نشطة: {tableSession.active_orders_count}</p>
            <p className="text-xs text-gray-600">طلبات غير مسددة: {tableSession.unsettled_orders_count}</p>
            <p className="text-sm font-bold text-brand-700">الإجمالي غير المسدد: {tableSession.unpaid_total.toFixed(2)} د.ج</p>
          </div>

          <div className="space-y-2">
            {tableSession.orders.map((order) => (
              <article key={order.id} className="rounded-xl border border-gray-200 bg-white p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-sm font-black text-gray-900">{formatOrderTrackingId(order.id)}</p>
                  <StatusBadge status={order.status} orderType={order.type} paymentStatus={order.payment_status ?? null} />
                </div>
                <div className="text-xs text-gray-600">
                  <p>الوقت: {timeFormatter.format(new Date(parseApiDateMs(order.created_at)))}</p>
                  <p>الإجمالي: {order.total.toFixed(2)} د.ج</p>
                </div>
              </article>
            ))}
          </div>

          <button type="button" onClick={onShowTableComposer} className="btn-secondary w-full">
            طلب جديد لنفس الطاولة
          </button>
        </div>
      ) : (
        <form onSubmit={onSubmitOrder} className="mt-6 space-y-3">
          {tableId && hasActiveTableSession ? (
            <button type="button" onClick={onHideTableComposer} className="btn-secondary w-full">
              الرجوع إلى تتبع الجلسة
            </button>
          ) : null}

          {!tableId && (orderType === 'takeaway' || orderType === 'delivery') ? (
            <label>
              <span className="form-label">رقم الهاتف</span>
              <input
                value={phone}
                onChange={(event) => onPhoneChange(event.target.value)}
                className="form-input"
                placeholder="رقم الهاتف"
                required
                dir="ltr"
              />
            </label>
          ) : null}

          {!tableId && orderType === 'delivery' ? (
            <label>
              <span className="form-label">عنوان التوصيل</span>
              <textarea
                value={address}
                onChange={(event) => onAddressChange(event.target.value)}
                className="form-textarea"
                placeholder="عنوان التوصيل"
                required
              />
            </label>
          ) : null}

          {!tableId && orderType === 'dine-in' ? (
            <label>
              <span className="form-label">رقم الطاولة</span>
              <select
                className="form-select"
                onChange={(event) => onSelectedTableChange(event.target.value ? Number(event.target.value) : undefined)}
                value={selectedTable ?? ''}
                required
              >
                <option value="" disabled>
                  اختر رقم الطاولة
                </option>
                {availablePublicTables.map((table) => (
                  <option key={table.id} value={table.id}>
                    طاولة {table.id} ({tableStatusLabel(table.status)})
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label>
            <span className="form-label">ملاحظات إضافية (اختياري)</span>
            <textarea
              value={notes}
              onChange={(event) => onNotesChange(event.target.value)}
              className="form-textarea"
              placeholder="ملاحظات إضافية"
            />
          </label>

          <div className="space-y-1 rounded-xl bg-brand-50 px-3 py-2 text-sm font-bold text-brand-700">
            <p>قيمة الطلب: {subtotal.toFixed(2)} د.ج</p>
            {!tableId && orderType === 'delivery' ? <p>رسوم التوصيل: {fixedDeliveryFee.toFixed(2)} د.ج</p> : null}
            {!tableId && orderType === 'delivery' && minDeliveryOrderAmount > 0 ? (
              <p>الحد الأدنى للتوصيل: {minDeliveryOrderAmount.toFixed(2)} د.ج</p>
            ) : null}
            <p className="text-base">الإجمالي: {total.toFixed(2)} د.ج</p>
          </div>

          {submitSuccess && !showCreatedOrderCard ? (
            <p className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
              تم إنشاء الطلب بنجاح.
            </p>
          ) : null}

          {error ? (
            <p className="rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{error}</p>
          ) : null}

          <button type="submit" disabled={submitDisabled} className="btn-primary w-full gap-2">
            <ShoppingBag className="h-4 w-4" />
            {submitPending ? 'جارٍ الإرسال...' : 'إرسال الطلب'}
          </button>
        </form>
      )}
    </aside>
  );
}
