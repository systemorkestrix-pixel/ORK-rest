import type { OrderType } from '@/shared/api/types';
import { tableStatusLabel } from '@/shared/utils/order';

interface PublicOrderHeaderCardProps {
  tableId?: number;
  tableStatus?: 'available' | 'occupied' | 'reserved';
  orderType: OrderType;
  publicOrderTypeOptions: Array<{ value: OrderType; label: string }>;
  availablePublicTablesCount: number;
  onOrderTypeChange: (value: OrderType) => void;
  bootstrapLoading: boolean;
  bootstrapErrorText: string;
  tablesErrorText: string;
  tableSessionErrorText: string;
  deliveryBlockedReason?: string;
}

export function PublicOrderHeaderCard({
  tableId,
  tableStatus,
  orderType,
  publicOrderTypeOptions,
  availablePublicTablesCount,
  onOrderTypeChange,
  bootstrapLoading,
  bootstrapErrorText,
  tablesErrorText,
  tableSessionErrorText,
  deliveryBlockedReason,
}: PublicOrderHeaderCardProps) {
  return (
    <section className="admin-card p-4 md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-xl font-black text-gray-900 md:text-2xl">طلب جديد</h2>
          <p className="text-sm text-gray-600">اختر الأصناف، راجع الملخص، ثم أرسل الطلب مباشرة.</p>
        </div>
        {tableId ? (
          <span className="rounded-full ui-badge-success px-3 py-1 text-xs font-bold md:text-sm">
            الطاولة رقم {tableId}
            {tableStatus ? ` - ${tableStatusLabel(tableStatus)}` : ''}
          </span>
        ) : (
          <label className="w-full max-w-xs">
            <span className="form-label">نوع الطلب</span>
            <select
              className="form-select"
              value={orderType}
              onChange={(event) => onOrderTypeChange(event.target.value as OrderType)}
            >
              {publicOrderTypeOptions.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                  disabled={option.value === 'dine-in' && availablePublicTablesCount === 0}
                >
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {bootstrapLoading ? (
          <p className="rounded-xl border border-sky-300 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-700">
            جارٍ تجهيز الواجهة وبيانات الطلب...
          </p>
        ) : null}
        {bootstrapErrorText ? (
          <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
            {bootstrapErrorText}
          </p>
        ) : null}
        {!tableId && tablesErrorText ? (
          <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
            {tablesErrorText}
          </p>
        ) : null}
        {!tableId && orderType === 'delivery' && deliveryBlockedReason ? (
          <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
            {deliveryBlockedReason}
          </p>
        ) : null}
        {tableSessionErrorText ? (
          <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
            {tableSessionErrorText}
          </p>
        ) : null}
      </div>
    </section>
  );
}
