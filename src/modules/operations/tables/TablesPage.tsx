import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import QRCode from 'qrcode';
import { ArrowDownUp, ArrowLeft, ArrowRight, Check, Clock3, Copy, Download, ExternalLink, Eye, Plus, Printer, QrCode as QrCodeIcon, RotateCcw, Save, Search, SlidersHorizontal, Trash2, UtensilsCrossed } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { tableApi } from '@/entities/table';
import type { ManagerTable } from '@/entities/table';
import { useDataView } from '@/shared/hooks/useDataView';
import { PageShell } from '@/shared/ui/PageShell';
import { TablePagination } from '@/shared/ui/TablePagination';
import { TABLE_STATUS_CHIP_BORDER_BASE } from '@/shared/ui/tableAppearance';
import { Modal } from '@/shared/ui/Modal';
import { QrCode } from '@/shared/ui/QrCode';
import { tableStatusLabel } from '@/shared/utils/order';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';

type TableCreateStep = 'status' | 'review' | 'result';

const statusBadgeClass: Record<ManagerTable['status'], string> = {
  available: 'border border-emerald-300 bg-emerald-100 text-emerald-700',
  occupied: 'border border-amber-300 bg-amber-100 text-amber-700',
  reserved: 'border border-sky-300 bg-sky-100 text-sky-700',
};

function resolveTableRowTone(status: ManagerTable['status']): 'success' | 'warning' | 'danger' {
  if (status === 'available') return 'success';
  if (status === 'reserved') return 'warning';
  return 'danger';
}

function resolveTablePublicUrl(qrCode: string): string {
  if (/^https?:\/\//i.test(qrCode)) {
    return qrCode;
  }
  const path = qrCode.startsWith('/') ? qrCode : `/${qrCode}`;
  if (typeof window === 'undefined') {
    return path;
  }
  return `${window.location.origin}${path}`;
}

function CompactTableStat({
  label,
  value,
  icon,
  tone = 'default',
}: {
  label: string;
  value: string | number;
  icon: any;
  tone?: 'default' | 'warning' | 'info';
}) {
  const toneClass =
    tone === 'warning'
      ? 'border-amber-300 bg-amber-100/80 text-amber-900'
      : tone === 'info'
        ? 'border-sky-300 bg-sky-100/80 text-sky-900'
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

export function TablesPage() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [searchDraft, setSearchDraft] = useState('');
  const [sortBy, setSortBy] = useState('id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createStep, setCreateStep] = useState<TableCreateStep>('status');
  const [createStatus, setCreateStatus] = useState<ManagerTable['status']>('available');
  const [createdTable, setCreatedTable] = useState<ManagerTable | null>(null);
  const [pendingStatuses, setPendingStatuses] = useState<Record<number, ManagerTable['status']>>({});
  const [copiedTableId, setCopiedTableId] = useState<number | null>(null);
  const [settlementAmounts, setSettlementAmounts] = useState<Record<number, string>>({});
  const [qrPreviewTable, setQrPreviewTable] = useState<ManagerTable | null>(null);

  const refreshTables = () => {
    queryClient.invalidateQueries({ queryKey: ['manager-tables'] });
    queryClient.invalidateQueries({ queryKey: ['public-tables'] });
    queryClient.invalidateQueries({ queryKey: ['manager-orders-paged'] });
    queryClient.invalidateQueries({ queryKey: ['manager-dashboard-operational-heart'] });
    queryClient.invalidateQueries({ queryKey: ['manager-dashboard-smart-orders'] });
    queryClient.invalidateQueries({ queryKey: ['manager-financial'] });
    queryClient.invalidateQueries({ queryKey: ['public-table-session'] });
  };

  const tablesQuery = useQuery({
    queryKey: ['manager-tables'],
    queryFn: () => tableApi.getManagerTables(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(4000),
  });

  const createTableMutation = useMutation({
    mutationFn: (status: ManagerTable['status']) => tableApi.createTable(role ?? 'manager', status),
    onSuccess: (table) => {
      refreshTables();
      setCreatedTable(table);
      setCreateStep('result');
    },
  });

  const updateTableMutation = useMutation({
    mutationFn: ({ tableId, status }: { tableId: number; status: ManagerTable['status'] }) =>
      tableApi.updateTable(role ?? 'manager', tableId, status),
    onSuccess: () => {
      refreshTables();
    },
  });

  const deleteTableMutation = useMutation({
    mutationFn: (tableId: number) => tableApi.deleteTable(role ?? 'manager', tableId),
    onSuccess: () => {
      refreshTables();
    },
  });

  const settleTableMutation = useMutation({
    mutationFn: ({ tableId, amount }: { tableId: number; amount?: number }) =>
      tableApi.settleTableSession(role ?? 'manager', tableId, amount),
    onSuccess: (result) => {
      refreshTables();
      setSettlementAmounts((prev) => {
        const next = { ...prev };
        delete next[result.table_id];
        return next;
      });
    },
  });

  const view = useDataView({
    rows: tablesQuery.data ?? [],
    search,
    page,
    pageSize: 12,
    sortBy,
    sortDirection,
    searchAccessor: (row) => `${row.id} ${row.status} ${row.qr_code}`,
    sortAccessors: {
      id: (row) => row.id,
      status: (row) => row.status,
      total_orders: (row) => row.total_orders_count,
      active_orders: (row) => row.active_orders_count,
      unpaid_total: (row) => row.unpaid_total,
    },
  });

  const actionError = useMemo(() => {
    if (createTableMutation.isError) {
      return createTableMutation.error instanceof Error ? createTableMutation.error.message : 'تعذر إضافة الطاولة.';
    }
    if (updateTableMutation.isError) {
      return updateTableMutation.error instanceof Error ? updateTableMutation.error.message : 'تعذر تعديل حالة الطاولة.';
    }
    if (deleteTableMutation.isError) {
      return deleteTableMutation.error instanceof Error ? deleteTableMutation.error.message : 'تعذر حذف الطاولة.';
    }
    return '';
  }, [
    createTableMutation.error,
    createTableMutation.isError,
    deleteTableMutation.error,
    deleteTableMutation.isError,
    updateTableMutation.error,
    updateTableMutation.isError,
  ]);

  const settlementError = settleTableMutation.isError
    ? settleTableMutation.error instanceof Error
      ? settleTableMutation.error.message
      : 'تعذر تنفيذ تسوية الجلسة.'
    : '';

  const onCopyLink = async (table: ManagerTable) => {
    const link = resolveTablePublicUrl(table.qr_code);
    try {
      await navigator.clipboard.writeText(link);
      setCopiedTableId(table.id);
      window.setTimeout(() => setCopiedTableId((current) => (current === table.id ? null : current)), 1800);
    } catch {
      setCopiedTableId(null);
    }
  };

  const openQrPreview = (table: ManagerTable) => {
    setQrPreviewTable(table);
  };

  const closeQrPreview = () => {
    setQrPreviewTable(null);
  };

  const openTableQrPrintView = async (table: ManagerTable, mode: 'print' | 'pdf') => {
    const publicLink = resolveTablePublicUrl(table.qr_code);
    const popup = window.open('', '_blank', 'noopener,noreferrer,width=980,height=760');
    if (!popup) {
      window.alert('تعذر فتح نافذة رمز الطاولة. تأكد من السماح بالنوافذ المنبثقة.');
      return;
    }

    const styles = window.getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--text-primary-strong').trim() || '#3a261b';
    const mutedColor = styles.getPropertyValue('--text-muted').trim() || '#6b7280';
    const surfaceColor = styles.getPropertyValue('--surface-card').trim() || '#fffaf2';
    const borderColor = styles.getPropertyValue('--console-border').trim() || '#cab79f';
    const accentColor = styles.getPropertyValue('--primary-button-bg').trim() || '#a8612d';
    const qrDataUrl = await QRCode.toDataURL(publicLink, {
      width: 320,
      margin: 1,
      color: {
        dark: textColor,
        light: surfaceColor,
      },
    });

    popup.document.open();
    popup.document.write(`<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>رمز الطاولة #${table.id}</title>
  <style>
    body { font-family: Cairo, Tahoma, Arial, sans-serif; margin: 0; background: ${surfaceColor}; color: ${textColor}; }
    .page { max-width: 820px; margin: 0 auto; padding: 28px; }
    .shell { border: 1px solid ${borderColor}; border-radius: 24px; padding: 28px; }
    .hero { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 24px; }
    .title { font-size: 28px; font-weight: 800; margin: 0; }
    .muted { color: ${mutedColor}; font-size: 14px; margin-top: 6px; }
    .chip { display: inline-flex; padding: 8px 16px; border-radius: 999px; border: 1px solid ${borderColor}; background: rgba(255,255,255,0.65); font-weight: 700; }
    .layout { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 24px; align-items: start; }
    .card { border: 1px solid ${borderColor}; border-radius: 20px; padding: 18px; background: rgba(255,255,255,0.55); }
    .card h2 { margin: 0 0 12px; font-size: 16px; }
    .link { font-size: 14px; color: ${textColor}; word-break: break-word; line-height: 1.8; }
    .qr-wrap { display: flex; flex-direction: column; align-items: center; gap: 14px; }
    .qr-wrap img { border: 1px solid ${borderColor}; border-radius: 20px; padding: 12px; background: ${surfaceColor}; }
    .hint { margin-top: 18px; padding: 12px 14px; border-radius: 16px; background: rgba(255,255,255,0.7); color: ${mutedColor}; font-size: 13px; }
    .accent { color: ${accentColor}; font-weight: 700; }
    @media print { body { background: #fff; } .shell { box-shadow: none; } }
  </style>
</head>
<body>
  <div class="page">
    <div class="shell">
      <div class="hero">
        <div>
          <h1 class="title">رمز الطاولة #${table.id}</h1>
          <div class="muted">واجهة الطاولة العامة ورمز الوصول السريع</div>
        </div>
        <span class="chip">${tableStatusLabel(table.status)}</span>
      </div>
      <div class="layout">
        <div class="card">
          <h2>رابط الطاولة</h2>
          <div class="link">${publicLink}</div>
          <div class="hint">${mode === 'pdf' ? 'سيظهر مربع الطباعة الآن. اختر <span class="accent">حفظ كملف PDF</span> من خيارات الطابعة.' : 'سيظهر مربع الطباعة الآن مباشرة.'}</div>
        </div>
        <div class="card qr-wrap">
          <img src="${qrDataUrl}" width="320" height="320" alt="رمز الطاولة #${table.id}" />
          <div class="muted">امسح الرمز لفتح واجهة الطاولة مباشرة</div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>`);
    popup.document.close();
    popup.focus();
    window.setTimeout(() => popup.print(), 250);
  };

  const openCreateModal = () => {
    setCreateStep('status');
    setCreateStatus('available');
    setCreatedTable(null);
    setIsCreateModalOpen(true);
  };

  const closeCreateModal = () => {
    setIsCreateModalOpen(false);
    setCreateStep('status');
    setCreatedTable(null);
    setCreateStatus('available');
  };

  const resetCreateFlow = () => {
    setCreateStep('status');
    setCreatedTable(null);
    setCreateStatus('available');
  };

  const createdTableLink = createdTable ? resolveTablePublicUrl(createdTable.qr_code) : '';
  const occupiedTablesCount = (tablesQuery.data ?? []).filter((table) => table.has_active_session).length;
  const unpaidTotalAmount = (tablesQuery.data ?? []).reduce((sum, table) => sum + table.unpaid_total, 0);

  useEffect(() => {
    setSearchDraft(search);
  }, [search]);

  useEffect(() => {
    if (searchDraft.trim().length === 0 && search.trim().length > 0) {
      setSearch('');
      setPage(1);
    }
  }, [searchDraft, search]);

  const applySearch = () => {
    setSearch(searchDraft.trim());
    setPage(1);
  };

  const resetTableFilters = () => {
    setSearch('');
    setSearchDraft('');
    setSortBy('id');
    setSortDirection('asc');
    setPage(1);
    setShowAdvancedFilters(false);
  };

  const createStatusCards = [
    {
      id: 'available' as const,
      label: 'متاحة',
      description: 'جاهزة لاستقبال العملاء فورًا.',
      icon: Check,
      className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      activeClassName: 'border-emerald-400 bg-emerald-100 text-emerald-900 shadow-[0_10px_24px_rgba(16,120,74,0.18)]',
    },
    {
      id: 'reserved' as const,
      label: 'محجوزة',
      description: 'محجوزة مسبقًا لعميل أو مجموعة.',
      icon: Clock3,
      className: 'border-amber-200 bg-amber-50 text-amber-700',
      activeClassName: 'border-amber-400 bg-amber-100 text-amber-900 shadow-[0_10px_24px_rgba(184,113,0,0.18)]',
    },
    {
      id: 'occupied' as const,
      label: 'مشغولة',
      description: 'يتم استخدامها حاليًا داخل المطعم.',
      icon: UtensilsCrossed,
      className: 'border-rose-200 bg-rose-50 text-rose-700',
      activeClassName: 'border-rose-400 bg-rose-100 text-rose-900 shadow-[0_10px_24px_rgba(190,45,45,0.18)]',
    },
  ];

  if (tablesQuery.isLoading) {
    return <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">جارٍ تحميل الطاولات...</div>;
  }

  if (tablesQuery.isError) {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">تعذر تحميل بيانات الطاولات.</div>;
  }

  return (
    <PageShell
      className="admin-page"
      header={
        <div dir="rtl" className="space-y-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)]/70 px-3 py-3 text-right md:px-4">
          <div className="grid grid-cols-1 gap-2 xl:grid-cols-[minmax(200px,220px)_minmax(0,1fr)]">
            <button
              type="button"
              onClick={openCreateModal}
              className="btn-primary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
            >
              <Plus className="h-4 w-4" />
              <span>إضافة طاولة جديدة</span>
            </button>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <CompactTableStat
                label="جلسات نشطة"
                value={occupiedTablesCount}
                icon={<UtensilsCrossed className="h-4 w-4" />}
                tone={occupiedTablesCount > 0 ? 'warning' : 'default'}
              />
              <CompactTableStat
                label="غير المسدد"
                value={`${unpaidTotalAmount.toFixed(2)} د.ج`}
                icon={<Check className="h-4 w-4" />}
                tone={unpaidTotalAmount > 0 ? 'info' : 'default'}
              />
            </div>
          </div>

          <div className="hidden rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/55 p-3 md:block">
            <form
              className="grid gap-2 xl:grid-cols-[minmax(260px,1.15fr)_120px_180px_160px_120px]"
              onSubmit={(event) => {
                event.preventDefault();
                applySearch();
              }}
            >
              <label>
                <span className="form-label">حقل البحث</span>
                <div className="flex min-h-[42px] items-center gap-2 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3">
                  <Search className="h-4 w-4 text-[var(--text-secondary)]" />
                  <input
                    value={searchDraft}
                    onChange={(event) => setSearchDraft(event.target.value)}
                    placeholder="ابحث برقم الطاولة أو حالتها"
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
                  <option value="id">رقم الطاولة</option>
                  <option value="status">الحالة</option>
                  <option value="active_orders">الطلبات النشطة</option>
                  <option value="unpaid_total">غير المسدد</option>
                  <option value="total_orders">إجمالي الطلبات</option>
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

              <div>
                <span className="form-label">إعادة الضبط</span>
                <button
                  type="button"
                  className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
                  onClick={resetTableFilters}
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>مسح</span>
                </button>
              </div>
            </form>
          </div>

          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)]/55 p-3 md:hidden">
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                applySearch();
              }}
            >
              <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                <div className="flex min-h-[42px] items-center gap-2 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3">
                  <Search className="h-4 w-4 text-[var(--text-secondary)]" />
                  <input
                    value={searchDraft}
                    onChange={(event) => setSearchDraft(event.target.value)}
                    placeholder="ابحث برقم الطاولة أو حالتها"
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

              {showAdvancedFilters ? (
                <div className="grid gap-2 pt-1">
                  <label>
                    <span className="form-label">الترتيب حسب</span>
                    <select
                      value={sortBy}
                      onChange={(event) => setSortBy(event.target.value)}
                      className="form-select"
                    >
                      <option value="id">رقم الطاولة</option>
                      <option value="status">الحالة</option>
                      <option value="active_orders">الطلبات النشطة</option>
                      <option value="unpaid_total">غير المسدد</option>
                      <option value="total_orders">إجمالي الطلبات</option>
                    </select>
                  </label>

                  <button
                    type="button"
                    onClick={() => setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))}
                    className="btn-secondary ui-size-sm inline-flex w-full items-center justify-center gap-2"
                  >
                    <ArrowDownUp className="h-4 w-4" />
                    <span>{sortDirection === 'asc' ? 'اتجاه الترتيب: تصاعدي' : 'اتجاه الترتيب: تنازلي'}</span>
                  </button>

                  <button
                    type="button"
                    className="btn-secondary ui-size-sm inline-flex w-full items-center justify-center gap-2"
                    onClick={resetTableFilters}
                  >
                    <RotateCcw className="h-4 w-4" />
                    <span>مسح</span>
                  </button>
                </div>
              ) : null}
            </form>
          </div>
        </div>
      }
    >
      <div className="space-y-3">
      {actionError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{actionError}</div>
      ) : null}
      {settlementError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{settlementError}</div>
      ) : null}

      <section className="admin-table-shell">
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-brand-50 text-gray-700">
              <tr>
                <th className="px-4 py-3 font-bold">الطاولة</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">الجلسة</th>
                <th className="px-4 py-3 font-bold">غير المسدد</th>
                <th className="px-4 py-3 font-bold">تسوية الجلسة</th>
                <th className="px-4 py-3 font-bold">رابط الطاولة</th>
                <th className="px-4 py-3 font-bold">التحكم</th>
              </tr>
            </thead>
            <tbody>
              {view.rows.map((table) => {
                const targetStatus = pendingStatuses[table.id] ?? table.status;
                const canDelete = !table.has_active_session && table.total_orders_count === 0;
                const publicLink = resolveTablePublicUrl(table.qr_code);
                const settlementText = settlementAmounts[table.id] ?? '';
                const parsedSettlement = Number(settlementText);
                const settlementAmount =
                  settlementText.trim().length === 0 || !Number.isFinite(parsedSettlement) ? undefined : parsedSettlement;
                const canSettleSession = table.has_active_session && table.unpaid_total > 0;
                const invalidSettlementAmount = settlementAmount !== undefined && settlementAmount < table.unpaid_total;
                return (
                  <tr key={table.id} className={`border-t border-gray-100 align-top table-row--${resolveTableRowTone(table.status)}`}>
                    <td data-label="الطاولة" className="px-4 py-3">
                      <p className="font-black text-gray-900">#{table.id}</p>
                      <p className="text-xs text-gray-500">إجمالي الطلبات: {table.total_orders_count}</p>
                    </td>
                    <td data-label="الحالة" className="px-4 py-3">
                      <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${statusBadgeClass[table.status]}`}>
                        {tableStatusLabel(table.status)}
                      </span>
                    </td>
                    <td data-label="الجلسة" className="px-4 py-3 text-xs text-gray-600">
                      <div className="flex flex-wrap gap-1.5">
                        <span
                          className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${
                            table.has_active_session ? 'border-amber-300 bg-amber-100 text-amber-700' : 'border-stone-300 bg-stone-100 text-stone-700'
                          }`}
                        >
                          {table.has_active_session ? 'جلسة نشطة' : 'بدون جلسة'}
                        </span>
                        <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} border-sky-300 bg-sky-100 text-sky-700`}>
                          طلبات نشطة: {table.active_orders_count}
                        </span>
                        <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} border-[#d4a16a] bg-brand-50 text-brand-700`}>
                          غير مسددة: {table.unsettled_orders_count}
                        </span>
                      </div>
                    </td>
                    <td data-label="غير المسدد" className="px-4 py-3">
                      <p className="font-black text-brand-700">{table.unpaid_total.toFixed(2)} د.ج</p>
                    </td>
                    <td data-label="تسوية الجلسة" className="px-4 py-3">
                      {canSettleSession ? (
                        <div className="space-y-2">
                          <input
                            type="number"
                            min={table.unpaid_total}
                            step="0.1"
                            value={settlementText}
                            onChange={(event) =>
                              setSettlementAmounts((prev) => ({
                                ...prev,
                                [table.id]: event.target.value,
                              }))
                            }
                            className={`form-input w-full md:min-w-[180px] ${invalidSettlementAmount ? 'border-rose-300 bg-rose-50 focus:border-rose-400' : ''}`}
                            placeholder="المبلغ المستلم (اختياري)"
                            aria-invalid={invalidSettlementAmount}
                          />
                          <button
                            type="button"
                            onClick={() => settleTableMutation.mutate({ tableId: table.id, amount: settlementAmount })}
                            disabled={settleTableMutation.isPending || invalidSettlementAmount}
                            className="btn-primary ui-size-sm w-full inline-flex flex-row-reverse items-center justify-center gap-2"
                          >
                            <Check className="h-4 w-4" />
                            <span>{settleTableMutation.isPending ? 'جارٍ التسوية...' : 'تسوية نهائية'}</span>
                          </button>
                          {invalidSettlementAmount ? (
                            <div className="rounded-lg border border-rose-200 bg-rose-50 px-2 py-1 text-[11px] font-semibold text-rose-700">
                              المبلغ المستلم أقل من المستحق. أدخل قيمة مساوية أو أعلى.
                            </div>
                          ) : null}
                        </div>
                      ) : (
                        <p className="text-xs font-semibold text-gray-500">لا توجد تسوية مطلوبة.</p>
                      )}
                    </td>
                    <td data-label="رابط الطاولة" className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => openQrPreview(table)}
                        className="btn-secondary ui-size-sm inline-flex w-full flex-row-reverse items-center justify-center gap-2"
                      >
                        <Eye className="h-4 w-4" />
                        <span>إدارة الرابط</span>
                      </button>
                    </td>
                    <td data-label="التحكم" className="px-4 py-3">
                      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                        <select
                          value={targetStatus}
                          onChange={(event) =>
                            setPendingStatuses((prev) => ({
                              ...prev,
                              [table.id]: event.target.value as ManagerTable['status'],
                            }))
                          }
                          className="form-select w-full sm:min-w-[122px] sm:w-auto"
                        >
                          <option value="available">متاحة</option>
                          <option value="occupied">مشغولة</option>
                          <option value="reserved">محجوزة</option>
                        </select>
                        <button
                          type="button"
                          onClick={() => updateTableMutation.mutate({ tableId: table.id, status: targetStatus })}
                          disabled={updateTableMutation.isPending || targetStatus === table.status}
                          className="btn-primary ui-size-sm inline-flex w-full flex-row-reverse items-center justify-center gap-2 sm:w-auto"
                        >
                          <Save className="h-4 w-4" />
                          <span>حفظ</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteTableMutation.mutate(table.id)}
                          disabled={deleteTableMutation.isPending || !canDelete}
                          className="btn-danger ui-size-sm inline-flex w-full flex-row-reverse items-center justify-center gap-2 sm:w-auto"
                          title={canDelete ? 'حذف الطاولة' : 'لا يمكن حذف طاولة لها جلسة أو سجل طلبات'}
                        >
                          <Trash2 className="h-4 w-4" />
                          <span>حذف</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {view.rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-gray-500">
                    لا توجد طاولات مطابقة.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <TablePagination page={view.page} totalPages={view.totalPages} totalRows={view.totalRows} onPageChange={setPage} />
      </section>

      <Modal
        open={isCreateModalOpen}
        onClose={closeCreateModal}
        title={
          <span className="inline-flex items-center gap-2">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-brand-300 bg-brand-50 text-brand-700">
              <Plus className="h-5 w-5" />
            </span>
            <span>الطاولة</span>
          </span>
        }
        description={undefined}
        footer={(
          <div className="flex flex-wrap items-center gap-2">
            {createStep === 'review' ? (
              <button
                type="button"
                className="btn-secondary inline-flex min-h-[44px] min-w-[144px] items-center justify-center gap-2"
                onClick={() => setCreateStep('status')}
              >
                <ArrowRight className="h-4 w-4" />
                <span>رجوع</span>
              </button>
            ) : null}
            {createStep === 'result' && createdTable ? (
              <button
                type="button"
                className="btn-primary inline-flex min-h-[44px] min-w-[144px] items-center justify-center gap-2"
                onClick={resetCreateFlow}
              >
                <Plus className="h-4 w-4" />
                <span>إضافة طاولة أخرى</span>
              </button>
            ) : createStep === 'status' ? (
              <button
                type="button"
                className="btn-primary inline-flex min-h-[44px] min-w-[144px] items-center justify-center gap-2"
                onClick={() => setCreateStep('review')}
              >
                <ArrowLeft className="h-4 w-4" />
                <span>متابعة</span>
              </button>
            ) : createStep === 'review' ? (
              <button
                type="button"
                className="btn-primary inline-flex min-h-[44px] min-w-[144px] items-center justify-center gap-2"
                disabled={createTableMutation.isPending}
                onClick={() => createTableMutation.mutate(createStatus)}
              >
                <Check className="h-4 w-4" />
                <span>{createTableMutation.isPending ? 'جارٍ الإضافة...' : 'تأكيد الإضافة'}</span>
              </button>
            ) : null}
          </div>
        )}
      >
        <div className="space-y-4">
          <div className="grid gap-2 md:grid-cols-3">
            {(
              [
                { id: 'status', label: '1. حالة البداية' },
                { id: 'review', label: '2. المراجعة' },
                { id: 'result', label: '3. الرمز والإجراءات' },
              ] as Array<{ id: TableCreateStep; label: string }>
            ).map((stepCard) => {
              const active = createStep === stepCard.id;
              return (
                <button
                  key={stepCard.id}
                  type="button"
                  onClick={() => {
                    if (stepCard.id === 'review') {
                      setCreateStep('review');
                      return;
                    }
                    if (stepCard.id === 'result' && !createdTable) {
                      return;
                    }
                    setCreateStep(stepCard.id);
                  }}
                  disabled={stepCard.id === 'result' && !createdTable}
                  className={`rounded-2xl border px-3 py-3 text-right transition ${
                    active
                      ? 'border-[var(--accent-strong)] bg-[var(--surface-card-soft)] text-[var(--text-primary-strong)]'
                      : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]'
                  } ${stepCard.id === 'result' && !createdTable ? 'cursor-not-allowed opacity-60' : ''}`}
                >
                  <span className="block text-sm font-black">{stepCard.label}</span>
                </button>
              );
            })}
          </div>

          {createStep === 'status' ? (
            <div className="space-y-3">
              <div className="ops-surface-soft rounded-2xl border p-4">
                <p className="ops-title text-sm font-black">حالة الطاولة</p>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {createStatusCards.map((card) => {
                  const isSelected = createStatus === card.id;
                  const Icon = card.icon;
                  return (
                    <button
                      key={card.id}
                      type="button"
                      onClick={() => setCreateStatus(card.id)}
                      className={`flex min-h-[132px] flex-col items-start gap-2 rounded-2xl border px-4 py-4 text-right transition ${
                        isSelected ? card.activeClassName : card.className
                      }`}
                    >
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)]/80">
                        <Icon className="h-5 w-5" />
                      </span>
                      <span className="text-sm font-black">{card.label}</span>
                      <span className="text-xs font-semibold text-current/80">{card.description}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}

          {createStep === 'review' ? (
            <div className="space-y-3">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
                <p className="text-sm font-black text-[var(--text-primary-strong)]">المراجعة</p>
                <p className="mt-3 text-sm font-black text-[var(--text-primary-strong)]">{tableStatusLabel(createStatus)}</p>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {createStatusCards.map((card) => {
                  const isSelected = createStatus === card.id;
                  const Icon = card.icon;
                  return (
                    <div
                      key={`review-${card.id}`}
                      className={`flex min-h-[118px] flex-col items-start gap-2 rounded-2xl border px-4 py-4 text-right ${
                        isSelected ? card.activeClassName : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-muted)] opacity-70'
                      }`}
                    >
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)]/80">
                        <Icon className="h-5 w-5" />
                      </span>
                      <span className="text-sm font-black">{card.label}</span>
                      <span className="text-xs font-semibold text-current/80">{card.description}</span>
                    </div>
                  );
                })}
              </div>

              {createTableMutation.isError ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">
                  {createTableMutation.error instanceof Error ? createTableMutation.error.message : 'تعذر إضافة الطاولة.'}
                </div>
              ) : null}
            </div>
          ) : null}

          {createStep === 'result' ? (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <div className="space-y-3">
                {createdTable ? (
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
                    تم إنشاء الطاولة رقم #{createdTable.id} بالحالة {tableStatusLabel(createdTable.status)}.
                  </div>
                ) : null}

                <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
                  <p className="text-sm font-black text-[var(--text-primary-strong)]">الإجراءات</p>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => createdTable && onCopyLink(createdTable)}
                      disabled={!createdTable}
                      className="btn-secondary inline-flex flex-row-reverse items-center justify-center gap-2 disabled:opacity-60"
                    >
                      <Copy className="h-4 w-4" />
                      <span>نسخ الرابط</span>
                    </button>
                    {createdTable ? (
                      <a
                        href={createdTableLink}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-secondary inline-flex flex-row-reverse items-center justify-center gap-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                        <span>فتح الواجهة</span>
                      </a>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => createdTable && void openTableQrPrintView(createdTable, 'print')}
                      disabled={!createdTable}
                      className="btn-secondary inline-flex flex-row-reverse items-center justify-center gap-2 disabled:opacity-60"
                    >
                      <Printer className="h-4 w-4" />
                      <span>طباعة</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => createdTable && void openTableQrPrintView(createdTable, 'pdf')}
                      disabled={!createdTable}
                      className="btn-primary inline-flex flex-row-reverse items-center justify-center gap-2 disabled:opacity-60"
                    >
                      <Download className="h-4 w-4" />
                      <span>تنزيل PDF</span>
                    </button>
                  </div>
                </div>
              </div>

              <div className="ops-surface-card rounded-2xl border p-4">
                <p className="ops-title text-sm font-black">رمز الطاولة</p>
                <div className="mt-3 flex items-center justify-center">
                  <QrCode value={createdTableLink} size={190} />
                </div>
                <div className="ops-text mt-3 space-y-2 text-xs font-semibold">
                  <p className="truncate">الرابط: {createdTableLink || '-'}</p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </Modal>
      <Modal
        open={Boolean(qrPreviewTable)}
        onClose={closeQrPreview}
        title={
          <span className="inline-flex items-center gap-2">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-violet-300 bg-violet-50 text-violet-700">
              <QrCodeIcon className="h-5 w-5" />
            </span>
            <span>{qrPreviewTable ? `الطاولة #${qrPreviewTable.id}` : 'رمز الطاولة'}</span>
          </span>
        }
        description={undefined}
        footer={
          qrPreviewTable ? (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <button
                type="button"
                className="btn-secondary inline-flex w-full flex-row-reverse items-center justify-center gap-2"
                onClick={() => onCopyLink(qrPreviewTable)}
              >
                <Copy className="h-4 w-4" />
                <span>{copiedTableId === qrPreviewTable.id ? 'تم النسخ' : 'نسخ الرابط'}</span>
              </button>
              <a
                href={resolveTablePublicUrl(qrPreviewTable.qr_code)}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary inline-flex w-full flex-row-reverse items-center justify-center gap-2"
              >
                <ExternalLink className="h-4 w-4" />
                <span>فتح الواجهة</span>
              </a>
              <button
                type="button"
                className="btn-secondary inline-flex w-full flex-row-reverse items-center justify-center gap-2"
                onClick={() => void openTableQrPrintView(qrPreviewTable, 'print')}
              >
                <Printer className="h-4 w-4" />
                <span>طباعة</span>
              </button>
              <button
                type="button"
                className="btn-primary inline-flex w-full flex-row-reverse items-center justify-center gap-2"
                onClick={() => void openTableQrPrintView(qrPreviewTable, 'pdf')}
              >
                <Download className="h-4 w-4" />
                <span>تنزيل PDF</span>
              </button>
            </div>
          ) : null
        }
      >
        {qrPreviewTable ? (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="ops-surface-soft rounded-2xl border p-4 text-right">
              <p className="ops-title text-sm font-black">الرابط العام</p>
              <p className="ops-text mt-2 break-all text-sm font-semibold">{resolveTablePublicUrl(qrPreviewTable.qr_code)}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="ops-surface-card rounded-2xl border p-3">
                  <p className="ops-text-muted text-[11px] font-bold">رقم الطاولة</p>
                  <p className="ops-title mt-1 text-base font-black">#{qrPreviewTable.id}</p>
                </div>
                <div className="ops-surface-card rounded-2xl border p-3">
                  <p className="ops-text-muted text-[11px] font-bold">الحالة الحالية</p>
                  <div className="mt-2 flex justify-end">
                    <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${statusBadgeClass[qrPreviewTable.status]}`}>
                      {tableStatusLabel(qrPreviewTable.status)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="ops-surface-card rounded-2xl border p-4">
              <div className="flex justify-center">
                <QrCode value={resolveTablePublicUrl(qrPreviewTable.qr_code)} size={240} />
              </div>
              <p className="ops-text-muted mt-3 text-center text-xs font-semibold">امسح الرمز لفتح الطاولة مباشرة على الواجهة العامة.</p>
            </div>
          </div>
        ) : null}
      </Modal>
      </div>
    </PageShell>
  );
}
