import type { DeliveryAddressNode, DeliveryLocationPricingQuote } from '@/shared/api/types';

interface PublicDeliveryAddressSelectorProps {
  rootNodes: DeliveryAddressNode[];
  adminAreaLevel2Nodes: DeliveryAddressNode[];
  localityNodes: DeliveryAddressNode[];
  sublocalityNodes: DeliveryAddressNode[];
  selectedRootId?: number;
  selectedAdminAreaLevel2Id?: number;
  selectedLocalityId?: number;
  selectedSublocalityId?: number;
  addressSummary: string;
  quote: DeliveryLocationPricingQuote | null | undefined;
  quoteLoading: boolean;
  selectionIncomplete: boolean;
  structuredReady: boolean;
  onRootChange: (value: number | undefined) => void;
  onAdminAreaLevel2Change: (value: number | undefined) => void;
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
      <span className="mb-2 block text-sm font-black text-[#5c4735]">{label}</span>
      <select
        className="w-full rounded-2xl border border-[#e4d5bf] bg-white px-4 py-3 text-sm font-semibold text-[#2f2218] outline-none transition focus:border-[#d59045] disabled:cursor-not-allowed disabled:bg-[#f3ede3] disabled:text-[#9f8b76]"
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

export function PublicDeliveryAddressSelector({
  rootNodes,
  adminAreaLevel2Nodes,
  localityNodes,
  sublocalityNodes,
  selectedRootId,
  selectedAdminAreaLevel2Id,
  selectedLocalityId,
  selectedSublocalityId,
  addressSummary,
  quote,
  quoteLoading,
  selectionIncomplete,
  structuredReady,
  onRootChange,
  onAdminAreaLevel2Change,
  onLocalityChange,
  onSublocalityChange,
}: PublicDeliveryAddressSelectorProps) {
  if (!structuredReady) {
    return (
      <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
        خدمة التوصيل تحتاج إلى ضبط عناوين التغطية أولًا قبل استقبال الطلبات العامة.
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-[28px] border border-[#e7d8c3] bg-[#fffaf3] p-4">
      <div className="space-y-1">
        <p className="text-sm font-black text-[#2f2218]">حدد عنوان التوصيل من القوائم</p>
        <p className="text-xs leading-6 text-[#7a6450]">
          اختر آخر مستوى متاح لك، وسيحسب النظام رسوم التوصيل من أقرب نطاق مسعّر.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <AddressSelectField
          label="المنطقة الرئيسية"
          placeholder="اختر المنطقة الرئيسية"
          options={rootNodes}
          value={selectedRootId}
          onChange={onRootChange}
        />
        <AddressSelectField
          label="المنطقة الفرعية"
          placeholder="اختر المنطقة الفرعية"
          options={adminAreaLevel2Nodes}
          value={selectedAdminAreaLevel2Id}
          disabled={!selectedRootId}
          onChange={onAdminAreaLevel2Change}
        />
        <AddressSelectField
          label="المدينة"
          placeholder="اختر المدينة"
          options={localityNodes}
          value={selectedLocalityId}
          disabled={!selectedAdminAreaLevel2Id}
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

      <div className="grid gap-3 md:grid-cols-[minmax(0,1.3fr)_minmax(220px,0.7fr)]">
        <article className="rounded-2xl border border-[#eadbc7] bg-white px-4 py-3">
          <p className="text-xs font-bold text-[#8b735d]">العنوان المختار</p>
          <p className="mt-2 text-sm font-black text-[#2f2218]">
            {addressSummary || 'ابدأ باختيار موقع التوصيل من القوائم المتاحة.'}
          </p>
          {selectionIncomplete ? (
            <p className="mt-2 text-xs font-semibold text-amber-700">
              ما زال هناك مستوى متاح أسفل العنوان الحالي. أكمل الاختيار للوصول إلى عقدة نهائية.
            </p>
          ) : null}
          {!selectionIncomplete && quote?.message ? (
            <p className="mt-2 text-xs font-semibold text-rose-700">{quote.message}</p>
          ) : null}
        </article>

        <article
          className={[
            'rounded-2xl border px-4 py-3',
            quote?.available ? 'border-emerald-300 bg-emerald-50' : 'border-[#eadbc7] bg-white',
          ].join(' ')}
        >
          <p className="text-xs font-bold text-[#8b735d]">رسوم التوصيل</p>
          <p className="mt-2 text-lg font-black text-[#2f2218]">
            {quoteLoading ? 'جارٍ الحساب...' : quote?.delivery_fee != null ? `${quote.delivery_fee.toFixed(2)} د.ج` : '--'}
          </p>
          {quote?.resolved_node_label ? (
            <p className="mt-2 text-xs text-[#7a6450]">تم اعتماد التسعير من: {quote.resolved_node_label}</p>
          ) : null}
        </article>
      </div>
    </div>
  );
}
