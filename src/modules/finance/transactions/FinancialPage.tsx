import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { CashboxMovement, DeliverySettlement, FinancialTransaction, ShiftClosure } from '@/shared/api/types';
import { useDataView } from '@/shared/hooks/useDataView';
import { TABLE_STATUS_CHIP_BASE } from '@/shared/ui/tableAppearance';
import { TableControls } from '@/shared/ui/TableControls';
import { TablePagination } from '@/shared/ui/TablePagination';
import { parseApiDateMs } from '@/shared/utils/date';
import { formatOrderTrackingId } from '@/shared/utils/order';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { sanitizeMojibakeText } from '@/shared/utils/textSanitizer';

type FinancialTab = 'overview' | 'cashbox' | 'settlements' | 'entries' | 'closures';

const financialTabs: Array<{ id: FinancialTab; label: string; subtitle: string }> = [
  { id: 'overview', label: 'الملخص', subtitle: 'قراءة اليوم وإغلاق الوردية' },
  { id: 'cashbox', label: 'الصندوق', subtitle: 'حركة النقد الداخل والخارج' },
  { id: 'settlements', label: 'تسويات التوصيل', subtitle: 'متابعة المندوبين والتوريد' },
  { id: 'entries', label: 'القيود المحاسبية', subtitle: 'تفاصيل القيود والمراجع' },
  { id: 'closures', label: 'سجل الإغلاقات', subtitle: 'أرشيف الورديات السابقة' },
];

const transactionTypeLabel: Record<string, string> = {
  sale: 'مبيعات',
  refund: 'مرتجعات',
  expense: 'مصروف',
  food_revenue: 'إيراد الطعام',
  delivery_revenue: 'إيراد التوصيل',
  driver_payable: 'مستحق المندوب',
  collection_clearing: 'ذمة التحصيل',
  collection_adjustment: 'فرق التحصيل',
  refund_food_revenue: 'عكس إيراد الطعام',
  refund_delivery_revenue: 'عكس إيراد التوصيل',
  reverse_driver_payable: 'عكس مستحق المندوب',
  reverse_collection_clearing: 'عكس ذمة التحصيل',
};

const transactionNoteFallback: Record<string, string> = {
  sale: 'تحصيل نقدي عند التسليم',
  refund: 'إرجاع مالي للطلب',
  expense: 'قيد مصروف تشغيلي',
  food_revenue: 'إثبات إيراد الطعام',
  delivery_revenue: 'إثبات إيراد التوصيل',
  driver_payable: 'إثبات مستحق المندوب',
  collection_clearing: 'إثبات ذمة التحصيل',
  collection_adjustment: 'فرق تحصيل',
  refund_food_revenue: 'عكس إيراد الطعام',
  refund_delivery_revenue: 'عكس إيراد التوصيل',
  reverse_driver_payable: 'عكس مستحق المندوب',
  reverse_collection_clearing: 'عكس ذمة التحصيل',
};

const settlementStatusLabel: Record<string, string> = {
  pending: 'قيد التسوية',
  partially_remitted: 'توريد جزئي',
  remitted: 'مورّد',
  settled: 'مغلق',
  variance: 'فيه فرق',
  reversed: 'معكوس',
};

const cashboxDirectionLabel: Record<string, string> = {
  in: 'داخل',
  out: 'خارج',
};

const cashboxTypeLabel: Record<string, string> = {
  driver_remittance: 'توريد مندوب',
  driver_payout: 'دفع مندوب',
  cash_order_collection: 'تحصيل طلب',
  cash_refund: 'استرجاع نقدي',
  cash_adjustment: 'تسوية نقدية',
};

const cashChannelLabel: Record<string, string> = {
  cash_drawer: 'درج الكاش',
  safe: 'الخزنة',
  bank: 'البنك',
  wallet: 'محفظة',
};

const accountCodeLabel: Record<string, string> = {
  REV_FOOD: 'إيراد الطعام',
  REV_DELIVERY: 'إيراد التوصيل',
  LIAB_DRIVER_PAYABLE: 'مستحقات المندوبين',
  ASSET_COLLECTION_CLEARING: 'ذمم التحصيل',
  ADJ_COLLECTION_VARIANCE: 'فروقات التحصيل',
};

const referenceEventLabel: Record<string, string> = {
  delivery_completed: 'تسليم طلب توصيل',
  delivery_refund: 'استرجاع طلب توصيل',
  order_cash_paid: 'تحصيل نقدي',
  order_refund: 'استرجاع طلب',
  legacy_backfill: 'ترحيل تاريخي',
};

const fallbackPhraseLabel: Record<string, string> = {
  full_delivery_fee: 'كامل رسم التوصيل',
  fixed_amount: 'مبلغ ثابت',
  percentage: 'نسبة',
  pending: 'قيد التسوية',
  partially_remitted: 'توريد جزئي',
  remitted: 'مورّد',
  settled: 'مغلق',
  reversed: 'معكوس',
  variance: 'فيه فرق',
  sale: 'مبيعات',
  refund: 'استرجاع',
  expense: 'مصروف',
  cash_drawer: 'درج الكاش',
  safe: 'الخزنة',
  bank: 'البنك',
  wallet: 'محفظة',
};

const fallbackTokenLabel: Record<string, string> = {
  food: 'طعام',
  revenue: 'إيراد',
  delivery: 'توصيل',
  driver: 'مندوب',
  payable: 'مستحق',
  collection: 'تحصيل',
  clearing: 'ذمة',
  adjustment: 'تسوية',
  reverse: 'عكس',
  cash: 'نقدي',
  order: 'طلب',
  remittance: 'توريد',
  payout: 'دفع',
  amount: 'مبلغ',
  account: 'حساب',
  asset: 'أصل',
  liability: 'التزام',
  variance: 'فرق',
  legacy: 'تاريخي',
  backfill: 'ترحيل',
  history: 'سجل',
};

function translateSystemCode(raw: string): string {
  const normalized = raw.trim().replace(/[:\-]+/g, '_').toLowerCase();
  if (!normalized) {
    return raw;
  }
  if (fallbackPhraseLabel[normalized]) {
    return fallbackPhraseLabel[normalized];
  }
  const parts = normalized.split('_').filter(Boolean);
  const translatedParts = parts.map((part) => fallbackTokenLabel[part] ?? part);
  return translatedParts.join(' ');
}

function translateAccountingText(raw: string): string {
  return raw
    .replace(/Delivery completed for order #(\d+)/g, (_, id: string) => `تسليم الطلب ${formatOrderTrackingId(Number(id))}`)
    .replace(/Delivery refund for order #(\d+)/g, (_, id: string) => `استرجاع الطلب ${formatOrderTrackingId(Number(id))}`)
    .replace(/Legacy backfill for order #(\d+)/g, (_, id: string) => `ترحيل تاريخي للطلب ${formatOrderTrackingId(Number(id))}`)
    .replace(/legacy_backfill/g, 'ترحيل تاريخي')
    .replace(/legacy_assumed_total/g, 'اعتماد إجمالي الطلب كسجل تاريخي')
    .replace(/legacy_variance_detected/g, 'فرق تحصيل مكتشف في سجل تاريخي')
    .replace(/assumed_amount_received=order\.total/g, 'تم اعتماد المبلغ المحصل مساويًا لإجمالي الطلب')
    .replace(/\brefunded\b/g, 'طلب مسترجع')
    .replace(/Cash order payment recorded\.?/g, 'تسجيل تحصيل نقدي للطلب')
    .replace(/Expense approved:/g, 'اعتماد مصروف:')
    .replace(/Cost center:/g, 'مركز التكلفة:')
    .replace(/Food revenue/g, 'إيراد الطعام')
    .replace(/Delivery revenue/g, 'إيراد التوصيل')
    .replace(/Driver payable/g, 'مستحق المندوب')
    .replace(/Driver collection clearing/g, 'ذمة التحصيل')
    .replace(/Delivery collection variance/g, 'فرق التحصيل')
    .replace(/Reverse food revenue/g, 'عكس إيراد الطعام')
    .replace(/Reverse delivery revenue/g, 'عكس إيراد التوصيل')
    .replace(/Reverse driver payable/g, 'عكس مستحق المندوب')
    .replace(/Reverse collection clearing/g, 'عكس ذمة التحصيل')
    .replace(/Reverse collection variance/g, 'عكس فرق التحصيل');
}

function renderFinancialNote(note: string | null | undefined, type: string): string {
  const cleaned = sanitizeMojibakeText(note, '');
  if (!cleaned.trim()) {
    return transactionNoteFallback[type] ?? 'قيد مالي';
  }
  return translateAccountingText(cleaned);
}

function renderAccountLabel(code: string | null | undefined): string {
  if (!code) {
    return '-';
  }
  return accountCodeLabel[code] ?? translateSystemCode(code);
}

function renderReferenceLabel(referenceGroup: string | null | undefined, orderId?: number | null): string {
  if (!referenceGroup) {
    return '-';
  }
  const [eventKey] = referenceGroup.split(':');
  const eventLabel = referenceEventLabel[eventKey] ?? `مرجع ${translateSystemCode(eventKey)}`;
  return orderId ? `${eventLabel} | ${formatOrderTrackingId(orderId)}` : eventLabel;
}

function asMoney(value: number): string {
  return `${value.toFixed(2)} د.ج`;
}

function localDateKey(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function badgeToneForSettlement(status: string): string {
  if (status === 'settled' || status === 'remitted') return 'ui-badge-success';
  if (status === 'variance' || status === 'partially_remitted') return 'ui-badge-warning';
  if (status === 'reversed') return 'ui-badge-danger';
  return 'ui-badge-info';
}

function settlementRowTone(status: string): 'success' | 'warning' | 'danger' {
  if (status === 'settled' || status === 'remitted') return 'success';
  if (status === 'reversed') return 'danger';
  return 'warning';
}

function MetricCard({
  title,
  value,
  tone,
  hint,
}: {
  title: string;
  value: string;
  tone: 'neutral' | 'success' | 'info' | 'warning' | 'danger' | 'primary';
  hint?: string;
}) {
  const toneClasses: Record<typeof tone, string> = {
    neutral: 'border-gray-200 bg-gray-50 text-gray-900',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    info: 'border-cyan-200 bg-cyan-50 text-cyan-800',
    warning: 'border-amber-200 bg-amber-50 text-amber-800',
    danger: 'border-rose-200 bg-rose-50 text-rose-800',
    primary: 'border-brand-200 bg-brand-50 text-brand-800',
  };

  return (
    <div className={`rounded-2xl border px-4 py-3 shadow-sm ${toneClasses[tone]}`}>
      <p className="text-xs font-semibold opacity-75">{title}</p>
      <p className="mt-1 text-lg font-black">{value}</p>
      {hint ? <p className="mt-1 text-[11px] opacity-75">{hint}</p> : null}
    </div>
  );
}

function CompactMetricCard({
  title,
  value,
  tone,
}: {
  title: string;
  value: string;
  tone: 'success' | 'info' | 'warning' | 'danger' | 'primary';
}) {
  const toneClasses: Record<typeof tone, string> = {
    success: 'border-emerald-500/35 bg-[var(--surface-card-soft)] text-emerald-200',
    info: 'border-cyan-500/35 bg-[var(--surface-card-soft)] text-cyan-200',
    warning: 'border-amber-500/35 bg-[var(--surface-card-soft)] text-amber-200',
    danger: 'border-rose-500/35 bg-[var(--surface-card-soft)] text-rose-200',
    primary: 'border-[var(--console-accent)]/45 bg-[var(--surface-card-soft)] text-[var(--text-primary)]',
  };

  return (
    <div className={`w-full rounded-2xl border px-3 py-3 shadow-sm ${toneClasses[tone]}`}>
      <p className="text-[11px] font-bold leading-5 opacity-80">{title}</p>
      <p className="mt-1 text-base font-black leading-6 sm:text-[1.05rem]">{value}</p>
    </div>
  );
}

function SectionBadge({
  children,
  tone = 'primary',
}: {
  children: any;
  tone?: 'success' | 'info' | 'warning' | 'danger' | 'primary';
}) {
  const toneClasses: Record<typeof tone, string> = {
    success: 'border-emerald-500/35 bg-[var(--surface-card-soft)] text-emerald-200',
    info: 'border-cyan-500/35 bg-[var(--surface-card-soft)] text-cyan-200',
    warning: 'border-amber-500/35 bg-[var(--surface-card-soft)] text-amber-200',
    danger: 'border-rose-500/35 bg-[var(--surface-card-soft)] text-rose-200',
    primary: 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]',
  };

  return <div className={`rounded-lg border px-2 py-1 text-[11px] font-bold ${toneClasses[tone]}`}>{children}</div>;
}

function SummaryStrip({ children }: { children: any }) {
  return <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">{children}</div>;
}

function renderShiftStatus(
  todayClosure: ShiftClosure | undefined,
  variancePreview: number
): { title: string; value: string; hint: string; tone: 'success' | 'warning' } {
  if (todayClosure) {
    const isBalanced = Math.abs(todayClosure.variance) < 0.009;
    return {
      title: isBalanced ? 'الوردية مطابقة' : 'الوردية فيها فرق',
      value: asMoney(todayClosure.variance),
      hint: `أغلقت اليوم عند ${new Date(parseApiDateMs(todayClosure.closed_at)).toLocaleTimeString('ar-DZ-u-nu-latn')}`,
      tone: isBalanced ? 'success' : 'warning',
    };
  }

  const isBalanced = Math.abs(variancePreview) < 0.009;
  return {
    title: isBalanced ? 'مطابقة مبدئية' : 'فرق مبدئي',
    value: asMoney(variancePreview),
    hint: 'يتغير حسب النقد الفعلي المدخل قبل الإغلاق',
    tone: isBalanced ? 'success' : 'warning',
  };
}

interface FinancialPageProps {
  initialTab?: FinancialTab;
}

export function FinancialPage({ initialTab = 'overview' }: FinancialPageProps) {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<FinancialTab>(initialTab);

  const [entrySearch, setEntrySearch] = useState('');
  const [entrySortBy, setEntrySortBy] = useState('created_at');
  const [entrySortDirection, setEntrySortDirection] = useState<'asc' | 'desc'>('desc');
  const [entryPage, setEntryPage] = useState(1);

  const [settlementSearch, setSettlementSearch] = useState('');
  const [settlementSortBy, setSettlementSortBy] = useState('recognized_at');
  const [settlementSortDirection, setSettlementSortDirection] = useState<'asc' | 'desc'>('desc');
  const [settlementPage, setSettlementPage] = useState(1);

  const [cashboxSearch, setCashboxSearch] = useState('');
  const [cashboxSortBy, setCashboxSortBy] = useState('created_at');
  const [cashboxSortDirection, setCashboxSortDirection] = useState<'asc' | 'desc'>('desc');
  const [cashboxPage, setCashboxPage] = useState(1);

  const [closureSearch, setClosureSearch] = useState('');
  const [closureSortBy, setClosureSortBy] = useState('closed_at');
  const [closureSortDirection, setClosureSortDirection] = useState<'asc' | 'desc'>('desc');
  const [closurePage, setClosurePage] = useState(1);

  const [openingCash, setOpeningCash] = useState('0');
  const [actualCash, setActualCash] = useState('0');
  const [closureNote, setClosureNote] = useState('');

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const transactionsQuery = useQuery({
    queryKey: ['manager-financial'],
    queryFn: () => api.managerFinancialTransactions(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const closuresQuery = useQuery({
    queryKey: ['manager-shift-closures'],
    queryFn: () => api.managerShiftClosures(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const settlementsQuery = useQuery({
    queryKey: ['manager-delivery-settlements'],
    queryFn: () => api.managerDeliverySettlements(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const cashboxQuery = useQuery({
    queryKey: ['manager-cashbox-movements'],
    queryFn: () => api.managerCashboxMovements(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const createClosureMutation = useMutation({
    mutationFn: () =>
      api.managerCreateShiftClosure(role ?? 'manager', {
        opening_cash: Number(openingCash),
        actual_cash: Number(actualCash),
        note: closureNote.trim() || null,
      }),
    onSuccess: () => {
      setClosureNote('');
      queryClient.invalidateQueries({ queryKey: ['manager-shift-closures'] });
      queryClient.invalidateQueries({ queryKey: ['manager-cashbox-movements'] });
      queryClient.invalidateQueries({ queryKey: ['manager-dashboard-operational-heart'] });
      queryClient.invalidateQueries({ queryKey: ['manager-dashboard-smart-orders'] });
      queryClient.invalidateQueries({ queryKey: ['manager-audit-system-logs'] });
    },
  });

  const entriesView = useDataView<FinancialTransaction>({
    rows: transactionsQuery.data ?? [],
    search: entrySearch,
    page: entryPage,
    pageSize: 12,
    sortBy: entrySortBy,
    sortDirection: entrySortDirection,
    searchAccessor: (row) =>
      `${row.id} ${row.type} ${row.account_code ?? ''} ${row.reference_group ?? ''} ${row.delivery_settlement_id ?? ''} ${renderFinancialNote(row.note, row.type)} ${row.order_id ?? ''} ${row.order_id ? formatOrderTrackingId(row.order_id) : ''}`,
    sortAccessors: {
      created_at: (row) => parseApiDateMs(row.created_at),
      amount: (row) => row.amount,
      type: (row) => row.type,
      order_id: (row) => row.order_id ?? 0,
    },
  });

  const settlementsView = useDataView<DeliverySettlement>({
    rows: settlementsQuery.data ?? [],
    search: settlementSearch,
    page: settlementPage,
    pageSize: 10,
    sortBy: settlementSortBy,
    sortDirection: settlementSortDirection,
    searchAccessor: (row) =>
      `${row.id} ${row.order_id} ${formatOrderTrackingId(row.order_id)} ${row.driver_id} ${row.status} ${row.variance_reason ?? ''} ${row.note ?? ''}`,
    sortAccessors: {
      recognized_at: (row) => parseApiDateMs(row.recognized_at),
      order_id: (row) => row.order_id,
      driver_due_amount: (row) => row.driver_due_amount,
      store_due_amount: (row) => row.store_due_amount,
      variance_amount: (row) => row.variance_amount,
    },
  });

  const cashboxView = useDataView<CashboxMovement>({
    rows: cashboxQuery.data ?? [],
    search: cashboxSearch,
    page: cashboxPage,
    pageSize: 10,
    sortBy: cashboxSortBy,
    sortDirection: cashboxSortDirection,
    searchAccessor: (row) =>
      `${row.id} ${row.type} ${row.direction} ${row.cash_channel} ${row.order_id ?? ''} ${row.note ?? ''}`,
    sortAccessors: {
      created_at: (row) => parseApiDateMs(row.created_at),
      amount: (row) => row.amount,
      type: (row) => row.type,
      order_id: (row) => row.order_id ?? 0,
    },
  });

  const closuresView = useDataView<ShiftClosure>({
    rows: closuresQuery.data ?? [],
    search: closureSearch,
    page: closurePage,
    pageSize: 10,
    sortBy: closureSortBy,
    sortDirection: closureSortDirection,
    searchAccessor: (row) => `${row.business_date} ${row.note ?? ''} ${row.closed_by}`,
    sortAccessors: {
      closed_at: (row) => parseApiDateMs(row.closed_at),
      expected_cash: (row) => row.expected_cash,
      actual_cash: (row) => row.actual_cash,
      variance: (row) => row.variance,
    },
  });

  const todayDateKey = useMemo(() => localDateKey(new Date()), []);

  const todaySummary = useMemo(() => {
    const rows = (transactionsQuery.data ?? []).filter(
      (row) => localDateKey(new Date(parseApiDateMs(row.created_at))) === todayDateKey
    );
    const cashRows = (cashboxQuery.data ?? []).filter(
      (row) => localDateKey(new Date(parseApiDateMs(row.created_at))) === todayDateKey
    );

    const foodSales =
      rows.filter((row) => row.type === 'food_revenue').reduce((sum, row) => sum + row.amount, 0) -
      rows.filter((row) => row.type === 'refund_food_revenue').reduce((sum, row) => sum + row.amount, 0);
    const deliveryRevenue =
      rows.filter((row) => row.type === 'delivery_revenue').reduce((sum, row) => sum + row.amount, 0) -
      rows.filter((row) => row.type === 'refund_delivery_revenue').reduce((sum, row) => sum + row.amount, 0);
    const driverCost =
      rows.filter((row) => row.type === 'driver_payable').reduce((sum, row) => sum + row.amount, 0) -
      rows.filter((row) => row.type === 'reverse_driver_payable').reduce((sum, row) => sum + row.amount, 0);
    const operatingExpenses = rows
      .filter((row) => row.type === 'expense')
      .reduce((sum, row) => sum + row.amount, 0);
    const refunds = rows.filter((row) => row.type === 'refund').reduce((sum, row) => sum + row.amount, 0);
    const cashIn = cashRows.filter((row) => row.direction === 'in').reduce((sum, row) => sum + row.amount, 0);
    const cashOut = cashRows.filter((row) => row.direction === 'out').reduce((sum, row) => sum + row.amount, 0);
    const sales = foodSales + deliveryRevenue;
    const expenses = driverCost + operatingExpenses;

    return {
      foodSales,
      deliveryRevenue,
      driverCost,
      operatingExpenses,
      sales,
      refunds,
      expenses,
      cashIn,
      cashOut,
      net: sales - expenses,
    };
  }, [cashboxQuery.data, todayDateKey, transactionsQuery.data]);

  const settlementsSummary = useMemo(() => {
    const rows = settlementsQuery.data ?? [];
    const openRows = rows.filter((row) => row.status === 'pending' || row.status === 'partially_remitted' || row.status === 'variance');

    return {
      openCount: openRows.length,
      openStoreDue: openRows.reduce((sum, row) => sum + row.remaining_store_due_amount, 0),
      openDriverDue: openRows.reduce((sum, row) => sum + row.driver_due_amount, 0),
      varianceCount: rows.filter((row) => Math.abs(row.variance_amount) >= 0.009).length,
    };
  }, [settlementsQuery.data]);

  const overviewCashboxRows = useMemo(
    () =>
      [...(cashboxQuery.data ?? [])]
        .sort((a, b) => parseApiDateMs(b.created_at) - parseApiDateMs(a.created_at))
        .slice(0, 6),
    [cashboxQuery.data]
  );

  const overviewSettlementRows = useMemo(
    () =>
      [...(settlementsQuery.data ?? [])]
        .sort((a, b) => parseApiDateMs(b.recognized_at) - parseApiDateMs(a.recognized_at))
        .slice(0, 6),
    [settlementsQuery.data]
  );

  const overviewEntryRows = useMemo(
    () =>
      [...(transactionsQuery.data ?? [])]
        .sort((a, b) => parseApiDateMs(b.created_at) - parseApiDateMs(a.created_at))
        .slice(0, 6),
    [transactionsQuery.data]
  );

  const overviewExpenseRows = useMemo(
    () =>
      [...(transactionsQuery.data ?? [])]
        .filter((row) => row.type === 'expense')
        .sort((a, b) => parseApiDateMs(b.created_at) - parseApiDateMs(a.created_at))
        .slice(0, 5),
    [transactionsQuery.data]
  );

  const overviewClosureRows = useMemo(
    () =>
      [...(closuresQuery.data ?? [])]
        .sort((a, b) => parseApiDateMs(b.closed_at) - parseApiDateMs(a.closed_at))
        .slice(0, 5),
    [closuresQuery.data]
  );

  const entriesSummary = useMemo(() => {
    const rows = (transactionsQuery.data ?? []).filter(
      (row) => localDateKey(new Date(parseApiDateMs(row.created_at))) === todayDateKey
    );

    return {
      todayCount: rows.length,
      debitTotal: rows.filter((row) => row.direction === 'debit').reduce((sum, row) => sum + row.amount, 0),
      creditTotal: rows.filter((row) => row.direction === 'credit').reduce((sum, row) => sum + row.amount, 0),
    };
  }, [todayDateKey, transactionsQuery.data]);

  const closuresSummary = useMemo(() => {
    const rows = closuresQuery.data ?? [];
    const matchedCount = rows.filter((row) => Math.abs(row.variance) < 0.009).length;

    return {
      totalCount: rows.length,
      matchedCount,
      varianceCount: rows.length - matchedCount,
    };
  }, [closuresQuery.data]);

  const openingCashValue = Number(openingCash);
  const actualCashValue = Number(actualCash);
  const expectedCashPreview = (Number.isFinite(openingCashValue) ? openingCashValue : 0) + todaySummary.cashIn - todaySummary.cashOut;
  const variancePreview = (Number.isFinite(actualCashValue) ? actualCashValue : 0) - expectedCashPreview;
  const todayClosure = useMemo(
    () => (closuresQuery.data ?? []).find((row) => row.business_date === todayDateKey),
    [closuresQuery.data, todayDateKey]
  );
  const shiftStatus = renderShiftStatus(todayClosure, variancePreview);
  const activeTabMeta = financialTabs.find((tab) => tab.id === activeTab);
  const activeTabSummaryCards = useMemo(() => {
    if (activeTab === 'cashbox') {
      return [
        { title: 'داخل اليوم', value: asMoney(todaySummary.cashIn), tone: 'success' as const },
        { title: 'خارج اليوم', value: asMoney(todaySummary.cashOut), tone: 'danger' as const },
        {
          title: 'صافي الحركة',
          value: asMoney(todaySummary.cashIn - todaySummary.cashOut),
          tone: todaySummary.cashIn >= todaySummary.cashOut ? ('primary' as const) : ('warning' as const),
        },
        { title: 'فرق الوردية', value: shiftStatus.value, tone: shiftStatus.tone === 'success' ? ('success' as const) : ('warning' as const) },
      ];
    }

    if (activeTab === 'settlements') {
      return [
        { title: 'تسويات مفتوحة', value: `${settlementsSummary.openCount}`, tone: 'info' as const },
        { title: 'المتبقي للمطعم', value: asMoney(settlementsSummary.openStoreDue), tone: 'primary' as const },
        { title: 'مستحق المندوب', value: asMoney(settlementsSummary.openDriverDue), tone: 'warning' as const },
        { title: 'فروقات', value: `${settlementsSummary.varianceCount}`, tone: 'danger' as const },
      ];
    }

    if (activeTab === 'entries') {
      return [
        { title: 'قيود اليوم', value: `${entriesSummary.todayCount}`, tone: 'info' as const },
        { title: 'مدين اليوم', value: asMoney(entriesSummary.debitTotal), tone: 'primary' as const },
        { title: 'دائن اليوم', value: asMoney(entriesSummary.creditTotal), tone: 'success' as const },
        { title: 'صافي اليوم', value: asMoney(todaySummary.net), tone: 'warning' as const },
      ];
    }

    if (activeTab === 'closures') {
      return [
        { title: 'إجمالي الإغلاقات', value: `${closuresSummary.totalCount}`, tone: 'info' as const },
        { title: 'مطابقة', value: `${closuresSummary.matchedCount}`, tone: 'success' as const },
        { title: 'فيها فرق', value: `${closuresSummary.varianceCount}`, tone: 'warning' as const },
        {
          title: 'آخر إغلاق',
          value: overviewClosureRows[0]
            ? new Date(parseApiDateMs(overviewClosureRows[0].closed_at)).toLocaleTimeString('ar-DZ-u-nu-latn', {
                hour: '2-digit',
                minute: '2-digit',
              })
            : '-',
          tone: 'primary' as const,
        },
      ];
    }

    return [];
  }, [
    activeTab,
    closuresSummary.matchedCount,
    closuresSummary.totalCount,
    closuresSummary.varianceCount,
    entriesSummary.creditTotal,
    entriesSummary.debitTotal,
    entriesSummary.todayCount,
    overviewClosureRows,
    settlementsSummary.openCount,
    settlementsSummary.openDriverDue,
    settlementsSummary.openStoreDue,
    settlementsSummary.varianceCount,
    shiftStatus.tone,
    shiftStatus.value,
    todaySummary.cashIn,
    todaySummary.cashOut,
    todaySummary.net,
  ]);

  const closureError = createClosureMutation.isError
    ? createClosureMutation.error instanceof Error
      ? sanitizeMojibakeText(createClosureMutation.error.message, 'تعذر تنفيذ إغلاق الوردية.')
      : 'تعذر تنفيذ إغلاق الوردية.'
    : '';

  if (transactionsQuery.isLoading || closuresQuery.isLoading || settlementsQuery.isLoading || cashboxQuery.isLoading) {
    return <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">جارٍ تحميل البيانات المالية...</div>;
  }

  if (transactionsQuery.isError || closuresQuery.isError || settlementsQuery.isError || cashboxQuery.isError) {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">تعذر تحميل البيانات المالية.</div>;
  }

  return (
    <div className="admin-page space-y-4">
      {activeTab !== 'overview' ? (
        <section className="admin-card p-4">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-brand-700">القسم الحالي</p>
              <h2 className="mt-1 text-lg font-black text-gray-900">{activeTabMeta?.label ?? 'المالية'}</h2>
              <p className="text-sm text-gray-600">{activeTabMeta?.subtitle ?? 'تفاصيل مالية مباشرة للمستخدم النهائي.'}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <SectionBadge tone="primary">المحتوى أدناه خاص بهذا القسم</SectionBadge>
              <SectionBadge tone={shiftStatus.tone === 'success' ? 'success' : 'warning'}>{shiftStatus.title}</SectionBadge>
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 shadow-sm">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-bold text-gray-700">المؤشرات الإلزامية للقسم</p>
              <p className="text-[11px] font-semibold text-gray-500">هذه هي البطاقات المباشرة قبل السجلات والجداول</p>
            </div>
            <SummaryStrip>
              {activeTabSummaryCards.map((card) => (
                <CompactMetricCard key={card.title} title={card.title} value={card.value} tone={card.tone} />
              ))}
            </SummaryStrip>
          </div>
        </section>
      ) : null}

            {activeTab === 'overview' ? (
        <div className="space-y-4">
          <section className="admin-card p-4">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">إغلاق وردية اليوم</h3>
                <p className="text-sm text-gray-600">هذا هو قسم الإجراء الوحيد هنا. بقية الأقسام للقراءة السريعة ومراجعة الحركات فقط.</p>
              </div>
              <SectionBadge tone={shiftStatus.tone === 'success' ? 'success' : 'warning'}>{shiftStatus.title}</SectionBadge>
            </div>

            <div className="space-y-4">
              <div className="space-y-3">
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-xl border border-cyan-200 bg-cyan-50/80 px-3 py-3 text-cyan-900">
                    <p className="text-[11px] font-bold opacity-80">رصيد البداية</p>
                    <p className="mt-1 text-base font-black">{asMoney(Number.isFinite(openingCashValue) ? openingCashValue : 0)}</p>
                  </div>
                  <div className="rounded-xl border border-brand-200 bg-brand-50 px-3 py-3 text-brand-900">
                    <p className="text-[11px] font-bold opacity-80">الرصيد المتوقع</p>
                    <p className="mt-1 text-base font-black">{asMoney(expectedCashPreview)}</p>
                  </div>
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 px-3 py-3 text-emerald-900">
                    <p className="text-[11px] font-bold opacity-80">النقد الفعلي</p>
                    <p className="mt-1 text-base font-black">{asMoney(Number.isFinite(actualCashValue) ? actualCashValue : 0)}</p>
                  </div>
                  <div className={`rounded-xl border px-3 py-3 ${shiftStatus.tone === 'success' ? 'border-emerald-200 bg-emerald-50/80 text-emerald-900' : 'border-amber-200 bg-amber-50/80 text-amber-900'}`}>
                    <p className="text-[11px] font-bold opacity-80">فرق المطابقة</p>
                    <p className="mt-1 text-base font-black">{shiftStatus.value}</p>
                  </div>
                </div>

                {todayClosure ? (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm font-semibold text-emerald-700">
                    تم إغلاق وردية اليوم بالفعل.
                  </div>
                ) : (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm font-semibold text-amber-800">
                    الوردية ما زالت مفتوحة. أدخل الرصيد الفعلي ثم نفّذ الإغلاق بعد المطابقة.
                  </div>
                )}

                <div className="grid gap-3 lg:grid-cols-3">
                  <label className="space-y-1">
                    <span className="form-label">رصيد البداية (د.ج)</span>
                    <input
                      type="number"
                      min={0}
                      step="0.1"
                      className="form-input ui-size-sm"
                      value={openingCash}
                      onChange={(event) => setOpeningCash(event.target.value)}
                    />
                  </label>

                  <label className="space-y-1">
                    <span className="form-label">النقد الفعلي (د.ج)</span>
                    <input
                      type="number"
                      min={0}
                      step="0.1"
                      className="form-input ui-size-sm"
                      value={actualCash}
                      onChange={(event) => setActualCash(event.target.value)}
                    />
                  </label>

                  <label className="space-y-1">
                    <span className="form-label">ملاحظة الإغلاق</span>
                    <input
                      className="form-input ui-size-sm"
                      value={closureNote}
                      onChange={(event) => setClosureNote(event.target.value)}
                      placeholder="اختياري"
                    />
                  </label>
                </div>

                {closureError ? <p className="text-sm font-semibold text-rose-700">{closureError}</p> : null}
                {createClosureMutation.isSuccess ? <p className="text-sm font-semibold text-emerald-700">تم تنفيذ الإغلاق بنجاح.</p> : null}

                <button
                  type="button"
                  className="btn-primary ui-size-sm w-full"
                  disabled={
                    createClosureMutation.isPending ||
                    !!todayClosure ||
                    !Number.isFinite(Number(openingCash)) ||
                    Number(openingCash) < 0 ||
                    !Number.isFinite(Number(actualCash)) ||
                    Number(actualCash) < 0
                  }
                  onClick={() => createClosureMutation.mutate()}
                >
                  {createClosureMutation.isPending ? 'جارٍ تنفيذ الإغلاق...' : 'إغلاق وردية اليوم'}
                </button>
              </div>
            </div>
          </section>

          <section className="admin-card p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">آخر القيود المحاسبية</h3>
                <p className="text-sm text-gray-600">عرض مختصر لآخر القيود بدون فرز أو تحكم داخل صفحة الملخص.</p>
              </div>
              <span className="rounded-full border border-gray-200 bg-white px-2 py-1 text-xs font-bold text-gray-600">
                {overviewEntryRows.length} قيد
              </span>
            </div>

            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">الوقت</th>
                    <th className="px-3 py-2 font-bold">النوع</th>
                    <th className="px-3 py-2 font-bold">الحساب</th>
                    <th className="px-3 py-2 font-bold">المبلغ</th>
                    <th className="px-3 py-2 font-bold">البيان</th>
                  </tr>
                </thead>
                <tbody>
                  {overviewEntryRows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100">
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.created_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                      <td className="px-3 py-2 font-semibold">{transactionTypeLabel[row.type] ?? translateSystemCode(row.type)}</td>
                      <td className="px-3 py-2">{renderAccountLabel(row.account_code)}</td>
                      <td className="px-3 py-2 font-black text-brand-700">{asMoney(row.amount)}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{renderFinancialNote(row.note, row.type)}</td>
                    </tr>
                  ))}
                  {overviewEntryRows.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-sm text-gray-500">
                        لا توجد قيود حديثة.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <section className="admin-card p-4">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">حركات الصندوق الأخيرة</h3>
                <p className="text-sm text-gray-600">متابعة آخر ما دخل وخرج من الصندوق أو الخزنة بدون أدوات تحكم إضافية.</p>
              </div>
              <div className="grid min-w-[220px] gap-2 sm:grid-cols-2">
                <CompactMetricCard title="داخل اليوم" value={asMoney(todaySummary.cashIn)} tone="success" />
                <CompactMetricCard title="خارج اليوم" value={asMoney(todaySummary.cashOut)} tone="warning" />
              </div>
            </div>

            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">الوقت</th>
                    <th className="px-3 py-2 font-bold">النوع</th>
                    <th className="px-3 py-2 font-bold">الاتجاه</th>
                    <th className="px-3 py-2 font-bold">القناة</th>
                    <th className="px-3 py-2 font-bold">المبلغ</th>
                  </tr>
                </thead>
                <tbody>
                  {overviewCashboxRows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100">
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.created_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                      <td className="px-3 py-2 font-semibold">{cashboxTypeLabel[row.type] ?? translateSystemCode(row.type)}</td>
                      <td className={`px-3 py-2 font-bold ${row.direction === 'in' ? 'text-emerald-700' : 'text-rose-700'}`}>
                        {cashboxDirectionLabel[row.direction] ?? translateSystemCode(row.direction)}
                      </td>
                      <td className="px-3 py-2">{cashChannelLabel[row.cash_channel] ?? translateSystemCode(row.cash_channel)}</td>
                      <td className="px-3 py-2 font-black text-brand-700">{asMoney(row.amount)}</td>
                    </tr>
                  ))}
                  {overviewCashboxRows.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-sm text-gray-500">
                        لا توجد حركات صندوق حديثة.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <section className="admin-card p-4">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">ملخص تسويات التوصيل</h3>
                <p className="text-sm text-gray-600">قراءة للتسويات المفتوحة وآخر الحركات بدون الدخول إلى شاشة الإدارة التفصيلية.</p>
              </div>
              <div className="grid min-w-[260px] gap-2 sm:grid-cols-2">
                <CompactMetricCard title="تسويات مفتوحة" value={`${settlementsSummary.openCount}`} tone="info" />
                <CompactMetricCard title="المتبقي للمطعم" value={asMoney(settlementsSummary.openStoreDue)} tone="primary" />
                <CompactMetricCard title="مستحق المندوب" value={asMoney(settlementsSummary.openDriverDue)} tone="warning" />
                <CompactMetricCard title="فروقات" value={`${settlementsSummary.varianceCount}`} tone="danger" />
              </div>
            </div>

            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">الطلب</th>
                    <th className="px-3 py-2 font-bold">الحالة</th>
                    <th className="px-3 py-2 font-bold">المطعم</th>
                    <th className="px-3 py-2 font-bold">المورد</th>
                    <th className="px-3 py-2 font-bold">الفرق</th>
                  </tr>
                </thead>
                <tbody>
                  {overviewSettlementRows.map((row) => (
                    <tr key={row.id} className={`border-t border-gray-100 table-row--${settlementRowTone(row.status)}`}>
                      <td className="px-3 py-2 font-semibold">{formatOrderTrackingId(row.order_id)}</td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-bold ${badgeToneForSettlement(row.status)}`}>
                          {settlementStatusLabel[row.status] ?? translateSystemCode(row.status)}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-bold text-brand-700">{asMoney(row.store_due_amount)}</td>
                      <td className="px-3 py-2 font-bold text-gray-900">{asMoney(row.remitted_amount)}</td>
                      <td className={`px-3 py-2 font-bold ${Math.abs(row.variance_amount) < 0.009 ? 'text-emerald-700' : 'text-amber-700'}`}>
                        {asMoney(row.variance_amount)}
                      </td>
                    </tr>
                  ))}
                  {overviewSettlementRows.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-sm text-gray-500">
                        لا توجد تسويات حديثة.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <section className="admin-card p-4">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">ملخص المصروفات التشغيلية</h3>
                <p className="text-sm text-gray-600">قراءة فقط للمصروفات لتفادي تكرار شاشة الإدارة والاعتماد داخل واجهة الملخص.</p>
              </div>
              <div className="grid min-w-[220px] gap-2 sm:grid-cols-2">
                <CompactMetricCard title="مصروفات اليوم" value={asMoney(todaySummary.operatingExpenses)} tone="danger" />
                <CompactMetricCard title="تكلفة المندوبين" value={asMoney(todaySummary.driverCost)} tone="warning" />
              </div>
            </div>

            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">الوقت</th>
                    <th className="px-3 py-2 font-bold">الحساب</th>
                    <th className="px-3 py-2 font-bold">المبلغ</th>
                    <th className="px-3 py-2 font-bold">البيان</th>
                  </tr>
                </thead>
                <tbody>
                  {overviewExpenseRows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100">
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.created_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                      <td className="px-3 py-2">{renderAccountLabel(row.account_code)}</td>
                      <td className="px-3 py-2 font-black text-rose-700">{asMoney(row.amount)}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{renderFinancialNote(row.note, row.type)}</td>
                    </tr>
                  ))}
                  {overviewExpenseRows.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-3 py-6 text-center text-sm text-gray-500">
                        لا توجد مصروفات تشغيلية حديثة.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <section className="admin-card p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">آخر إغلاقات الوردية</h3>
                <p className="text-sm text-gray-600">أرشيف مختصر للمراجعة السريعة بدون بحث أو أدوات تشغيل إضافية.</p>
              </div>
              <span className="rounded-full border border-gray-200 bg-white px-2 py-1 text-xs font-bold text-gray-600">
                {overviewClosureRows.length} إغلاق
              </span>
            </div>

            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">التاريخ</th>
                    <th className="px-3 py-2 font-bold">المتوقع</th>
                    <th className="px-3 py-2 font-bold">الفعلي</th>
                    <th className="px-3 py-2 font-bold">الفرق</th>
                    <th className="px-3 py-2 font-bold">وقت الإغلاق</th>
                  </tr>
                </thead>
                <tbody>
                  {overviewClosureRows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100">
                      <td className="px-3 py-2 font-semibold">{row.business_date}</td>
                      <td className="px-3 py-2 font-bold text-brand-700">{asMoney(row.expected_cash)}</td>
                      <td className="px-3 py-2 font-bold text-gray-900">{asMoney(row.actual_cash)}</td>
                      <td className={`px-3 py-2 font-bold ${Math.abs(row.variance) < 0.009 ? 'text-emerald-700' : 'text-rose-700'}`}>
                        {asMoney(row.variance)}
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.closed_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                    </tr>
                  ))}
                  {overviewClosureRows.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-sm text-gray-500">
                        لا توجد إغلاقات وردية مسجلة بعد.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      ) : null}

      {activeTab === 'cashbox' ? (
        <>
          <section className="admin-card p-4">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">راجع الحركات المسجلة</h3>
                <p className="text-sm text-gray-600">استخدم البحث والترتيب للوصول بسرعة إلى حركة الصندوق التي تريدها.</p>
              </div>
              <SectionBadge tone="success">ابدأ بالمراجعة</SectionBadge>
            </div>

            <div className="mt-3">
              <TableControls
                search={cashboxSearch}
                onSearchChange={(value) => {
                  setCashboxSearch(value);
                  setCashboxPage(1);
                }}
                sortBy={cashboxSortBy}
                onSortByChange={setCashboxSortBy}
                sortDirection={cashboxSortDirection}
                onSortDirectionChange={setCashboxSortDirection}
                sortOptions={[
                  { value: 'created_at', label: 'ترتيب: الوقت' },
                  { value: 'amount', label: 'ترتيب: المبلغ' },
                  { value: 'type', label: 'ترتيب: النوع' },
                  { value: 'order_id', label: 'ترتيب: الطلب' },
                ]}
                searchPlaceholder="ابحث عن حركة صندوق..."
              />
            </div>
          </section>

          <section className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-4 py-3 font-bold">الوقت</th>
                    <th className="px-4 py-3 font-bold">النوع</th>
                    <th className="px-4 py-3 font-bold">الاتجاه</th>
                    <th className="px-4 py-3 font-bold">القناة</th>
                    <th className="px-4 py-3 font-bold">المبلغ</th>
                    <th className="px-4 py-3 font-bold">الطلب</th>
                    <th className="px-4 py-3 font-bold">الملاحظة</th>
                  </tr>
                </thead>
                <tbody>
                  {cashboxView.rows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100">
                      <td data-label="الوقت" className="px-4 py-3 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.created_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                      <td data-label="النوع" className="px-4 py-3 font-semibold">
                        {cashboxTypeLabel[row.type] ?? translateSystemCode(row.type)}
                      </td>
                      <td
                        data-label="الاتجاه"
                        className={`px-4 py-3 font-bold ${row.direction === 'in' ? 'text-emerald-700' : 'text-rose-700'}`}
                      >
                        {cashboxDirectionLabel[row.direction] ?? translateSystemCode(row.direction)}
                      </td>
                      <td data-label="القناة" className="px-4 py-3">
                        {cashChannelLabel[row.cash_channel] ?? translateSystemCode(row.cash_channel)}
                      </td>
                      <td data-label="المبلغ" className="px-4 py-3 font-black text-brand-700">
                        {asMoney(row.amount)}
                      </td>
                      <td data-label="الطلب" className="px-4 py-3">
                        {row.order_id ? formatOrderTrackingId(row.order_id) : '-'}
                      </td>
                      <td data-label="الملاحظة" className="px-4 py-3 text-xs text-gray-500">
                        {sanitizeMojibakeText(row.note, 'حركة صندوق')}
                      </td>
                    </tr>
                  ))}
                  {cashboxView.rows.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد حركات صندوق.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <TablePagination page={cashboxView.page} totalPages={cashboxView.totalPages} totalRows={cashboxView.totalRows} onPageChange={setCashboxPage} />
          </section>
        </>
      ) : null}

      {activeTab === 'settlements' ? (
        <>
          <section className="admin-card p-4">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">راجع ما يحتاج توريدًا</h3>
                <p className="text-sm text-gray-600">ستجد هنا الحالات المفتوحة والفروقات وما تم توريده للمطعم.</p>
              </div>
              <SectionBadge tone="primary">تابع التحصيل</SectionBadge>
            </div>

            <div className="mt-3">
              <TableControls
                search={settlementSearch}
                onSearchChange={(value) => {
                  setSettlementSearch(value);
                  setSettlementPage(1);
                }}
                sortBy={settlementSortBy}
                onSortByChange={setSettlementSortBy}
                sortDirection={settlementSortDirection}
                onSortDirectionChange={setSettlementSortDirection}
                sortOptions={[
                  { value: 'recognized_at', label: 'ترتيب: وقت التسوية' },
                  { value: 'order_id', label: 'ترتيب: الطلب' },
                  { value: 'driver_due_amount', label: 'ترتيب: مستحق المندوب' },
                  { value: 'store_due_amount', label: 'ترتيب: مستحق المطعم' },
                  { value: 'variance_amount', label: 'ترتيب: الفرق' },
                ]}
                searchPlaceholder="ابحث عن تسوية توصيل..."
              />
            </div>
          </section>

          <section className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-4 py-3 font-bold">الطلب</th>
                    <th className="px-4 py-3 font-bold">المندوب</th>
                    <th className="px-4 py-3 font-bold">الحالة</th>
                    <th className="px-4 py-3 font-bold">المبلغ المحصل</th>
                    <th className="px-4 py-3 font-bold">مستحق المندوب</th>
                    <th className="px-4 py-3 font-bold">مستحق المطعم</th>
                    <th className="px-4 py-3 font-bold">المبلغ المورد</th>
                    <th className="px-4 py-3 font-bold">الفرق</th>
                    <th className="px-4 py-3 font-bold">وقت التسوية</th>
                  </tr>
                </thead>
                <tbody>
                  {settlementsView.rows.map((row) => (
                    <tr key={row.id} className={`border-t border-gray-100 table-row--${settlementRowTone(row.status)}`}>
                      <td data-label="الطلب" className="px-4 py-3 font-semibold">
                        {formatOrderTrackingId(row.order_id)}
                      </td>
                      <td data-label="المندوب" className="px-4 py-3">
                        <div className="font-semibold text-gray-900">مندوب #{row.driver_id}</div>
                        <div className="text-xs text-gray-500">
                          {row.driver_share_model === 'percentage'
                            ? `نسبة ${row.driver_share_value.toFixed(2)}%`
                            : row.driver_share_model === 'fixed_amount'
                            ? `مبلغ ثابت ${asMoney(row.driver_share_value)}`
                            : 'كامل رسم التوصيل'}
                        </div>
                      </td>
                      <td data-label="الحالة" className="px-4 py-3">
                        <span className={`${TABLE_STATUS_CHIP_BASE} ${badgeToneForSettlement(row.status)}`}>
                          {settlementStatusLabel[row.status] ?? translateSystemCode(row.status)}
                        </span>
                      </td>
                      <td data-label="المبلغ المحصل" className="px-4 py-3 font-bold text-emerald-700">
                        {asMoney(row.actual_collected_amount)}
                      </td>
                      <td data-label="مستحق المندوب" className="px-4 py-3 font-bold text-amber-700">
                        {asMoney(row.driver_due_amount)}
                      </td>
                      <td data-label="مستحق المطعم" className="px-4 py-3 font-bold text-brand-700">
                        {asMoney(row.store_due_amount)}
                      </td>
                      <td data-label="المبلغ المورد" className="px-4 py-3">
                        {asMoney(row.remitted_amount)}
                      </td>
                      <td
                        data-label="الفرق"
                        className={`px-4 py-3 font-bold ${Math.abs(row.variance_amount) < 0.009 ? 'text-emerald-700' : 'text-rose-700'}`}
                      >
                        {asMoney(row.variance_amount)}
                      </td>
                      <td data-label="وقت التسوية" className="px-4 py-3 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.recognized_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                    </tr>
                  ))}
                  {settlementsView.rows.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد تسويات توصيل.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <TablePagination
              page={settlementsView.page}
              totalPages={settlementsView.totalPages}
              totalRows={settlementsView.totalRows}
              onPageChange={setSettlementPage}
            />
          </section>
        </>
      ) : null}

      {activeTab === 'entries' ? (
        <>
          <section className="admin-card p-4">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">راجع القيد الذي تبحث عنه</h3>
                <p className="text-sm text-gray-600">يمكنك الوصول بسرعة إلى القيد المطلوب حسب الوقت أو الطلب أو نوع الحركة.</p>
              </div>
              <SectionBadge tone="info">سجل مرجعي</SectionBadge>
            </div>

            <div className="mt-3">
              <TableControls
                search={entrySearch}
                onSearchChange={(value) => {
                  setEntrySearch(value);
                  setEntryPage(1);
                }}
                sortBy={entrySortBy}
                onSortByChange={setEntrySortBy}
                sortDirection={entrySortDirection}
                onSortDirectionChange={setEntrySortDirection}
                sortOptions={[
                  { value: 'created_at', label: 'ترتيب: الوقت' },
                  { value: 'amount', label: 'ترتيب: المبلغ' },
                  { value: 'type', label: 'ترتيب: نوع القيد' },
                  { value: 'order_id', label: 'ترتيب: الطلب' },
                ]}
                searchPlaceholder="ابحث عن قيد محاسبي..."
              />
            </div>
          </section>

          <section className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-4 py-3 font-bold">الوقت</th>
                    <th className="px-4 py-3 font-bold">نوع القيد</th>
                    <th className="px-4 py-3 font-bold">مدين / دائن</th>
                    <th className="px-4 py-3 font-bold">الحساب</th>
                    <th className="px-4 py-3 font-bold">المبلغ</th>
                    <th className="px-4 py-3 font-bold">الطلب</th>
                    <th className="px-4 py-3 font-bold">المرجع</th>
                    <th className="px-4 py-3 font-bold">الملاحظة</th>
                  </tr>
                </thead>
                <tbody>
                  {entriesView.rows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100">
                      <td data-label="الوقت" className="px-4 py-3 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.created_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                      <td data-label="نوع القيد" className="px-4 py-3 font-semibold">
                        {transactionTypeLabel[row.type] ?? translateSystemCode(row.type)}
                      </td>
                      <td data-label="مدين / دائن" className="px-4 py-3">
                        {row.direction ? (row.direction === 'debit' ? 'مدين' : 'دائن') : '-'}
                      </td>
                      <td data-label="الحساب" className="px-4 py-3">
                        {renderAccountLabel(row.account_code)}
                      </td>
                      <td data-label="المبلغ" className="px-4 py-3 font-black text-brand-700">
                        {asMoney(row.amount)}
                      </td>
                      <td data-label="الطلب" className="px-4 py-3">
                        {row.order_id ? formatOrderTrackingId(row.order_id) : '-'}
                      </td>
                      <td data-label="المرجع" className="px-4 py-3 text-xs text-gray-500">
                        {renderReferenceLabel(row.reference_group, row.order_id)}
                      </td>
                      <td data-label="الملاحظة" className="px-4 py-3 text-xs text-gray-500">
                        {renderFinancialNote(row.note, row.type)}
                      </td>
                    </tr>
                  ))}
                  {entriesView.rows.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد قيود محاسبية.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <TablePagination page={entriesView.page} totalPages={entriesView.totalPages} totalRows={entriesView.totalRows} onPageChange={setEntryPage} />
          </section>
        </>
      ) : null}

      {activeTab === 'closures' ? (
        <>
          <section className="admin-card p-4">
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">راجع الإغلاقات السابقة</h3>
                <p className="text-sm text-gray-600">هذا الجدول مخصص لك لمراجعة المطابقة والرصيد الفعلي لكل وردية مغلقة.</p>
              </div>
              <SectionBadge tone="warning">أرشيف المراجعة</SectionBadge>
            </div>

            <div className="mt-3">
              <TableControls
                search={closureSearch}
                onSearchChange={(value) => {
                  setClosureSearch(value);
                  setClosurePage(1);
                }}
                sortBy={closureSortBy}
                onSortByChange={setClosureSortBy}
                sortDirection={closureSortDirection}
                onSortDirectionChange={setClosureSortDirection}
                sortOptions={[
                  { value: 'closed_at', label: 'ترتيب: وقت الإغلاق' },
                  { value: 'expected_cash', label: 'ترتيب: الرصيد المتوقع' },
                  { value: 'actual_cash', label: 'ترتيب: الرصيد الفعلي' },
                  { value: 'variance', label: 'ترتيب: الفرق' },
                ]}
                searchPlaceholder="ابحث في الإغلاقات السابقة..."
              />
            </div>
          </section>

          <section className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-4 py-3 font-bold">التاريخ</th>
                    <th className="px-4 py-3 font-bold">بداية الوردية</th>
                    <th className="px-4 py-3 font-bold">المبيعات</th>
                    <th className="px-4 py-3 font-bold">المرتجعات</th>
                    <th className="px-4 py-3 font-bold">المصروفات</th>
                    <th className="px-4 py-3 font-bold">الرصيد المتوقع</th>
                    <th className="px-4 py-3 font-bold">الرصيد الفعلي</th>
                    <th className="px-4 py-3 font-bold">الفرق</th>
                    <th className="px-4 py-3 font-bold">بواسطة</th>
                    <th className="px-4 py-3 font-bold">وقت الإغلاق</th>
                  </tr>
                </thead>
                <tbody>
                  {closuresView.rows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100">
                      <td data-label="التاريخ" className="px-4 py-3 font-semibold">
                        {row.business_date}
                      </td>
                      <td data-label="بداية الوردية" className="px-4 py-3">
                        {asMoney(row.opening_cash)}
                      </td>
                      <td data-label="المبيعات" className="px-4 py-3 font-bold text-emerald-700">
                        {asMoney(row.sales_total)}
                      </td>
                      <td data-label="المرتجعات" className="px-4 py-3 font-bold text-amber-700">
                        {asMoney(row.refunds_total)}
                      </td>
                      <td data-label="المصروفات" className="px-4 py-3 font-bold text-rose-700">
                        {asMoney(row.expenses_total)}
                      </td>
                      <td data-label="الرصيد المتوقع" className="px-4 py-3 font-bold text-brand-700">
                        {asMoney(row.expected_cash)}
                      </td>
                      <td data-label="الرصيد الفعلي" className="px-4 py-3 font-bold text-gray-900">
                        {asMoney(row.actual_cash)}
                      </td>
                      <td
                        data-label="الفرق"
                        className={`px-4 py-3 font-bold ${Math.abs(row.variance) < 0.009 ? 'text-emerald-700' : 'text-amber-700'}`}
                      >
                        {asMoney(row.variance)}
                      </td>
                      <td data-label="بواسطة" className="px-4 py-3">
                        {row.closed_by}
                      </td>
                      <td data-label="وقت الإغلاق" className="px-4 py-3 text-xs text-gray-500">
                        {new Date(parseApiDateMs(row.closed_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                    </tr>
                  ))}
                  {closuresView.rows.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد إغلاقات وردية مسجلة بعد.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            <TablePagination
              page={closuresView.page}
              totalPages={closuresView.totalPages}
              totalRows={closuresView.totalRows}
              onPageChange={setClosurePage}
            />
          </section>
        </>
      ) : null}
    </div>
  );
}



