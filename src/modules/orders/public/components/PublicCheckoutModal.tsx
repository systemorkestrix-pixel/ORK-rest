import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Bike, CheckCircle2, ClipboardCheck, Copy, ShoppingBag, Store, UtensilsCrossed, X } from 'lucide-react';
import { useLocation } from 'react-router-dom';

import type {
  DeliveryAddressNode,
  DeliveryLocationPricingQuote,
  Order,
  OrderType,
  PublicSecondaryOption,
  TableInfo,
} from '@/shared/api/types';
import { formatOrderTrackingId } from '@/shared/utils/order';
import type { CartRow, CartSecondarySelection } from '../publicOrder.helpers';
import { PublicDeliveryAddressSelector } from './PublicDeliveryAddressSelector';

interface PublicCheckoutModalProps {
  open: boolean;
  tableId?: number;
  orderType: OrderType;
  orderTypeOptions: Array<{ value: OrderType; label: string }>;
  availablePublicTables: TableInfo[];
  cartItems: CartRow[];
  subtotal: number;
  secondaryCatalog: PublicSecondaryOption[];
  secondarySelections: Record<number, CartSecondarySelection>;
  deliveryFee: number;
  minDeliveryOrderAmount: number;
  total: number;
  requirePhoneForTakeaway: boolean;
  requirePhoneForDelivery: boolean;
  phone: string;
  addressSummary: string;
  notes: string;
  selectedTable?: number;
  structuredDeliveryReady: boolean;
  deliveryRootNodes: DeliveryAddressNode[];
  deliveryAdminAreaLevel2Nodes: DeliveryAddressNode[];
  deliveryLocalityNodes: DeliveryAddressNode[];
  deliverySublocalityNodes: DeliveryAddressNode[];
  selectedDeliveryRootId?: number;
  selectedDeliveryAdminAreaLevel2Id?: number;
  selectedDeliveryLocalityId?: number;
  selectedDeliverySublocalityId?: number;
  deliveryQuote: DeliveryLocationPricingQuote | null | undefined;
  deliveryQuoteLoading: boolean;
  deliverySelectionIncomplete: boolean;
  submitPending: boolean;
  submitDisabled: boolean;
  deliveryEnabled: boolean;
  deliveryBlockedReason: string;
  error: string;
  lastCreatedOrder: Order | null;
  showSuccess: boolean;
  onClose: () => void;
  onOrderTypeChange: (value: OrderType) => void;
  onPhoneChange: (value: string) => void;
  onNotesChange: (value: string) => void;
  onSecondaryQuantityChange: (option: PublicSecondaryOption, delta: number) => void;
  onSelectedTableChange: (value: number | undefined) => void;
  onDeliveryRootChange: (value: number | undefined) => void;
  onDeliveryAdminAreaLevel2Change: (value: number | undefined) => void;
  onDeliveryLocalityChange: (value: number | undefined) => void;
  onDeliverySublocalityChange: (value: number | undefined) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCloseSuccess: () => void;
}

type CheckoutStep = 'fulfillment' | 'secondary' | 'review';

const orderTypeIcons = {
  takeaway: Store,
  delivery: Bike,
  'dine-in': UtensilsCrossed,
} satisfies Record<OrderType, typeof Store>;

function getInitialStep(tableId: number | undefined, hasSecondaryStep: boolean): CheckoutStep {
  if (tableId) {
    return hasSecondaryStep ? 'secondary' : 'review';
  }
  return 'fulfillment';
}

function getStepItems(
  tableId: number | undefined,
  hasSecondaryStep: boolean,
): Array<{ id: CheckoutStep; label: string }> {
  return [
    ...(tableId ? [] : [{ id: 'fulfillment' as const, label: 'المسار' }]),
    ...(hasSecondaryStep ? [{ id: 'secondary' as const, label: 'الإضافات' }] : []),
    { id: 'review', label: 'المراجعة' },
  ];
}

function summaryOrderTypeLabel(orderType: OrderType, selectedLabel: string): string {
  if (orderType === 'dine-in') return 'طلب من الطاولة';
  if (orderType === 'delivery') return selectedLabel;
  return 'استلام من المطعم';
}

function ReviewRow({ label, quantity, amount }: { label: string; quantity: number; amount: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-[#eadbc7] bg-[#fffaf3] px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-black text-[#2d2117]">{label}</p>
        <p className="mt-1 text-xs font-semibold text-[#7c6651]">× {quantity}</p>
      </div>
      <p className="shrink-0 text-sm font-black text-[#a05e24]">{amount}</p>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="rounded-2xl border border-[#eadbc7] bg-white p-4">
      <p className="text-xs font-bold text-[#8b735d]">{label}</p>
      <p className="mt-2 text-base font-black text-[#2d2117]">{value}</p>
    </article>
  );
}

function SummaryBadge({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-[#f0e2cf] bg-[#fcf6ec] px-3 py-3 text-center">
      <p className="text-[11px] font-bold text-[#8b735d]">{label}</p>
      <p className="mt-1 text-lg font-black text-[#2d2117]">{value}</p>
    </div>
  );
}

function TotalRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <p className={`text-sm ${strong ? 'font-black text-[#2d2117]' : 'font-semibold text-[#6f5b49]'}`}>{label}</p>
      <p className={`text-sm ${strong ? 'font-black text-[#2d2117]' : 'font-black text-[#a05e24]'}`}>{value}</p>
    </div>
  );
}

function getRowAmount(price: number, quantity: number): string {
  return `${(price * quantity).toFixed(2)} د.ج`;
}

export function PublicCheckoutModal(props: PublicCheckoutModalProps) {
  const location = useLocation();
  const tenantPrefix = location.pathname.match(/^\/t\/[^/]+/i)?.[0] ?? '';
  const scopedTrackPath = tenantPrefix ? `${tenantPrefix}/track` : '/track';
  const {
    open,
    tableId,
    orderType,
    orderTypeOptions,
    availablePublicTables,
    cartItems,
    subtotal,
    secondaryCatalog,
    secondarySelections,
    deliveryFee,
    minDeliveryOrderAmount,
    total,
    requirePhoneForTakeaway,
    requirePhoneForDelivery,
    phone,
    addressSummary,
    notes,
    selectedTable,
    structuredDeliveryReady,
    deliveryRootNodes,
    deliveryAdminAreaLevel2Nodes,
    deliveryLocalityNodes,
    deliverySublocalityNodes,
    selectedDeliveryRootId,
    selectedDeliveryAdminAreaLevel2Id,
    selectedDeliveryLocalityId,
    selectedDeliverySublocalityId,
    deliveryQuote,
    deliveryQuoteLoading,
    deliverySelectionIncomplete,
    submitPending,
    submitDisabled,
    deliveryEnabled,
    deliveryBlockedReason,
    error,
    lastCreatedOrder,
    showSuccess,
    onClose,
    onOrderTypeChange,
    onPhoneChange,
    onNotesChange,
    onSecondaryQuantityChange,
    onSelectedTableChange,
    onDeliveryRootChange,
    onDeliveryAdminAreaLevel2Change,
    onDeliveryLocalityChange,
    onDeliverySublocalityChange,
    onSubmit,
    onCloseSuccess,
  } = props;

  const hasSecondaryStep = secondaryCatalog.length > 0;
  const stepItems = useMemo(() => getStepItems(tableId, hasSecondaryStep), [tableId, hasSecondaryStep]);
  const [step, setStep] = useState<CheckoutStep>(getInitialStep(tableId, hasSecondaryStep));
  const [copied, setCopied] = useState(false);

  const secondaryRows = useMemo(() => Object.values(secondarySelections), [secondarySelections]);
  const cartItemCount = useMemo(
    () =>
      cartItems.reduce((sum, item) => sum + item.quantity, 0) +
      secondaryRows.reduce((sum, item) => sum + item.quantity, 0),
    [cartItems, secondaryRows],
  );
  const selectedOrderTypeLabel = useMemo(
    () => orderTypeOptions.find((option) => option.value === orderType)?.label ?? orderType,
    [orderType, orderTypeOptions],
  );
  const selectedTableInfo = useMemo(
    () => availablePublicTables.find((table) => table.id === selectedTable),
    [availablePublicTables, selectedTable],
  );
  const needsPhone =
    !tableId &&
    ((orderType === 'delivery' && requirePhoneForDelivery) || (orderType === 'takeaway' && requirePhoneForTakeaway));

  useEffect(() => {
    if (!open) {
      setStep(getInitialStep(tableId, hasSecondaryStep));
      setCopied(false);
      return;
    }
    if (showSuccess) return;
    setCopied(false);
    setStep((current) => {
      if (!hasSecondaryStep && current === 'secondary') return 'review';
      if (tableId && current === 'fulfillment') return getInitialStep(tableId, hasSecondaryStep);
      return current;
    });
  }, [open, showSuccess, tableId, hasSecondaryStep]);

  if (!open) return null;

  const doneIndex = stepItems.findIndex((item) => item.id === step);
  const deliveryMinimumReached = minDeliveryOrderAmount <= 0 || subtotal >= minDeliveryOrderAmount;
  const canAdvanceFromFulfillment =
    tableId ||
    (orderType === 'dine-in'
      ? Boolean(selectedTable)
      : orderType === 'delivery'
        ? deliveryEnabled
        : true);

  const copyTrackingCode = async () => {
    if (!lastCreatedOrder) return;
    try {
      await navigator.clipboard.writeText(lastCreatedOrder.tracking_code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const goNext = () => {
    const currentIndex = stepItems.findIndex((item) => item.id === step);
    const nextItem = stepItems[Math.min(stepItems.length - 1, currentIndex + 1)];
    setStep(nextItem.id);
  };

  const goPrevious = () => {
    const currentIndex = stepItems.findIndex((item) => item.id === step);
    const previousItem = stepItems[Math.max(0, currentIndex - 1)];
    setStep(previousItem.id);
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#6d5845]/20 backdrop-blur-[2px]" dir="rtl">
      <div className="absolute inset-x-0 bottom-0 top-0 overflow-y-auto md:inset-0 md:flex md:items-center md:justify-center md:p-4">
        <div className="min-h-full w-full rounded-none border-0 bg-[#fffaf3] shadow-none md:min-h-0 md:max-h-[92vh] md:max-w-5xl md:overflow-hidden md:rounded-[34px] md:border md:border-[#eadbc7] md:shadow-[0_28px_90px_rgba(170,126,70,0.20)]">
          <div className="sticky top-0 z-10 border-b border-[#eadbc7] bg-[#fffaf3]/95 px-4 py-4 backdrop-blur md:px-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-black tracking-[0.18em] text-[#8b735d]">CHECKOUT</p>
                <h2 className="mt-2 text-2xl font-black text-[#2d2117]">
                  {showSuccess ? 'تم استلام طلبك' : 'مراجعة الطلب'}
                </h2>
                <p className="mt-1 text-sm font-semibold text-[#6f5b49]">
                  {showSuccess ? 'احتفظ بكود التتبع للمتابعة لاحقًا.' : 'اختر المسار ثم راجع الطلب وأكد الإرسال.'}
                </p>
              </div>

              <button
                type="button"
                onClick={showSuccess ? onCloseSuccess : onClose}
                className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#eadbc7] bg-white text-[#5c4735] transition hover:bg-[#fff2df]"
                aria-label="إغلاق"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {!showSuccess ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {stepItems.map((item, index) => {
                  const itemIndex = stepItems.findIndex((stepItem) => stepItem.id === item.id);
                  const active = item.id === step;
                  const done = itemIndex < doneIndex;
                  const locked = itemIndex > doneIndex;

                  return (
                    <button
                      key={item.id}
                      type="button"
                      disabled={locked}
                      onClick={() => !locked && setStep(item.id)}
                      className={[
                        'inline-flex items-center gap-2 rounded-2xl border px-4 py-2 text-sm font-black transition',
                        active
                          ? 'border-[#e3a056] bg-[#fff1dd] text-[#8a531c]'
                          : done
                            ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                            : 'border-[#eadbc7] bg-white text-[#6d5845]',
                        locked ? 'cursor-not-allowed opacity-60' : '',
                      ].join(' ')}
                    >
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/80 text-xs">
                        {index + 1}
                      </span>
                      {item.label}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>

          <div className="p-4 md:max-h-[calc(92vh-170px)] md:overflow-y-auto md:p-6">
            {showSuccess && lastCreatedOrder ? (
              <div className="space-y-4">
                <section className="rounded-3xl border border-emerald-300 bg-emerald-50 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                      <p className="inline-flex items-center gap-2 text-sm font-black text-emerald-700">
                        <CheckCircle2 className="h-5 w-5" />
                        تم تسجيل الطلب بنجاح
                      </p>
                      <h3 className="text-3xl font-black tracking-wide text-[#2d2117]">
                        {lastCreatedOrder.tracking_code}
                      </h3>
                      <p className="text-sm text-[#5f4a38]">
                        رقم الطلب المختصر: {formatOrderTrackingId(lastCreatedOrder.id)}
                      </p>
                    </div>
                    <div className="grid gap-2">
                      <button
                        type="button"
                        onClick={copyTrackingCode}
                        className="inline-flex min-h-[42px] items-center justify-center gap-2 rounded-2xl bg-[#e38b38] px-4 text-sm font-black text-[#1a120d] transition hover:bg-[#ef9a4b]"
                      >
                        <Copy className="h-4 w-4" />
                        {copied ? 'تم نسخ الكود' : 'نسخ كود التتبع'}
                      </button>
                      <a
                        href={scopedTrackPath}
                        className="inline-flex min-h-[42px] items-center justify-center gap-2 rounded-2xl border border-[#eadbc7] bg-white px-4 text-center text-sm font-black text-[#2d2117] transition hover:bg-[#fff2df]"
                      >
                        <ClipboardCheck className="h-4 w-4" />
                        صفحة التتبع
                      </a>
                    </div>
                  </div>
                </section>

                <section className="grid gap-3 md:grid-cols-3">
                  <SummaryCard label="نوع الطلب" value={selectedOrderTypeLabel} />
                  <SummaryCard label="عدد الأصناف" value={lastCreatedOrder.items.length} />
                  <SummaryCard label="الإجمالي" value={`${lastCreatedOrder.total.toFixed(2)} د.ج`} />
                </section>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="space-y-5">
                {step === 'fulfillment' ? (
                  <section className="space-y-4">
                    <div className="grid gap-3 md:grid-cols-3">
                      {orderTypeOptions.map((option) => {
                        const Icon = orderTypeIcons[option.value];
                        const active = option.value === orderType;
                        const disabled = option.value === 'delivery' && !deliveryEnabled;

                        return (
                          <button
                            key={option.value}
                            type="button"
                            disabled={disabled}
                            onClick={() => onOrderTypeChange(option.value)}
                            className={[
                              'rounded-[28px] border px-4 py-5 text-right transition',
                              active
                                ? 'border-[#e3a056] bg-[#fff2df] shadow-[0_18px_40px_rgba(227,139,56,0.14)]'
                                : 'border-[#eadbc7] bg-white hover:bg-[#fff8ee]',
                              disabled ? 'cursor-not-allowed opacity-60' : '',
                            ].join(' ')}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-base font-black text-[#2d2117]">{option.label}</p>
                                <p className="mt-2 text-xs font-semibold text-[#7c6651]">
                                  {option.value === 'dine-in'
                                    ? 'لطلبات الطاولات داخل المطعم.'
                                    : option.value === 'delivery'
                                      ? 'للإرسال إلى العنوان.'
                                      : 'للاستلام من المطعم.'}
                                </p>
                              </div>
                              <span
                                className={[
                                  'inline-flex h-11 w-11 items-center justify-center rounded-2xl border',
                                  active
                                    ? 'border-[#e3a056] bg-white text-[#a05e24]'
                                    : 'border-[#eadbc7] bg-[#fffaf3] text-[#5c4735]',
                                ].join(' ')}
                              >
                                <Icon className="h-5 w-5" />
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>

                    {!tableId && orderType === 'dine-in' ? (
                      <section className="space-y-3 rounded-[28px] border border-[#eadbc7] bg-white p-4">
                        <div>
                          <p className="text-sm font-black text-[#2d2117]">اختر الطاولة</p>
                          <p className="mt-1 text-xs font-semibold text-[#7c6651]">الطاولة مطلوبة قبل متابعة الطلب.</p>
                        </div>

                        {availablePublicTables.length > 0 ? (
                          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                            {availablePublicTables.map((table) => {
                              const active = selectedTable === table.id;
                              return (
                                <button
                                  key={table.id}
                                  type="button"
                                  onClick={() => onSelectedTableChange(table.id)}
                                  className={[
                                    'rounded-2xl border px-3 py-4 text-center transition',
                                    active
                                      ? 'border-[#e3a056] bg-[#fff2df] text-[#8a531c]'
                                      : 'border-[#eadbc7] bg-[#fffaf3] text-[#2d2117] hover:bg-[#fff8ee]',
                                  ].join(' ')}
                                >
                                  <p className="text-xs font-bold text-[#8b735d]">الطاولة</p>
                                  <p className="mt-1 text-xl font-black">#{table.id}</p>
                                </button>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="rounded-2xl border border-dashed border-[#eadbc7] bg-[#fffaf3] px-4 py-6 text-center text-sm font-semibold text-[#7c6651]">
                            لا توجد طاولات متاحة الآن.
                          </div>
                        )}
                      </section>
                    ) : null}

                    {!tableId && orderType === 'delivery' && !deliveryEnabled ? (
                      <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                        {deliveryBlockedReason}
                      </div>
                    ) : null}
                  </section>
                ) : null}

                {step === 'secondary' ? (
                  <section className="space-y-4">
                    <div>
                      <p className="text-sm font-black text-[#2d2117]">إضافات سريعة</p>
                      <p className="mt-1 text-xs font-semibold text-[#7c6651]">أضف ما تحتاجه ثم تابع مباشرة.</p>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2">
                      {secondaryCatalog.map((option) => {
                        const selection = secondarySelections[option.product_id];
                        const quantity = selection?.quantity ?? 0;
                        const reachedMax = option.max_quantity > 0 && quantity >= option.max_quantity;

                        return (
                          <article
                            key={option.product_id}
                            className="rounded-[26px] border border-[#eadbc7] bg-white p-4"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-base font-black text-[#2d2117]">{option.name}</p>
                                <p className="mt-1 text-xs font-semibold text-[#7c6651]">
                                  {option.price.toFixed(2)} د.ج
                                  {option.max_quantity > 0 ? ` • الحد ${option.max_quantity}` : ''}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  onClick={() => onSecondaryQuantityChange(option, -1)}
                                  className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[#eadbc7] bg-[#fffaf3] text-[#4a382a] transition hover:bg-[#fff2df]"
                                  aria-label={`تقليل ${option.name}`}
                                >
                                  -
                                </button>
                                <span className="min-w-10 text-center text-lg font-black text-[#2d2117]">{quantity}</span>
                                <button
                                  type="button"
                                  disabled={reachedMax}
                                  onClick={() => onSecondaryQuantityChange(option, 1)}
                                  className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-[#e38b38] text-lg font-black text-[#1a120d] transition hover:bg-[#ef9a4b] disabled:cursor-not-allowed disabled:bg-[#edd8bf] disabled:text-[#7c6651]"
                                  aria-label={`زيادة ${option.name}`}
                                >
                                  +
                                </button>
                              </div>
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </section>
                ) : null}

                {step === 'review' ? (
                  <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-[#2d2117]">
                        <ShoppingBag className="h-5 w-5" />
                        <h3 className="text-base font-black">محتوى الطلب</h3>
                      </div>

                      <div className="space-y-3 rounded-[28px] border border-[#eadbc7] bg-white p-4">
                        {cartItems.map((item) => (
                          <ReviewRow
                            key={`product-${item.product.id}`}
                            label={item.product.name}
                            quantity={item.quantity}
                            amount={getRowAmount(item.product.price, item.quantity)}
                          />
                        ))}

                        {secondaryRows.map((item) => (
                          <ReviewRow
                            key={`secondary-${item.option.product_id}`}
                            label={item.option.name}
                            quantity={item.quantity}
                            amount={getRowAmount(item.option.price, item.quantity)}
                          />
                        ))}
                      </div>

                      <div className="space-y-3 rounded-[28px] border border-[#eadbc7] bg-white p-4">
                        <TotalRow label="قيمة الطلب" value={`${subtotal.toFixed(2)} د.ج`} />
                        {deliveryFee > 0 ? <TotalRow label="رسوم التوصيل" value={`${deliveryFee.toFixed(2)} د.ج`} /> : null}
                        <div className="border-t border-[#eadbc7] pt-3">
                          <TotalRow label="الإجمالي" value={`${total.toFixed(2)} د.ج`} strong />
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                        <SummaryBadge label="المسار" value={summaryOrderTypeLabel(orderType, selectedOrderTypeLabel)} />
                        <SummaryBadge label="الأصناف" value={cartItemCount} />
                        <SummaryBadge
                          label={tableId || orderType === 'dine-in' ? 'الطاولة' : 'الحالة'}
                          value={
                            tableId
                              ? `#${tableId}`
                              : orderType === 'dine-in'
                                ? selectedTableInfo
                                  ? `#${selectedTableInfo.id}`
                                  : '--'
                                : 'جاهز للإرسال'
                          }
                        />
                      </div>

                      <section className="space-y-4 rounded-[28px] border border-[#eadbc7] bg-white p-4">
                        {needsPhone ? (
                          <label className="block">
                            <span className="mb-2 block text-sm font-black text-[#2d2117]">رقم الهاتف</span>
                            <input
                              type="tel"
                              inputMode="tel"
                              value={phone}
                              onChange={(event) => onPhoneChange(event.target.value)}
                              className="w-full rounded-2xl border border-[#e4d5bf] bg-[#fffaf3] px-4 py-3 text-sm font-semibold text-[#2f2218] outline-none transition focus:border-[#d59045]"
                              placeholder="أدخل رقم الهاتف"
                            />
                          </label>
                        ) : null}

                        {!tableId && orderType === 'delivery' ? (
                          <>
                            <PublicDeliveryAddressSelector
                              rootNodes={deliveryRootNodes}
                              adminAreaLevel2Nodes={deliveryAdminAreaLevel2Nodes}
                              localityNodes={deliveryLocalityNodes}
                              sublocalityNodes={deliverySublocalityNodes}
                              selectedRootId={selectedDeliveryRootId}
                              selectedAdminAreaLevel2Id={selectedDeliveryAdminAreaLevel2Id}
                              selectedLocalityId={selectedDeliveryLocalityId}
                              selectedSublocalityId={selectedDeliverySublocalityId}
                              addressSummary={addressSummary}
                              quote={deliveryQuote}
                              quoteLoading={deliveryQuoteLoading}
                              selectionIncomplete={deliverySelectionIncomplete}
                              structuredReady={structuredDeliveryReady}
                              onRootChange={onDeliveryRootChange}
                              onAdminAreaLevel2Change={onDeliveryAdminAreaLevel2Change}
                              onLocalityChange={onDeliveryLocalityChange}
                              onSublocalityChange={onDeliverySublocalityChange}
                            />

                            {minDeliveryOrderAmount > 0 ? (
                              <div
                                className={[
                                  'rounded-2xl border px-4 py-3 text-sm font-semibold',
                                  deliveryMinimumReached
                                    ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                                    : 'border-amber-300 bg-amber-50 text-amber-800',
                                ].join(' ')}
                              >
                                الحد الأدنى للتوصيل: {minDeliveryOrderAmount.toFixed(2)} د.ج
                              </div>
                            ) : null}
                          </>
                        ) : null}

                        <label className="block">
                          <span className="mb-2 block text-sm font-black text-[#2d2117]">ملاحظة الطلب</span>
                          <textarea
                            value={notes}
                            onChange={(event) => onNotesChange(event.target.value)}
                            rows={4}
                            className="w-full resize-none rounded-2xl border border-[#e4d5bf] bg-[#fffaf3] px-4 py-3 text-sm font-semibold text-[#2f2218] outline-none transition focus:border-[#d59045]"
                            placeholder="اكتب الملاحظة إذا لزم الأمر"
                          />
                        </label>
                      </section>

                      {error ? (
                        <div className="rounded-2xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
                          {error}
                        </div>
                      ) : null}
                    </div>
                  </section>
                ) : null}

                <div className="sticky bottom-0 border-t border-[#eadbc7] bg-[#fffaf3]/95 px-0 pt-4 backdrop-blur">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="rounded-2xl border border-[#eadbc7] bg-white px-4 py-3">
                      <p className="text-[11px] font-bold text-[#8b735d]">الإجمالي الحالي</p>
                      <p className="mt-1 text-lg font-black text-[#2d2117]">{total.toFixed(2)} د.ج</p>
                    </div>

                    <div className="grid gap-2 sm:grid-cols-2 lg:flex">
                      <button
                        type="button"
                        onClick={step === stepItems[0]?.id ? onClose : goPrevious}
                        className="inline-flex min-h-[46px] items-center justify-center rounded-2xl border border-[#eadbc7] bg-white px-5 text-sm font-black text-[#5c4735] transition hover:bg-[#fff2df]"
                      >
                        {step === stepItems[0]?.id ? 'إغلاق' : 'رجوع'}
                      </button>

                      {step !== 'review' ? (
                        <button
                          type="button"
                          disabled={step === 'fulfillment' && !canAdvanceFromFulfillment}
                          onClick={goNext}
                          className="inline-flex min-h-[46px] items-center justify-center rounded-2xl bg-[#e38b38] px-5 text-sm font-black text-[#1a120d] transition hover:bg-[#ef9a4b] disabled:cursor-not-allowed disabled:bg-[#edd8bf] disabled:text-[#7c6651]"
                        >
                          متابعة
                        </button>
                      ) : (
                        <button
                          type="submit"
                          disabled={submitDisabled}
                          className="inline-flex min-h-[46px] items-center justify-center rounded-2xl bg-[#e38b38] px-5 text-sm font-black text-[#1a120d] transition hover:bg-[#ef9a4b] disabled:cursor-not-allowed disabled:bg-[#edd8bf] disabled:text-[#7c6651]"
                        >
                          {submitPending ? 'جارٍ الإرسال...' : 'تأكيد الطلب'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
