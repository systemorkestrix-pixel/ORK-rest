import type {
  DeliveryAddressNode,
  DeliveryAddressPricing,
  DeliveryLocationPricingQuote,
} from '@/shared/api/types';

interface DeliveryAddressPricingManagerProps {
  selectedNode: DeliveryAddressNode | null;
  selectedPathLabel: string;
  pricingItems: DeliveryAddressPricing[];
  quote?: DeliveryLocationPricingQuote | null;
  pricingSearch: string;
  pricingActiveOnly: boolean | null;
  onPricingSearchChange: (value: string) => void;
  onPricingActiveOnlyChange: (value: boolean | null) => void;
}

function levelLabel(level: string) {
  switch (level) {
    case 'admin_area_level_1':
      return 'المنطقة الرئيسية';
    case 'admin_area_level_2':
      return 'الفرع الإداري';
    case 'locality':
      return 'المدينة';
    case 'sublocality':
      return 'الحي';
    default:
      return level;
  }
}

function pricingSourceLabel(source?: string | null) {
  switch (source) {
    case 'manual_tree':
      return 'من شجرة العناوين';
    case 'fixed':
      return 'من الرسم الاحتياطي';
    case 'unavailable':
      return 'غير متاح';
    default:
      return 'غير محدد';
  }
}

export function DeliveryAddressPricingManager({
  selectedNode,
  selectedPathLabel,
  pricingItems,
  quote,
  pricingSearch,
  pricingActiveOnly,
  onPricingSearchChange,
  onPricingActiveOnlyChange,
}: DeliveryAddressPricingManagerProps) {
  return (
    <section className="admin-card space-y-4 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-1">
          <h3 className="text-sm font-black text-[var(--text-primary-strong)]">سجل الأسعار</h3>
          <p className="text-xs text-[var(--text-muted)]">راجع الأسعار الحالية وابحث عن العنوان المطلوب.</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="space-y-1">
            <span className="form-label">بحث</span>
            <input
              className="form-input ui-size-sm"
              value={pricingSearch}
              onChange={(event) => onPricingSearchChange(event.target.value)}
              placeholder="اسم العنوان أو رمزه"
            />
          </label>
          <label className="space-y-1">
            <span className="form-label">الحالة</span>
            <select
              className="form-select ui-size-sm"
              value={pricingActiveOnly === null ? 'all' : pricingActiveOnly ? 'active' : 'inactive'}
              onChange={(event) =>
                onPricingActiveOnlyChange(
                  event.target.value === 'all' ? null : event.target.value === 'active'
                )
              }
            >
              <option value="all">الكل</option>
              <option value="active">النشطة</option>
              <option value="inactive">الموقوفة</option>
            </select>
          </label>
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
            <p className="font-bold text-[var(--text-muted)]">نتيجة التحديد الحالي</p>
            <p className="mt-1 font-black text-[var(--text-primary-strong)]">
              {selectedPathLabel || 'لا يوجد تحديد'}
            </p>
          </div>
        </div>
      </div>

      {selectedNode ? (
        <div className="grid gap-2 sm:grid-cols-3">
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
            <p className="font-bold text-[var(--text-muted)]">السعر الفعلي</p>
            <p className="mt-1 text-base font-black text-[var(--text-primary-strong)]">
              {quote?.available && quote.delivery_fee !== null ? quote.delivery_fee.toFixed(2) : '--'}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
            <p className="font-bold text-[var(--text-muted)]">مصدر السعر</p>
            <p className="mt-1 font-black text-[var(--text-primary-strong)]">{pricingSourceLabel(quote?.pricing_source)}</p>
          </div>
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
            <p className="font-bold text-[var(--text-muted)]">العقدة المرجعية</p>
            <p className="mt-1 font-black text-[var(--text-primary-strong)]">{quote?.resolved_node_label ?? '--'}</p>
          </div>
        </div>
      ) : null}

      <div className="space-y-2">
        {pricingItems.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-[var(--console-border)] px-3 py-6 text-center text-sm text-[var(--text-muted)]">
            لا يوجد سعر مباشر بعد.
          </p>
        ) : (
          pricingItems.map((item) => (
            <div
              key={item.id}
              className={`rounded-2xl border px-3 py-3 ${
                item.node_id === selectedNode?.id
                  ? 'border-[var(--primary-button-bg)] bg-[color:color-mix(in_srgb,var(--primary-button-bg)_14%,transparent)]'
                  : 'border-[var(--console-border)] bg-[var(--surface-card-soft)]'
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-black text-[var(--text-primary-strong)]">{item.display_name}</p>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">
                    {levelLabel(item.level)} · الرمز: {item.code ?? item.location_key}
                  </p>
                </div>
                <div className="text-left">
                  <p className="text-lg font-black text-[var(--text-primary-strong)]">{item.delivery_fee.toFixed(2)}</p>
                  <p className={`text-xs font-bold ${item.active ? 'text-emerald-500' : 'text-amber-500'}`}>
                    {item.active ? 'نشط' : 'موقوف'}
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
