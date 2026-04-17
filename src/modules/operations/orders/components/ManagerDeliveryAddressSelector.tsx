import type { DeliveryAddressNode, DeliveryLocationPricingQuote } from '@/shared/api/types';

interface ManagerDeliveryAddressSelectorProps {
  rootNodes: DeliveryAddressNode[];
  level2Nodes: DeliveryAddressNode[];
  localityNodes: DeliveryAddressNode[];
  sublocalityNodes: DeliveryAddressNode[];
  selectedRootId?: number;
  selectedLevel2Id?: number;
  selectedLocalityId?: number;
  selectedSublocalityId?: number;
  addressSummary: string;
  quote: DeliveryLocationPricingQuote | null | undefined;
  quoteLoading: boolean;
  selectionIncomplete: boolean;
  structuredReady: boolean;
  onRootChange: (value: number | undefined) => void;
  onLevel2Change: (value: number | undefined) => void;
  onLocalityChange: (value: number | undefined) => void;
  onSublocalityChange: (value: number | undefined) => void;
}

interface AddressSelectFieldProps {
  label: string;
  placeholder: string;
  options: DeliveryAddressNode[];
  value?: number;
  disabled?: boolean;
  onChange: (value: number | undefined) => void;
}

function AddressSelectField({
  label,
  placeholder,
  options,
  value,
  disabled,
  onChange,
}: AddressSelectFieldProps) {
  return (
    <label className="block">
      <span className="form-label">{label}</span>
      <select
        className="form-select"
        value={value ?? ''}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : undefined)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ManagerDeliveryAddressSelector({
  rootNodes,
  level2Nodes,
  localityNodes,
  sublocalityNodes,
  selectedRootId,
  selectedLevel2Id,
  selectedLocalityId,
  selectedSublocalityId,
  addressSummary,
  quote,
  quoteLoading,
  selectionIncomplete,
  structuredReady,
  onRootChange,
  onLevel2Change,
  onLocalityChange,
  onSublocalityChange,
}: ManagerDeliveryAddressSelectorProps) {
  if (!structuredReady) {
    return (
      <div className="rounded-2xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-300">
        لا يمكن إنشاء طلب توصيل من اللوحة قبل ضبط شجرة العناوين والتسعير في صفحة التوصيل.
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
      <div className="space-y-1">
        <p className="text-sm font-black text-[var(--text-primary-strong)]">عنوان التوصيل</p>
        <p className="text-xs text-[var(--text-muted)]">
          اختر العنوان النهائي للعميل، والنظام سيحسب الرسوم تلقائيًا من أقرب عقدة مسعرة.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <AddressSelectField
          label="المستوى الأول"
          placeholder="اختر المستوى الأول"
          options={rootNodes}
          value={selectedRootId}
          onChange={onRootChange}
        />
        <AddressSelectField
          label="المستوى الثاني"
          placeholder="اختر المستوى الثاني"
          options={level2Nodes}
          value={selectedLevel2Id}
          disabled={!selectedRootId}
          onChange={onLevel2Change}
        />
        <AddressSelectField
          label="المدينة"
          placeholder="اختر المدينة"
          options={localityNodes}
          value={selectedLocalityId}
          disabled={!selectedLevel2Id}
          onChange={onLocalityChange}
        />
        <AddressSelectField
          label="الحي"
          placeholder="اختر الحي"
          options={sublocalityNodes}
          value={selectedSublocalityId}
          disabled={!selectedLocalityId}
          onChange={onSublocalityChange}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1.25fr)_minmax(220px,0.75fr)]">
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] px-4 py-3">
          <p className="text-xs font-bold text-[var(--text-muted)]">العنوان الذي سيحفظ على الطلب</p>
          <p className="mt-2 text-sm font-black text-[var(--text-primary-strong)]">
            {addressSummary || 'ابدأ باختيار عنوان التوصيل من القوائم المتاحة.'}
          </p>
          {selectionIncomplete ? (
            <p className="mt-2 text-xs font-semibold text-amber-300">
              ما زال هناك مستوى متاح أسفل هذا الاختيار. أكمل التحديد حتى تصل إلى آخر عقدة مناسبة.
            </p>
          ) : null}
          {!selectionIncomplete && quote?.message ? (
            <p className="mt-2 text-xs font-semibold text-rose-300">{quote.message}</p>
          ) : null}
        </div>

        <div
          className={`rounded-2xl border px-4 py-3 ${
            quote?.available
              ? 'border-emerald-500/30 bg-emerald-500/10'
              : 'border-[var(--console-border)] bg-[var(--surface-card)]'
          }`}
        >
          <p className="text-xs font-bold text-[var(--text-muted)]">رسوم التوصيل المعتمدة</p>
          <p className="mt-2 text-lg font-black text-[var(--text-primary-strong)]">
            {quoteLoading ? 'جارٍ الحساب...' : quote?.delivery_fee != null ? `${quote.delivery_fee.toFixed(2)} د.ج` : '--'}
          </p>
          {quote?.resolved_node_label ? (
            <p className="mt-2 text-xs text-[var(--text-muted)]">تم اعتماد التسعير من: {quote.resolved_node_label}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
