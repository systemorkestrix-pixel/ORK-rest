import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChefHat, Clock3, Flame, PackageCheck } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { KitchenMonitorSummary, KitchenOrdersPage, OrderStatus } from '@/shared/api/types';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { TableControls } from '@/shared/ui/TableControls';
import { TablePagination } from '@/shared/ui/TablePagination';
import { parseApiDateMs } from '@/shared/utils/date';
import { formatOrderTrackingId, orderTypeLabel, resolveOrderDeliveryAddress } from '@/shared/utils/order';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';

const KITCHEN_PAGE_SIZE = 24;

type KitchenSort = 'created_at' | 'total' | 'status' | 'id';

const kitchenColumns: Array<{ title: string; status: OrderStatus }> = [
  { title: 'طلبات جديدة', status: 'SENT_TO_KITCHEN' },
  { title: 'قيد التحضير', status: 'IN_PREPARATION' },
  { title: 'جاهزة', status: 'READY' },
];

const emptySummary: KitchenMonitorSummary = {
  sent_to_kitchen: 0,
  in_preparation: 0,
  ready: 0,
  oldest_order_wait_seconds: 0,
  metrics_window: 'day',
  avg_prep_minutes_today: 0,
  warehouse_issued_quantity_today: 0,
  warehouse_issue_vouchers_today: 0,
  warehouse_issued_items_today: 0,
};

function formatElapsed(now: number, anchorTime: string): string {
  const anchorMs = parseApiDateMs(anchorTime);
  if (!Number.isFinite(anchorMs)) {
    return '0د 00ث';
  }
  const diff = Math.max(0, Math.floor((now - anchorMs) / 1000));
  const minutes = Math.floor(diff / 60);
  const seconds = diff % 60;
  return `${minutes}د ${seconds.toString().padStart(2, '0')}ث`;
}

function formatWaitSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return 'لا يوجد انتظار متراكم';
  }
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}د ${remaining.toString().padStart(2, '0')}ث`;
}

export function ManagerKitchenMonitorPage() {
  const role = useAuthStore((state) => state.role);
  const [now, setNow] = useState(Date.now());
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<KitchenSort>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const kitchenQuery = useQuery<KitchenOrdersPage>({
    queryKey: ['manager-kitchen-monitor-paged', page, KITCHEN_PAGE_SIZE, search, sortBy, sortDirection],
    queryFn: () =>
      api.managerKitchenOrdersPaged(role ?? 'manager', {
        page,
        pageSize: KITCHEN_PAGE_SIZE,
        search,
        sortBy,
        sortDirection,
      }),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000, { minimumMs: 5000 }),
  });

  const grouped = useMemo(() => {
    const orders = kitchenQuery.data?.items ?? [];
    return kitchenColumns.map((column) => ({
      ...column,
      orders: orders.filter((order) => order.status === column.status),
    }));
  }, [kitchenQuery.data]);

  const summary = kitchenQuery.data?.summary ?? emptySummary;
  const totalRows = kitchenQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalRows / KITCHEN_PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  if (kitchenQuery.isLoading && !kitchenQuery.data) {
    return (
      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-6 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تحميل مراقبة المطبخ...
      </div>
    );
  }

  if (kitchenQuery.isError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        تعذر تحميل بيانات المطبخ.
      </div>
    );
  }

  return (
    <div className="admin-page">
      <section className="admin-card flex flex-col gap-4 p-4 md:p-5">
        <div className="admin-header">
          <h2 className="admin-title">مراقبة المطبخ</h2>
          <p className="admin-subtitle">هذا القسم يعرض طابور التحضير داخل المطبخ بعد تفعيل الإضافة، من دون خلطه مع دورة العمليات الأساسية.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-[var(--text-muted)]">طلبات جديدة</p>
                <p className="mt-1 text-2xl font-black text-[var(--text-primary)]">{summary.sent_to_kitchen}</p>
              </div>
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-100 text-amber-800">
                <ChefHat className="h-5 w-5" />
              </span>
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-[var(--text-muted)]">قيد التحضير</p>
                <p className="mt-1 text-2xl font-black text-[var(--text-primary)]">{summary.in_preparation}</p>
              </div>
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-orange-100 text-orange-800">
                <Flame className="h-5 w-5" />
              </span>
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-[var(--text-muted)]">جاهزة للتسليم</p>
                <p className="mt-1 text-2xl font-black text-[var(--text-primary)]">{summary.ready}</p>
              </div>
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800">
                <PackageCheck className="h-5 w-5" />
              </span>
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-[var(--text-muted)]">أقدم انتظار</p>
                <p className="mt-1 text-lg font-black text-[var(--text-primary)]">
                  {formatWaitSeconds(summary.oldest_order_wait_seconds)}
                </p>
              </div>
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-800">
                <Clock3 className="h-5 w-5" />
              </span>
            </div>
          </div>
        </div>
      </section>

      <TableControls
        search={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        sortBy={sortBy}
        onSortByChange={(value) => {
          setSortBy(value as KitchenSort);
          setPage(1);
        }}
        sortDirection={sortDirection}
        onSortDirectionChange={(value) => {
          setSortDirection(value);
          setPage(1);
        }}
        sortOptions={[
          { value: 'created_at', label: 'الترتيب حسب وقت الإنشاء' },
          { value: 'status', label: 'الترتيب حسب الحالة' },
          { value: 'total', label: 'الترتيب حسب المبلغ' },
          { value: 'id', label: 'الترتيب حسب رقم الطلب' },
        ]}
        searchPlaceholder="ابحث برقم الطلب أو رقم الهاتف أو الحالة..."
      />

      <div className="grid gap-4 xl:grid-cols-3">
        {grouped.map((column) => (
          <section key={column.status} className="admin-card">
            <header className="flex items-center justify-between border-b border-[var(--console-border)] px-4 py-3">
              <h3 className="text-sm font-black text-[var(--text-primary)]">{column.title}</h3>
              <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700">
                {column.orders.length}
              </span>
            </header>

            <div className="space-y-3 p-3">
              {column.orders.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[var(--console-border)] p-4 text-center text-xs text-[var(--text-faint)]">
                  لا توجد طلبات في هذا العمود.
                </div>
              ) : null}

              {column.orders.map((order) => (
                <article
                  key={order.id}
                  className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4 transition-colors"
                >
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <p className="text-base font-black text-[var(--text-primary-strong)]">
                      طلب {formatOrderTrackingId(order.id)}
                    </p>
                    <StatusBadge
                      status={order.status}
                      orderType={order.type}
                      paymentStatus={order.payment_status ?? null}
                    />
                  </div>

                  <p className="text-xs font-semibold text-[var(--text-secondary)]">{orderTypeLabel(order.type)}</p>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">
                    {order.table_id
                      ? `طاولة ${order.table_id}`
                      : order.phone
                        ? `هاتف ${order.phone}`
                        : order.type === 'delivery'
                          ? resolveOrderDeliveryAddress(order) !== '-'
                            ? `توصيل: ${resolveOrderDeliveryAddress(order)}`
                            : 'توصيل'
                          : 'طلب خارجي'}
                  </p>

                  <div className="mt-2 rounded-lg bg-[var(--surface-card)] px-2 py-1 text-xs text-[var(--text-secondary)]">
                    {order.items.map((item) => `${item.product_name} x ${item.quantity}`).join('، ')}
                  </div>

                  {order.notes ? (
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                      {order.notes}
                    </div>
                  ) : null}

                  <p className="mt-3 text-xs font-bold text-brand-700">
                    الوقت المنقضي: {formatElapsed(now, order.sent_to_kitchen_at ?? order.created_at)}
                  </p>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>

      <section className="admin-card">
        <TablePagination page={page} totalPages={totalPages} totalRows={totalRows} onPageChange={setPage} />
      </section>
    </div>
  );
}
