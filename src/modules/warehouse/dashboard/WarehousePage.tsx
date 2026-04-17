import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/modules/auth/store';
import { WarehouseSuppliersSection } from '@/modules/warehouse/suppliers/SuppliersPage';
import { api } from '@/shared/api/client';
import type { WarehouseItem } from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';
import { parseApiDateMs } from '@/shared/utils/date';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';

type InboundLine = { item_id: number; quantity: number; unit_cost: number };
type OutboundLine = { item_id: number; quantity: number };
type CountLine = { item_id: number; counted_quantity: number };
type ItemForm = { name: string; unit: string; alert_threshold: number; active: boolean };
export type WarehousePageView =
  | 'overview'
  | 'supply'
  | 'items'
  | 'stock'
  | 'counts'
  | 'suppliers'
  | 'balances'
  | 'inbound'
  | 'outbound'
  | 'ledger';

const emptyInboundLine: InboundLine = { item_id: 0, quantity: 1, unit_cost: 0 };
const emptyOutboundLine: OutboundLine = { item_id: 0, quantity: 1 };
const emptyCountLine: CountLine = { item_id: 0, counted_quantity: 0 };
const emptyItemForm: ItemForm = { name: '', unit: '', alert_threshold: 0, active: true };

function resolveStockCountRowTone(status: string): 'success' | 'warning' | 'danger' {
  if (status === 'settled') return 'success';
  if (status === 'pending') return 'warning';
  return 'danger';
}

function resolveWarehouseItemRowTone(active: boolean): 'success' | 'warning' | 'danger' {
  return active ? 'success' : 'danger';
}

export function WarehousePage({ initialView = 'overview' }: { initialView?: WarehousePageView }) {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();
  const [pageError, setPageError] = useState('');

  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [itemForm, setItemForm] = useState<ItemForm>({ ...emptyItemForm });

  const [inboundModalOpen, setInboundModalOpen] = useState(false);
  const [inboundSupplierId, setInboundSupplierId] = useState<number | ''>('');
  const [inboundReference, setInboundReference] = useState('');
  const [inboundNote, setInboundNote] = useState('');
  const [inboundLines, setInboundLines] = useState<InboundLine[]>([{ ...emptyInboundLine }]);

  const [outboundModalOpen, setOutboundModalOpen] = useState(false);
  const [outboundReasonCode, setOutboundReasonCode] = useState('');
  const [outboundReasonNote, setOutboundReasonNote] = useState('');
  const [outboundNote, setOutboundNote] = useState('');
  const [outboundLines, setOutboundLines] = useState<OutboundLine[]>([{ ...emptyOutboundLine }]);

  const [countModalOpen, setCountModalOpen] = useState(false);
  const [countNote, setCountNote] = useState('');
  const [countLines, setCountLines] = useState<CountLine[]>([{ ...emptyCountLine }]);
  const [settlingCountId, setSettlingCountId] = useState<number | null>(null);

  const [balanceOnlyLow, setBalanceOnlyLow] = useState(false);
  const [ledgerItemId, setLedgerItemId] = useState<number | ''>('');
  const [ledgerMovement, setLedgerMovement] = useState<'' | 'inbound' | 'outbound'>('');
  const [ledgerLimit, setLedgerLimit] = useState(200);

  const invalidateWarehouse = () => {
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-suppliers'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-items'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-balances'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-ledger'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-inbound'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-outbound'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-stock-counts'] });
  };

  const dashboardQuery = useQuery({
    queryKey: ['manager-warehouse-dashboard'],
    queryFn: () => api.managerWarehouseDashboard(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });
  const suppliersQuery = useQuery({
    queryKey: ['manager-warehouse-suppliers'],
    queryFn: () => api.managerWarehouseSuppliers(role ?? 'manager'),
    enabled: role === 'manager',
  });
  const itemsQuery = useQuery({
    queryKey: ['manager-warehouse-items'],
    queryFn: () => api.managerWarehouseItems(role ?? 'manager'),
    enabled: role === 'manager',
  });
  const balancesQuery = useQuery({
    queryKey: ['manager-warehouse-balances', balanceOnlyLow],
    queryFn: () => api.managerWarehouseBalances(role ?? 'manager', balanceOnlyLow),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(4000),
  });
  const ledgerQuery = useQuery({
    queryKey: ['manager-warehouse-ledger', ledgerLimit, ledgerItemId, ledgerMovement],
    queryFn: () =>
      api.managerWarehouseLedger(role ?? 'manager', {
        limit: ledgerLimit,
        itemId: ledgerItemId || undefined,
        movementKind: ledgerMovement || undefined,
      }),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(4000),
  });
  const inboundQuery = useQuery({
    queryKey: ['manager-warehouse-inbound'],
    queryFn: () => api.managerWarehouseInboundVouchers(role ?? 'manager', 100),
    enabled: role === 'manager',
  });
  const outboundQuery = useQuery({
    queryKey: ['manager-warehouse-outbound'],
    queryFn: () => api.managerWarehouseOutboundVouchers(role ?? 'manager', 100),
    enabled: role === 'manager',
  });
  const outboundReasonsQuery = useQuery({
    queryKey: ['manager-warehouse-outbound-reasons'],
    queryFn: () => api.managerWarehouseOutboundReasons(role ?? 'manager'),
    enabled: role === 'manager',
  });
  const stockCountsQuery = useQuery({
    queryKey: ['manager-warehouse-stock-counts'],
    queryFn: () => api.managerWarehouseStockCounts(role ?? 'manager', 100),
    enabled: role === 'manager',
  });

  const suppliers = suppliersQuery.data ?? [];
  const items = itemsQuery.data ?? [];
  const balances = balancesQuery.data ?? [];
  const ledgerRows = ledgerQuery.data ?? [];
  const inboundRows = inboundQuery.data ?? [];
  const outboundRows = outboundQuery.data ?? [];
  const outboundReasons = outboundReasonsQuery.data ?? [];
  const stockCounts = stockCountsQuery.data ?? [];
  const dashboard = dashboardQuery.data;

  const activeSuppliers = useMemo(() => suppliers.filter((supplier) => supplier.active), [suppliers]);
  const activeItems = useMemo(() => items.filter((item) => item.active), [items]);
  const inboundEligibleSuppliers = useMemo(
    () => activeSuppliers.filter((supplier) => supplier.supplied_item_ids.length > 0),
    [activeSuppliers]
  );
  const inboundSupplierItemIds = useMemo(() => {
    if (!inboundSupplierId) return new Set<number>();
    const selectedSupplier = suppliers.find((supplier) => supplier.id === Number(inboundSupplierId));
    return new Set<number>(selectedSupplier?.supplied_item_ids ?? []);
  }, [inboundSupplierId, suppliers]);
  const inboundAvailableItems = useMemo(
    () => activeItems.filter((item) => inboundSupplierItemIds.has(item.id)),
    [activeItems, inboundSupplierItemIds]
  );
  const kitchenOutboundReasons = useMemo(
    () => outboundReasons.filter((reason) => reason.code === 'kitchen_supply' || reason.code === 'operational_use'),
    [outboundReasons]
  );
  const pendingCounts = useMemo(() => stockCounts.filter((row) => row.status === 'pending').length, [stockCounts]);
  const outboundEligibleItemIds = useMemo(
    () => new Set<number>(balances.filter((row) => row.quantity > 0).map((row) => Number(row.item_id))),
    [balances]
  );
  const outboundAvailableItems = useMemo(
    () => activeItems.filter((item) => outboundEligibleItemIds.has(item.id)),
    [activeItems, outboundEligibleItemIds]
  );
  const balanceByItemId = useMemo(() => {
    const map = new Map<number, number>();
    balances.forEach((row) => map.set(Number(row.item_id), Number(row.quantity)));
    return map;
  }, [balances]);
  const itemCostHintById = useMemo(() => {
    const map = new Map<number, number>();
    inboundRows.forEach((voucher) => {
      voucher.items.forEach((line) => {
        if (!map.has(line.item_id) && Number.isFinite(line.unit_cost) && line.unit_cost >= 0) {
          map.set(line.item_id, Number(line.unit_cost));
        }
      });
    });
    outboundRows.forEach((voucher) => {
      voucher.items.forEach((line) => {
        if (!map.has(line.item_id) && Number.isFinite(line.unit_cost) && line.unit_cost >= 0) {
          map.set(line.item_id, Number(line.unit_cost));
        }
      });
    });
    ledgerRows.forEach((row) => {
      if (!map.has(row.item_id) && Number.isFinite(row.running_avg_cost) && row.running_avg_cost >= 0) {
        map.set(row.item_id, Number(row.running_avg_cost));
      }
    });
    return map;
  }, [inboundRows, outboundRows, ledgerRows]);

  useEffect(() => {
    if (!outboundReasonCode && kitchenOutboundReasons.length > 0) {
      setOutboundReasonCode(kitchenOutboundReasons[0].code);
    }
  }, [kitchenOutboundReasons, outboundReasonCode]);

  useEffect(() => {
    setInboundLines((prev) => prev.map((line) => (inboundSupplierItemIds.has(line.item_id) ? line : { ...line, item_id: 0 })));
  }, [inboundSupplierItemIds]);

  useEffect(() => {
    setOutboundLines((prev) => prev.map((line) => (outboundEligibleItemIds.has(line.item_id) ? line : { ...line, item_id: 0 })));
  }, [outboundEligibleItemIds]);

  const saveItemMutation = useMutation({
    mutationFn: () => {
      const payload = {
        name: itemForm.name.trim(),
        unit: itemForm.unit.trim(),
        alert_threshold: Number(itemForm.alert_threshold),
        active: itemForm.active,
      };
      if (editingItemId) return api.managerUpdateWarehouseItem(role ?? 'manager', editingItemId, payload);
      return api.managerCreateWarehouseItem(role ?? 'manager', payload);
    },
    onSuccess: () => {
      invalidateWarehouse();
      setPageError('');
      setItemModalOpen(false);
      setEditingItemId(null);
      setItemForm({ ...emptyItemForm });
    },
    onError: (error) => setPageError(error instanceof Error ? error.message : 'تعذر حفظ الصنف المخزني.'),
  });

  const createInboundMutation = useMutation({
    mutationFn: () =>
      api.managerCreateWarehouseInboundVoucher(role ?? 'manager', {
        supplier_id: Number(inboundSupplierId),
        reference_no: inboundReference.trim() || null,
        note: inboundNote.trim() || null,
        idempotency_key: `in-${Date.now()}`,
        items: inboundLines.map((line) => ({ item_id: Number(line.item_id), quantity: Number(line.quantity), unit_cost: Number(line.unit_cost) })),
      }),
    onSuccess: () => {
      invalidateWarehouse();
      setPageError('');
      setInboundModalOpen(false);
      setInboundSupplierId('');
      setInboundReference('');
      setInboundNote('');
      setInboundLines([{ ...emptyInboundLine }]);
    },
    onError: (error) => setPageError(error instanceof Error ? error.message : 'تعذر ترحيل سند الإدخال.'),
  });

  const createOutboundMutation = useMutation({
    mutationFn: () =>
      api.managerCreateWarehouseOutboundVoucher(role ?? 'manager', {
        reason_code: outboundReasonCode,
        reason_note: outboundReasonNote.trim() || null,
        note: outboundNote.trim() || null,
        idempotency_key: `out-${Date.now()}`,
        items: outboundLines.map((line) => ({ item_id: Number(line.item_id), quantity: Number(line.quantity) })),
      }),
    onSuccess: () => {
      invalidateWarehouse();
      setPageError('');
      setOutboundModalOpen(false);
      setOutboundReasonNote('');
      setOutboundNote('');
      setOutboundLines([{ ...emptyOutboundLine }]);
    },
    onError: (error) => setPageError(error instanceof Error ? error.message : 'تعذر ترحيل سند الصرف.'),
  });

  const createCountMutation = useMutation({
    mutationFn: () =>
      api.managerCreateWarehouseStockCount(role ?? 'manager', {
        note: countNote.trim() || null,
        idempotency_key: `cnt-${Date.now()}`,
        items: countLines.map((line) => ({ item_id: Number(line.item_id), counted_quantity: Number(line.counted_quantity) })),
      }),
    onSuccess: () => {
      invalidateWarehouse();
      setPageError('');
      setCountModalOpen(false);
      setCountNote('');
      setCountLines([{ ...emptyCountLine }]);
    },
    onError: (error) => setPageError(error instanceof Error ? error.message : 'تعذر حفظ مستند الجرد.'),
  });

  const settleCountMutation = useMutation({
    mutationFn: (countId: number) => api.managerSettleWarehouseStockCount(role ?? 'manager', countId),
    onMutate: (countId) => setSettlingCountId(countId),
    onSuccess: () => {
      invalidateWarehouse();
      setPageError('');
    },
    onError: (error) => setPageError(error instanceof Error ? error.message : 'تعذرت تسوية فروقات الجرد.'),
    onSettled: () => setSettlingCountId(null),
  });

  const openCreateItemModal = () => {
    setPageError('');
    setEditingItemId(null);
    setItemForm({ ...emptyItemForm });
    setItemModalOpen(true);
  };

  const openEditItemModal = (item: WarehouseItem) => {
    setPageError('');
    setEditingItemId(item.id);
    setItemForm({ name: item.name, unit: item.unit, alert_threshold: item.alert_threshold, active: item.active });
    setItemModalOpen(true);
  };

  const submitItem = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (itemForm.name.trim().length < 2) return setPageError('اسم الصنف يجب أن يكون حرفين على الأقل.');
    if (itemForm.unit.trim().length < 1) return setPageError('وحدة الصنف مطلوبة.');
    if (itemForm.alert_threshold < 0) return setPageError('حد التنبيه لا يمكن أن يكون سالبًا.');
    saveItemMutation.mutate();
  };

  const submitInbound = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inboundSupplierId) return setPageError('اختر المورد أولًا.');
    if (inboundAvailableItems.length === 0) return setPageError('المورد المختار لا يملك أصنافًا معتمدة للتوريد.');
    if (inboundLines.some((line) => !line.item_id || line.quantity <= 0 || line.unit_cost < 0)) return setPageError('تحقق من بيانات سند الإدخال.');
    if (inboundLines.some((line) => !inboundSupplierItemIds.has(line.item_id))) return setPageError('أحد الأصناف المختارة غير مرتبط بالمورد الحالي.');
    createInboundMutation.mutate();
  };

  const submitOutbound = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!outboundReasonCode) return setPageError('اختر سبب الصرف.');
    if (outboundAvailableItems.length === 0) return setPageError('لا توجد أصناف متاحة للصرف حاليًا.');
    if (outboundLines.some((line) => !line.item_id || line.quantity <= 0)) return setPageError('تحقق من بيانات سند الصرف.');
    if (outboundLines.some((line) => !outboundEligibleItemIds.has(line.item_id))) return setPageError('أحد الأصناف المختارة غير متاح للصرف (لا يوجد رصيد فعلي).');
    createOutboundMutation.mutate();
  };

  const submitCount = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (countLines.some((line) => !line.item_id || line.counted_quantity < 0)) return setPageError('تحقق من بيانات الجرد الفعلي.');
    createCountMutation.mutate();
  };

  const updateInboundLineItem = (index: number, itemId: number) => {
    setInboundLines((prev) =>
      prev.map((line, i) => {
        if (i !== index) return line;
        const hintedCost = itemId ? itemCostHintById.get(itemId) ?? line.unit_cost : 0;
        return {
          ...line,
          item_id: itemId,
          quantity: line.quantity > 0 ? line.quantity : 1,
          unit_cost: hintedCost,
        };
      })
    );
  };

  const updateOutboundLineItem = (index: number, itemId: number) => {
    setOutboundLines((prev) =>
      prev.map((line, i) => {
        if (i !== index) return line;
        const availableQty = balanceByItemId.get(itemId) ?? 0;
        const safeQuantity = availableQty > 0 ? Math.min(Math.max(line.quantity, 1), availableQty) : 1;
        return { ...line, item_id: itemId, quantity: safeQuantity };
      })
    );
  };

  const updateCountLineItem = (index: number, itemId: number) => {
    setCountLines((prev) =>
      prev.map((line, i) => {
        if (i !== index) return line;
        const systemQty = itemId ? balanceByItemId.get(itemId) ?? 0 : 0;
        return { ...line, item_id: itemId, counted_quantity: systemQty };
      })
    );
  };

  const isLoading =
    dashboardQuery.isLoading ||
    suppliersQuery.isLoading ||
    itemsQuery.isLoading ||
    balancesQuery.isLoading ||
    ledgerQuery.isLoading ||
    inboundQuery.isLoading ||
    outboundQuery.isLoading ||
    outboundReasonsQuery.isLoading ||
    stockCountsQuery.isLoading;
  const hasError =
    dashboardQuery.isError ||
    suppliersQuery.isError ||
    itemsQuery.isError ||
    balancesQuery.isError ||
    ledgerQuery.isError ||
    inboundQuery.isError ||
    outboundQuery.isError ||
    outboundReasonsQuery.isError ||
    stockCountsQuery.isError;

  const showOverview = initialView === 'overview';
  const showSupply = initialView === 'supply' || initialView === 'suppliers' || initialView === 'inbound';
  const showItems = initialView === 'items' || initialView === 'ledger';
  const showStock = initialView === 'stock' || initialView === 'balances' || initialView === 'outbound';
  const showCounts = initialView === 'counts';
  const lowStockCount = dashboard?.low_stock_items ?? 0;
  const inboundToday = (dashboard?.inbound_today ?? 0).toFixed(2);
  const outboundToday = (dashboard?.outbound_today ?? 0).toFixed(2);
  const activeSuppliersCount = activeSuppliers.length;
  const activeItemsCount = activeItems.length;
  const settledCounts = stockCounts.filter((row) => row.status === 'settled').length;

  if (isLoading) return <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">جارٍ تحميل بيانات المخزن...</div>;
  if (hasError) return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">تعذر تحميل قسم إدارة المخزن.</div>;

  return (
    <div className="admin-page space-y-4">
      {showOverview ? (
        <section className="admin-card space-y-4 p-4">
          <div className="space-y-2">
            <h2 className="text-lg font-black text-[var(--text-primary)]">كيف يسير المستودع اليوم؟</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              هذه القراءة السريعة تساعدك على معرفة ما يحتاج متابعة قبل الدخول إلى الصفحة المناسبة من الشريط الثانوي.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <article className="rounded-2xl border border-rose-300 bg-rose-50 p-4">
              <p className="text-xs font-bold text-rose-700">أصناف تحتاج متابعة</p>
              <p className="mt-1 text-2xl font-black text-rose-900">{lowStockCount}</p>
            </article>
            <article className="rounded-2xl border border-amber-300 bg-amber-50 p-4">
              <p className="text-xs font-bold text-amber-700">جرد بانتظار التسوية</p>
              <p className="mt-1 text-2xl font-black text-amber-900">{pendingCounts}</p>
            </article>
            <article className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4">
              <p className="text-xs font-bold text-emerald-700">تم استلامه اليوم</p>
              <p className="mt-1 text-2xl font-black text-emerald-900">{inboundToday}</p>
            </article>
            <article className="rounded-2xl border border-sky-300 bg-sky-50 p-4">
              <p className="text-xs font-bold text-sky-700">تم صرفه اليوم</p>
              <p className="mt-1 text-2xl font-black text-sky-900">{outboundToday}</p>
            </article>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <h3 className="text-sm font-black text-[var(--text-primary)]">من أين تبدأ؟</h3>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                ابدأ بإضافة المورد، ثم عرّف الصنف، وبعدها سجّل الاستلام أو الصرف أو الجرد حسب ما تحتاجه اليوم.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <h3 className="text-sm font-black text-[var(--text-primary)]">قراءة سريعة للمستودع</h3>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                  الموردون النشطون: <span className="font-black text-[var(--text-primary)]">{activeSuppliersCount}</span>
                </div>
                <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                  الأصناف النشطة: <span className="font-black text-[var(--text-primary)]">{activeItemsCount}</span>
                </div>
                <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                  الجرد الذي تمّت تسويته: <span className="font-black text-[var(--text-primary)]">{settledCounts}</span>
                </div>
                <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                  الحركة التي تحتاج متابعة الآن:{' '}
                  <span className="font-black text-[var(--text-primary)]">
                    {pendingCounts > 0 ? 'الجرد' : lowStockCount > 0 ? 'الأرصدة' : 'لا توجد متابعة عاجلة'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : null}
      {pageError ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{pageError}</div> : null}

      {showSupply ? (
        <section className="space-y-4">
          <section className="admin-card space-y-3 p-4">
            <div className="space-y-1">
              <h2 className="text-lg font-black text-[var(--text-primary)]">التوريد</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                من هنا تدير الموردين الذين تعتمد عليهم، ثم تسجل ما دخل إلى المستودع منهم في نفس السياق.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-3 text-sm text-[var(--text-secondary)]">
                الموردون النشطون: <span className="font-black text-[var(--text-primary)]">{activeSuppliersCount}</span>
              </div>
              <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-3 text-sm text-[var(--text-secondary)]">
                موردون جاهزون للتوريد: <span className="font-black text-[var(--text-primary)]">{inboundEligibleSuppliers.length}</span>
              </div>
              <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-3 text-sm text-[var(--text-secondary)]">
                استلام اليوم: <span className="font-black text-[var(--text-primary)]">{inboundToday}</span>
              </div>
            </div>
          </section>

          <section className="admin-card p-4">
            <WarehouseSuppliersSection embedded />
          </section>
        </section>
      ) : null}

      {showItems ? (
        <section id="warehouse-items" className="admin-card space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-black text-[var(--text-primary)]">عرّف الأصناف التي تخزنها</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                أضف الصنف مرة واحدة، ثم استخدمه لاحقًا في الاستلام والصرف والجرد بدون إعادة إدخاله كل مرة.
              </p>
            </div>
            <button
              type="button"
              className="btn-primary"
              onClick={openCreateItemModal}
              disabled={activeSuppliers.length === 0}
              title={activeSuppliers.length === 0 ? 'أضف موردًا نشطًا أولًا' : 'إضافة صنف'}
            >
              إضافة صنف
            </button>
          </div>
          {activeSuppliers.length === 0 ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              أضف موردًا نشطًا أولًا، وبعدها يمكنك إنشاء الأصناف التي ستتابعها داخل المستودع.
            </div>
          ) : null}
          <div className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">الصنف</th>
                    <th className="px-3 py-2 font-bold">الوحدة</th>
                    <th className="px-3 py-2 font-bold">حد التنبيه</th>
                    <th className="px-3 py-2 font-bold">الحالة</th>
                    <th className="px-3 py-2 font-bold">آخر تحديث</th>
                    <th className="px-3 py-2 font-bold">الإجراء</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className={`table-row--${resolveWarehouseItemRowTone(item.active)}`}>
                      <td data-label="الصنف" className="px-3 py-2 font-bold">{item.name}</td>
                      <td data-label="الوحدة" className="px-3 py-2">{item.unit}</td>
                      <td data-label="حد التنبيه" className="px-3 py-2">{item.alert_threshold.toFixed(3)}</td>
                      <td data-label="الحالة" className="px-3 py-2">{item.active ? 'نشط' : 'موقوف'}</td>
                      <td data-label="آخر تحديث" className="px-3 py-2 text-xs">
                        {new Date(parseApiDateMs(item.updated_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                      <td data-label="الإجراء" className="px-3 py-2">
                        <button type="button" className="btn-secondary ui-size-sm" onClick={() => openEditItemModal(item)}>
                          تعديل
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد أصناف في المستودع حتى الآن.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {showStock ? (
        <section className="admin-card space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-black text-[var(--text-primary)]">راجع الرصيد الحالي لكل صنف</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                هذه الصفحة تجمع بين الرصيد الحالي والحركة الخارجة من المستودع حتى ترى ما تملك وما تم صرفه في نفس المكان.
              </p>
            </div>
            <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-secondary)]">
              <input type="checkbox" checked={balanceOnlyLow} onChange={(e) => setBalanceOnlyLow(e.target.checked)} />
              اعرض ما يحتاج متابعة فقط
            </label>
          </div>
          <div className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">الصنف</th>
                    <th className="px-3 py-2 font-bold">الرصيد الحالي</th>
                    <th className="px-3 py-2 font-bold">الوحدة</th>
                    <th className="px-3 py-2 font-bold">حد التنبيه</th>
                  </tr>
                </thead>
                <tbody>
                  {balances.map((row) => (
                    <tr key={row.item_id}>
                      <td data-label="الصنف" className="px-3 py-2 font-bold">{row.item_name}</td>
                      <td data-label="الرصيد الحالي" className="px-3 py-2">{row.quantity.toFixed(3)}</td>
                      <td data-label="الوحدة" className="px-3 py-2">{row.unit}</td>
                      <td data-label="حد التنبيه" className="px-3 py-2">{row.alert_threshold.toFixed(3)}</td>
                    </tr>
                  ))}
                  {balances.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد أرصدة مطابقة للفلتر الحالي.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {showSupply ? (
        <section className="admin-card space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-black text-[var(--text-primary)]">سجّل ما تم استلامه</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                كل استلام جديد من الموردين يسجل هنا مع الكمية والتكلفة الفعلية لكل صنف.
              </p>
            </div>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setInboundModalOpen(true)}
              disabled={inboundEligibleSuppliers.length === 0 || activeItems.length === 0}
            >
              تسجيل استلام
            </button>
          </div>
          <div className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">رقم المستند</th>
                    <th className="px-3 py-2 font-bold">المورد</th>
                    <th className="px-3 py-2 font-bold">الكمية</th>
                    <th className="px-3 py-2 font-bold">التكلفة</th>
                  </tr>
                </thead>
                <tbody>
                  {inboundRows.slice(0, 10).map((row) => (
                    <tr key={row.id}>
                      <td data-label="رقم المستند" className="px-3 py-2 font-bold">{row.voucher_no}</td>
                      <td data-label="المورد" className="px-3 py-2">{row.supplier_name}</td>
                      <td data-label="الكمية" className="px-3 py-2">{row.total_quantity.toFixed(3)}</td>
                      <td data-label="التكلفة" className="px-3 py-2">{row.total_cost.toFixed(2)} د.ج</td>
                    </tr>
                  ))}
                  {inboundRows.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد عمليات استلام مسجلة حتى الآن.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {showStock ? (
        <section className="admin-card space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-black text-[var(--text-primary)]">سجّل ما خرج من المستودع</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                استخدم هذا القسم عند صرف الأصناف إلى المطبخ أو إلى أي استخدام تشغيلي آخر.
              </p>
            </div>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setOutboundModalOpen(true)}
              disabled={outboundAvailableItems.length === 0 || kitchenOutboundReasons.length === 0}
            >
              تسجيل صرف
            </button>
          </div>
          <div className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">رقم المستند</th>
                    <th className="px-3 py-2 font-bold">سبب الصرف</th>
                    <th className="px-3 py-2 font-bold">الكمية</th>
                    <th className="px-3 py-2 font-bold">التكلفة</th>
                  </tr>
                </thead>
                <tbody>
                  {outboundRows.slice(0, 10).map((row) => (
                    <tr key={row.id}>
                      <td data-label="رقم المستند" className="px-3 py-2 font-bold">{row.voucher_no}</td>
                      <td data-label="سبب الصرف" className="px-3 py-2">{row.reason}</td>
                      <td data-label="الكمية" className="px-3 py-2">{row.total_quantity.toFixed(3)}</td>
                      <td data-label="التكلفة" className="px-3 py-2">{row.total_cost.toFixed(2)} د.ج</td>
                    </tr>
                  ))}
                  {outboundRows.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد عمليات صرف مسجلة حتى الآن.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {showCounts ? (
        <section className="admin-card space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-black text-[var(--text-primary)]">طابق الكمية الفعلية مع النظام</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                أنشئ الجرد ثم راجع الفرق، وبعدها نفّذ التسوية إذا كانت البيانات صحيحة.
              </p>
            </div>
            <button type="button" className="btn-primary" onClick={() => setCountModalOpen(true)} disabled={items.length === 0}>
              تسجيل جرد
            </button>
          </div>
          <div className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">رقم المستند</th>
                    <th className="px-3 py-2 font-bold">الحالة</th>
                    <th className="px-3 py-2 font-bold">فرق الكمية</th>
                    <th className="px-3 py-2 font-bold">قيمة الفرق</th>
                    <th className="px-3 py-2 font-bold">الإجراء</th>
                  </tr>
                </thead>
                <tbody>
                  {stockCounts.slice(0, 20).map((row) => (
                    <tr key={row.id} className={`table-row--${resolveStockCountRowTone(row.status)}`}>
                      <td data-label="رقم المستند" className="px-3 py-2 font-bold">{row.count_no}</td>
                      <td data-label="الحالة" className="px-3 py-2">{row.status === 'settled' ? 'تمت التسوية' : 'بانتظار التسوية'}</td>
                      <td data-label="فرق الكمية" className="px-3 py-2">{row.total_variance_quantity.toFixed(3)}</td>
                      <td data-label="قيمة الفرق" className="px-3 py-2">{row.total_variance_value.toFixed(2)} د.ج</td>
                      <td data-label="الإجراء" className="px-3 py-2">
                        {row.status === 'pending' ? (
                          <button
                            type="button"
                            className="btn-primary ui-size-sm"
                            onClick={() => settleCountMutation.mutate(row.id)}
                            disabled={settleCountMutation.isPending}
                          >
                            {settlingCountId === row.id ? 'جارٍ التسوية...' : 'تسوية الآن'}
                          </button>
                        ) : (
                          '-'
                        )}
                      </td>
                    </tr>
                  ))}
                  {stockCounts.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد عمليات جرد مسجلة حتى الآن.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {showItems ? (
        <section className="admin-card space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 className="text-lg font-black text-[var(--text-primary)]">تتبّع حركة كل صنف</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                فلتر بالحركة أو الصنف أو عدد الصفوف حتى تصل بسرعة إلى السجل الذي تريد مراجعته.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <select className="form-select w-40" value={ledgerMovement} onChange={(e) => setLedgerMovement(e.target.value as '' | 'inbound' | 'outbound')}>
                <option value="">كل الحركات</option>
                <option value="inbound">استلام</option>
                <option value="outbound">صرف</option>
              </select>
              <select className="form-select w-48" value={ledgerItemId} onChange={(e) => setLedgerItemId(e.target.value ? Number(e.target.value) : '')}>
                <option value="">كل الأصناف</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
              <select className="form-select w-36" value={ledgerLimit} onChange={(e) => setLedgerLimit(Number(e.target.value))}>
                <option value={100}>100 صف</option>
                <option value={200}>200 صف</option>
                <option value={500}>500 صف</option>
              </select>
            </div>
          </div>
          <div className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-2 font-bold">الوقت</th>
                    <th className="px-3 py-2 font-bold">الصنف</th>
                    <th className="px-3 py-2 font-bold">الحركة</th>
                    <th className="px-3 py-2 font-bold">الكمية</th>
                    <th className="px-3 py-2 font-bold">تكلفة الوحدة</th>
                    <th className="px-3 py-2 font-bold">قيمة الحركة</th>
                    <th className="px-3 py-2 font-bold">متوسط التكلفة</th>
                    <th className="px-3 py-2 font-bold">قبل</th>
                    <th className="px-3 py-2 font-bold">بعد</th>
                  </tr>
                </thead>
                <tbody>
                  {ledgerRows.map((row) => (
                    <tr key={row.id}>
                      <td data-label="الوقت" className="px-3 py-2 text-xs">
                        {new Date(parseApiDateMs(row.created_at)).toLocaleString('ar-DZ-u-nu-latn')}
                      </td>
                      <td data-label="الصنف" className="px-3 py-2 font-bold">{row.item_name}</td>
                      <td data-label="الحركة" className="px-3 py-2">{row.movement_kind === 'inbound' ? 'استلام' : 'صرف'}</td>
                      <td data-label="الكمية" className="px-3 py-2">{row.quantity.toFixed(3)}</td>
                      <td data-label="تكلفة الوحدة" className="px-3 py-2">{row.unit_cost.toFixed(2)}</td>
                      <td data-label="قيمة الحركة" className="px-3 py-2">{row.line_value.toFixed(2)}</td>
                      <td data-label="متوسط التكلفة" className="px-3 py-2">{row.running_avg_cost.toFixed(2)}</td>
                      <td data-label="قبل" className="px-3 py-2">{row.balance_before.toFixed(3)}</td>
                      <td data-label="بعد" className="px-3 py-2">{row.balance_after.toFixed(3)}</td>
                    </tr>
                  ))}
                  {ledgerRows.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-500">
                        لا توجد حركة أصناف مطابقة للفلاتر الحالية.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      <Modal open={itemModalOpen} onClose={() => setItemModalOpen(false)} title={editingItemId ? `تعديل الصنف #${editingItemId}` : 'إضافة صنف مخزني'} description="عرّف الصنف المخزني الذي ستسجل عليه حركات التوريد والصرف والجرد.">
        <form onSubmit={submitItem} className="grid gap-3 md:grid-cols-2">
          <label className="space-y-1"><span className="form-label">اسم الصنف</span><input className="form-input" placeholder="مثال: جبن موزاريلا" value={itemForm.name} onChange={(e) => setItemForm((p) => ({ ...p, name: e.target.value }))} required /></label>
          <label className="space-y-1"><span className="form-label">الوحدة</span><input className="form-input" placeholder="مثال: كغ / لتر / قطعة" value={itemForm.unit} onChange={(e) => setItemForm((p) => ({ ...p, unit: e.target.value }))} required /></label>
          <label className="space-y-1 md:col-span-2"><span className="form-label">حد التنبيه</span><input type="number" min={0} step="0.001" className="form-input" placeholder="الحد الذي يبدأ عنده تنبيه انخفاض المخزون" value={itemForm.alert_threshold} onChange={(e) => setItemForm((p) => ({ ...p, alert_threshold: Number(e.target.value) }))} /></label>
          <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 md:col-span-2"><input type="checkbox" checked={itemForm.active} onChange={(e) => setItemForm((p) => ({ ...p, active: e.target.checked }))} />تفعيل الصنف</label>
          <div className="md:col-span-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setItemModalOpen(false)}>إلغاء</button><button type="submit" className="btn-primary" disabled={saveItemMutation.isPending}>{saveItemMutation.isPending ? 'جارٍ الحفظ...' : 'حفظ'}</button></div>
        </form>
      </Modal>

      <Modal open={inboundModalOpen} onClose={() => setInboundModalOpen(false)} title="سند إدخال جديد" description="يوثّق هذا السند دخول المواد من المورد إلى المخزن مع التكلفة الفعلية لكل صنف.">
        <form onSubmit={submitInbound} className="space-y-3"><p className="text-xs text-gray-600">اختر المورد أولًا، ثم أضف الأصناف المرتبطة به فقط مع الكمية وتكلفة الوحدة.</p>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1">
              <span className="form-label">المورد</span>
              <select className="form-select" value={inboundSupplierId} onChange={(e) => setInboundSupplierId(e.target.value ? Number(e.target.value) : '')}><option value="">اختر المورد</option>{inboundEligibleSuppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
            </label>
            <label className="space-y-1">
              <span className="form-label">مرجع السند (اختياري)</span>
              <input className="form-input" value={inboundReference} onChange={(e) => setInboundReference(e.target.value)} placeholder="مثال: INV-2026-0042 أو رقم سند المورد" />
            </label>
          </div>
          <label className="space-y-1">
            <span className="form-label">ملاحظة السند (اختياري)</span>
            <textarea className="form-textarea" value={inboundNote} onChange={(e) => setInboundNote(e.target.value)} placeholder="مثال: توريد صباحي / دفعة عاجلة (اختياري)" />
          </label>
          {inboundLines.map((line, index) => {
            const hintedCost = line.item_id ? itemCostHintById.get(line.item_id) : undefined;
            return (
              <div key={`in-${index}`} className="space-y-1">
                <div className="grid gap-2 md:grid-cols-[2fr_1fr_1fr_auto]">
                  <label className="space-y-1">
                    <span className="form-label">الصنف</span>
                    <select className="form-select" value={line.item_id} onChange={(e) => updateInboundLineItem(index, Number(e.target.value))}>
                      <option value={0}>اختر الصنف من القائمة</option>
                      {inboundAvailableItems.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="form-label">الكمية</span>
                    <input
                      type="number"
                      min={0.001}
                      step="0.001"
                      className="form-input"
                      placeholder="الكمية"
                      value={line.quantity}
                      onChange={(e) => setInboundLines((prev) => prev.map((x, i) => i === index ? { ...x, quantity: Number(e.target.value) } : x))}
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="form-label">سعر الوحدة (د.ج)</span>
                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      className="form-input"
                      placeholder="تكلفة الوحدة"
                      value={line.unit_cost}
                      onChange={(e) => setInboundLines((prev) => prev.map((x, i) => i === index ? { ...x, unit_cost: Number(e.target.value) } : x))}
                    />
                  </label>
                  <div className="space-y-1">
                    <span className="form-label">إجراء</span>
                    <button type="button" className="btn-danger w-full" onClick={() => setInboundLines((prev) => prev.length > 1 ? prev.filter((_, i) => i !== index) : prev)}>حذف</button>
                  </div>
                </div>
                {line.item_id && hintedCost !== undefined ? <p className="text-xs text-gray-500">سعر مرجعي تلقائي للصنف: {hintedCost.toFixed(2)} د.ج</p> : null}
              </div>
            );
          })}
          <button type="button" className="btn-secondary" onClick={() => setInboundLines((prev) => [...prev, { ...emptyInboundLine }])}>إضافة سطر</button>
          <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setInboundModalOpen(false)}>إلغاء</button><button type="submit" className="btn-primary" disabled={createInboundMutation.isPending}>{createInboundMutation.isPending ? 'جارٍ الترحيل...' : 'ترحيل'}</button></div>
        </form>
      </Modal>

      <Modal open={outboundModalOpen} onClose={() => setOutboundModalOpen(false)} title="سند صرف جديد" description="يوثّق هذا السند خروج المواد من المخزن إلى المطبخ وفق الرصيد المتاح فعليًا.">
        <form onSubmit={submitOutbound} className="space-y-3"><p className="text-xs text-gray-600">اختر سبب الصرف ثم حدد الأصناف والكميات المطلوب تحويلها إلى المطبخ.</p>
          <label className="space-y-1">
            <span className="form-label">سبب الصرف</span>
            <select className="form-select" value={outboundReasonCode} onChange={(e) => setOutboundReasonCode(e.target.value)}><option value="">اختر سبب الصرف</option>{kitchenOutboundReasons.map((reason) => <option key={reason.code} value={reason.code}>{reason.label}</option>)}</select>
          </label>
          <label className="space-y-1">
            <span className="form-label">تفصيل السبب (اختياري)</span>
            <input className="form-input" value={outboundReasonNote} onChange={(e) => setOutboundReasonNote(e.target.value)} placeholder="مثال: تجهيز وردية العشاء (اختياري)" />
          </label>
          <label className="space-y-1">
            <span className="form-label">ملاحظة السند (اختياري)</span>
            <textarea className="form-textarea" value={outboundNote} onChange={(e) => setOutboundNote(e.target.value)} placeholder="أي ملاحظة تدعم عملية الصرف (اختياري)" />
          </label>
          {outboundLines.map((line, index) => {
            const availableQty = line.item_id ? balanceByItemId.get(line.item_id) ?? 0 : 0;
            const hintedCost = line.item_id ? itemCostHintById.get(line.item_id) : undefined;
            return (
              <div key={`out-${index}`} className="space-y-1">
                <div className="grid gap-2 md:grid-cols-[2fr_1fr_auto]">
                  <label className="space-y-1">
                    <span className="form-label">الصنف</span>
                    <select className="form-select" value={line.item_id} onChange={(e) => updateOutboundLineItem(index, Number(e.target.value))}>
                      <option value={0}>اختر الصنف من القائمة</option>
                      {outboundAvailableItems.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="form-label">الكمية المصروفة</span>
                    <input
                      type="number"
                      min={0.001}
                      max={availableQty > 0 ? availableQty : undefined}
                      step="0.001"
                      className="form-input"
                      placeholder="الكمية"
                      value={line.quantity}
                      onChange={(e) => setOutboundLines((prev) => prev.map((x, i) => i === index ? { ...x, quantity: Number(e.target.value) } : x))}
                    />
                  </label>
                  <div className="space-y-1">
                    <span className="form-label">إجراء</span>
                    <button type="button" className="btn-danger w-full" onClick={() => setOutboundLines((prev) => prev.length > 1 ? prev.filter((_, i) => i !== index) : prev)}>حذف</button>
                  </div>
                </div>
                {line.item_id ? (
                  <p className="text-xs text-gray-500">
                    المتاح: {availableQty.toFixed(3)}
                    {hintedCost !== undefined ? ` | سعر مرجعي: ${hintedCost.toFixed(2)} د.ج` : ''}
                  </p>
                ) : null}
              </div>
            );
          })}
          <button type="button" className="btn-secondary" onClick={() => setOutboundLines((prev) => [...prev, { ...emptyOutboundLine }])}>إضافة سطر</button>
          <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setOutboundModalOpen(false)}>إلغاء</button><button type="submit" className="btn-primary" disabled={createOutboundMutation.isPending}>{createOutboundMutation.isPending ? 'جارٍ الترحيل...' : 'ترحيل'}</button></div>
        </form>
      </Modal>

      <Modal open={countModalOpen} onClose={() => setCountModalOpen(false)} title="مستند جرد جديد" description="يوثّق هذا المستند الكميات الفعلية داخل المخزن تمهيدًا لتسوية فروقات الجرد.">
        <form onSubmit={submitCount} className="space-y-3"><p className="text-xs text-gray-600">أدخل الكمية الفعلية لكل صنف بدقة. بعد الحفظ يمكن تنفيذ التسوية من جدول الجرد.</p>
          <label className="space-y-1">
            <span className="form-label">ملاحظة الجرد (اختياري)</span>
            <textarea className="form-textarea" value={countNote} onChange={(e) => setCountNote(e.target.value)} placeholder="مثال: جرد نهاية يوم / مراجعة مفاجئة (اختياري)" />
          </label>
          {countLines.map((line, index) => {
            const systemQty = line.item_id ? balanceByItemId.get(line.item_id) ?? 0 : 0;
            const hintedCost = line.item_id ? itemCostHintById.get(line.item_id) : undefined;
            return (
              <div key={`count-${index}`} className="space-y-1">
                <div className="grid gap-2 md:grid-cols-[2fr_1fr_auto]">
                  <label className="space-y-1">
                    <span className="form-label">الصنف</span>
                    <select className="form-select" value={line.item_id} onChange={(e) => updateCountLineItem(index, Number(e.target.value))}>
                      <option value={0}>اختر الصنف من القائمة</option>
                      {items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className="form-label">الكمية الفعلية</span>
                    <input
                      type="number"
                      min={0}
                      step="0.001"
                      className="form-input"
                      placeholder="الكمية الفعلية"
                      value={line.counted_quantity}
                      onChange={(e) => setCountLines((prev) => prev.map((x, i) => i === index ? { ...x, counted_quantity: Number(e.target.value) } : x))}
                    />
                  </label>
                  <div className="space-y-1">
                    <span className="form-label">إجراء</span>
                    <button type="button" className="btn-danger w-full" onClick={() => setCountLines((prev) => prev.length > 1 ? prev.filter((_, i) => i !== index) : prev)}>حذف</button>
                  </div>
                </div>
                {line.item_id ? (
                  <p className="text-xs text-gray-500">
                    رصيد النظام: {systemQty.toFixed(3)}
                    {hintedCost !== undefined ? ` | سعر مرجعي: ${hintedCost.toFixed(2)} د.ج` : ''}
                  </p>
                ) : null}
              </div>
            );
          })}
          <button type="button" className="btn-secondary" onClick={() => setCountLines((prev) => [...prev, { ...emptyCountLine }])}>إضافة سطر</button>
          <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setCountModalOpen(false)}>إلغاء</button><button type="submit" className="btn-primary" disabled={createCountMutation.isPending}>{createCountMutation.isPending ? 'جارٍ الحفظ...' : 'حفظ'}</button></div>
        </form>
      </Modal>
    </div>
  );
}


