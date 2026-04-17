import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChefHat, Clock3, Flame, History, PackageCheck } from 'lucide-react';
import { Link } from 'react-router-dom';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { KitchenMonitorSummary, OrderStatus } from '@/shared/api/types';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { TableControls } from '@/shared/ui/TableControls';
import { TablePagination } from '@/shared/ui/TablePagination';
import { TABLE_ACTION_BUTTON_BASE } from '@/shared/ui/tableAppearance';
import { parseApiDateMs } from '@/shared/utils/date';
import { formatOrderTrackingId, orderTypeLabel, resolveOrderDeliveryAddress } from '@/shared/utils/order';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';

const DEFAULT_KITCHEN_POLLING_MS = 5000;
const KITCHEN_PAGE_SIZE = 18;

type KitchenSort = 'created_at' | 'total' | 'status' | 'id';

const activeSummaryFallback: KitchenMonitorSummary = {
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

function normalizePollingMs(value?: number): number {
  if (!Number.isFinite(value)) {
    return DEFAULT_KITCHEN_POLLING_MS;
  }
  const parsed = Math.trunc(Number(value));
  if (parsed < 3000 || parsed > 60000) {
    return DEFAULT_KITCHEN_POLLING_MS;
  }
  return parsed;
}

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

function formatWait(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return 'لا يوجد انتظار متراكم';
  }
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}د ${remaining.toString().padStart(2, '0')}ث`;
}

function metricsWindowLabel(value: KitchenMonitorSummary['metrics_window']): string {
  if (value === 'week') {
    return 'هذا الأسبوع';
  }
  if (value === 'month') {
    return 'هذا الشهر';
  }
  return 'اليوم';
}

function summarizeItems(orderItems: Array<{ product_name: string; quantity: number }>): string {
  return orderItems
    .slice(0, 3)
    .map((item) => `${item.product_name} × ${item.quantity}`)
    .join('، ');
}

export function KitchenBoardPage() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();
  const [now, setNow] = useState(Date.now());
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<KitchenSort>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const runtimeSettingsQuery = useQuery({
    queryKey: ['kitchen-runtime-settings', role],
    queryFn: () => api.kitchenRuntimeSettings(role ?? 'kitchen'),
    enabled: role === 'kitchen',
    refetchInterval: adaptiveRefetchInterval(60_000, { minimumMs: 30_000 }),
  });

  const pollingMs = normalizePollingMs(runtimeSettingsQuery.data?.order_polling_ms);

  const ordersQuery = useQuery({
    queryKey: ['kitchen-orders-paged', 'active', page, KITCHEN_PAGE_SIZE, search, sortBy, sortDirection],
    queryFn: () =>
      api.kitchenOrdersPaged(role ?? 'kitchen', {
        page,
        pageSize: KITCHEN_PAGE_SIZE,
        scope: 'active',
        search,
        sortBy,
        sortDirection,
      }),
    enabled: role === 'kitchen',
    refetchInterval: adaptiveRefetchInterval(pollingMs, { minimumMs: 3000 }),
  });

  const invalidateKitchenAndManagerViews = () => {
    const keys = [
      'kitchen-orders-paged',
      'manager-orders-paged',
      'manager-kitchen-monitor-paged',
      'manager-dashboard-operational-heart',
      'manager-dashboard-smart-orders',
    ];
    for (const key of keys) {
      queryClient.invalidateQueries({ queryKey: [key] });
    }
  };

  const startMutation = useMutation({
    mutationFn: (orderId: number) => api.kitchenStartOrder(role ?? 'kitchen', orderId),
    onSuccess: invalidateKitchenAndManagerViews,
  });

  const readyMutation = useMutation({
    mutationFn: (orderId: number) => api.kitchenReadyOrder(role ?? 'kitchen', orderId),
    onSuccess: invalidateKitchenAndManagerViews,
  });

  const totalRows = ordersQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalRows / KITCHEN_PAGE_SIZE));
  const summary = ordersQuery.data?.summary ?? activeSummaryFallback;

  const groupedCounts = useMemo(
    () => ({
      newOrders: summary.sent_to_kitchen,
      inPreparation: summary.in_preparation,
      ready: summary.ready,
    }),
    [summary],
  );

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  if (ordersQuery.isLoading && !ordersQuery.data) {
    return (
      <div className="rounded-3xl border border-[var(--console-border)] bg-[var(--surface-card)] p-6 text-sm font-semibold text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تحميل تنفيذ المطبخ...
      </div>
    );
  }

  if (ordersQuery.isError) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm font-semibold text-rose-700">
        تعذر تحميل لوحة التنفيذ الآن.
      </div>
    );
  }

  const actionError =
    (startMutation.error as Error | null)?.message ?? (readyMutation.error as Error | null)?.message ?? null;

  return (
    <div className="space-y-4">
      <section className="admin-card space-y-4 p-4 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">LIVE KITCHEN FLOW</p>
            <h2 className="mt-2 text-xl font-black text-[var(--text-primary-strong)]">لوحة التنفيذ المباشر</h2>
            <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
              شاشة سريعة للمطبخ: الطلب الجديد يبدأ التحضير، والطلب الجاهز ينتقل مباشرة إلى السجل.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs font-black text-[var(--text-secondary)]">
              التحديث كل {(pollingMs / 1000).toFixed(0)} ث
            </span>
            <Link
              to="/kitchen/console/history"
              className="inline-flex min-h-[42px] items-center gap-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 text-sm font-black text-[var(--text-primary)] transition hover:border-[#b98757]"
            >
              <History className="h-4 w-4" />
              <span>سجل الطلبات</span>
            </Link>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <KitchenMetricCard
            label="طلبات جديدة"
            value={groupedCounts.newOrders}
            hint="بانتظار بدء التحضير"
            icon={<ChefHat className="h-5 w-5" />}
            tone="amber"
          />
          <KitchenMetricCard
            label="قيد التحضير"
            value={groupedCounts.inPreparation}
            hint="طلبات يعمل عليها الفريق الآن"
            icon={<Flame className="h-5 w-5" />}
            tone="orange"
          />
          <KitchenMetricCard
            label="جاهزة خارج اللوحة"
            value={groupedCounts.ready}
            hint="انتقلت إلى السجل بعد التجهيز"
            icon={<PackageCheck className="h-5 w-5" />}
            tone="emerald"
          />
          <KitchenMetricCard
            label={`متوسط التحضير - ${metricsWindowLabel(summary.metrics_window)}`}
            value={`${summary.avg_prep_minutes_today.toFixed(1)} د`}
            hint="يخضع لإعداد نافذة الإحصائيات"
            icon={<Clock3 className="h-5 w-5" />}
            tone="sky"
          />
          <KitchenMetricCard
            label="أقدم انتظار"
            value={formatWait(summary.oldest_order_wait_seconds)}
            hint="منذ دخول الطلب إلى طابور المطبخ"
            icon={<Clock3 className="h-5 w-5" />}
            tone="stone"
          />
        </div>
      </section>

      {actionError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
          {actionError}
        </div>
      ) : null}

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
        searchPlaceholder="ابحث برقم الطلب أو الهاتف أو نوع الطلب..."
      />

      <section className="admin-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--console-border)] text-sm">
            <thead className="bg-[var(--surface-card-soft)]">
              <tr className="text-[var(--text-secondary)]">
                <th className="px-4 py-3 text-right font-black">الطلب</th>
                <th className="px-4 py-3 text-right font-black">النوع/الوصول</th>
                <th className="px-4 py-3 text-right font-black">العناصر</th>
                <th className="px-4 py-3 text-right font-black">الانتظار</th>
                <th className="px-4 py-3 text-right font-black">الحالة</th>
                <th className="px-4 py-3 text-right font-black">الإجراء</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--console-border)]">
              {(ordersQuery.data?.items ?? []).length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm font-semibold text-[var(--text-muted)]">
                    لا توجد طلبات نشطة في المطبخ الآن.
                  </td>
                </tr>
              ) : null}

              {(ordersQuery.data?.items ?? []).map((order) => {
                const startPending = startMutation.isPending && startMutation.variables === order.id;
                const readyPending = readyMutation.isPending && readyMutation.variables === order.id;
                const noteText = order.notes?.trim();

                return (
                  <tr key={order.id} className="align-top">
                    <td className="px-4 py-4">
                      <div className="space-y-1">
                        <p className="text-base font-black text-[var(--text-primary-strong)]">
                          {formatOrderTrackingId(order.id)}
                        </p>
                        <p className="text-xs font-semibold text-[var(--text-muted)]">
                          {new Date(parseApiDateMs(order.created_at)).toLocaleString('ar-DZ-u-nu-latn')}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="space-y-1">
                        <p className="font-black text-[var(--text-primary)]">{orderTypeLabel(order.type)}</p>
                        <p className="text-xs font-semibold text-[var(--text-muted)]">
                          {order.table_id
                            ? `طاولة ${order.table_id}`
                            : order.phone
                              ? `هاتف ${order.phone}`
                              : order.type === 'delivery'
                                ? resolveOrderDeliveryAddress(order) !== '-'
                                  ? resolveOrderDeliveryAddress(order)
                                  : 'توصيل'
                                : 'استلام من المطعم'}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="space-y-2">
                        <p className="font-black text-[var(--text-primary)]">{summarizeItems(order.items)}</p>
                        {order.items.length > 3 ? (
                          <p className="text-xs font-semibold text-[var(--text-muted)]">
                            + {order.items.length - 3} عناصر إضافية
                          </p>
                        ) : null}
                        {noteText ? (
                          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                            {noteText}
                          </div>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <p className="font-black text-[var(--text-primary)]">
                        {formatElapsed(now, order.sent_to_kitchen_at ?? order.created_at)}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge
                        status={order.status}
                        orderType={order.type}
                        paymentStatus={order.payment_status ?? null}
                      />
                    </td>
                    <td className="px-4 py-4">
                      {order.status === 'SENT_TO_KITCHEN' ? (
                        <button
                          type="button"
                          onClick={() => startMutation.mutate(order.id)}
                          disabled={startPending}
                          className={`${TABLE_ACTION_BUTTON_BASE} border-amber-300 bg-amber-100 text-amber-900 hover:bg-amber-50`}
                        >
                          {startPending ? 'جارٍ البدء...' : 'بدء التحضير'}
                        </button>
                      ) : null}

                      {order.status === 'IN_PREPARATION' ? (
                        <button
                          type="button"
                          onClick={() => readyMutation.mutate(order.id)}
                          disabled={readyPending}
                          className={`${TABLE_ACTION_BUTTON_BASE} border-emerald-300 bg-emerald-100 text-emerald-900 hover:bg-emerald-50`}
                        >
                          {readyPending ? 'جارٍ الحفظ...' : 'تم التجهيز'}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <TablePagination page={page} totalPages={totalPages} totalRows={totalRows} onPageChange={setPage} />
      </section>
    </div>
  );
}

function KitchenMetricCard({
  label,
  value,
  hint,
  icon,
  tone,
}: {
  label: string;
  value: string | number;
  hint: string;
  icon: ReactNode;
  tone: 'amber' | 'orange' | 'emerald' | 'sky' | 'stone';
}) {
  const toneClasses: Record<typeof tone, string> = {
    amber: 'border-amber-200 bg-amber-50 text-amber-900',
    orange: 'border-orange-200 bg-orange-50 text-orange-900',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    sky: 'border-sky-200 bg-sky-50 text-sky-900',
    stone: 'border-stone-200 bg-stone-50 text-stone-900',
  };

  return (
    <article className={`rounded-3xl border p-4 ${toneClasses[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold opacity-80">{label}</p>
          <p className="mt-2 text-xl font-black">{value}</p>
        </div>
        <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/40 bg-white/70">
          {icon}
        </span>
      </div>
      <p className="mt-3 text-xs font-semibold opacity-80">{hint}</p>
    </article>
  );
}
