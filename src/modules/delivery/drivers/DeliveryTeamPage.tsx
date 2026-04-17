import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Truck } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { DeliveryDispatchAction } from '@/modules/delivery/components/DeliveryDispatchAction';
import {
  isAwaitingDispatchOffer,
  isAwaitingDispatchSelection,
  isOfferedDispatch,
  isReadyAssigned,
  resolveDeliveryDispatchSupplementalTag,
  resolveDispatchTargetLabel,
} from '@/modules/delivery/shared/deliveryDispatchState';
import { api } from '@/shared/api/client';
import type { Order } from '@/shared/api/types';
import { useDataView } from '@/shared/hooks/useDataView';
import { PageHeaderCard } from '@/shared/ui/PageHeaderCard';
import { PageShell } from '@/shared/ui/PageShell';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { TableControls } from '@/shared/ui/TableControls';
import { TablePagination } from '@/shared/ui/TablePagination';
import { TABLE_STATUS_CHIP_BASE, TABLE_STATUS_CHIP_BORDER_BASE } from '@/shared/ui/tableAppearance';
import { parseApiDateMs } from '@/shared/utils/date';
import { formatOrderTrackingId, orderRowTone, resolveOrderDeliveryAddress } from '@/shared/utils/order';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { sanitizeMojibakeText } from '@/shared/utils/textSanitizer';

const deliveryHighlightMap: Partial<Record<Order['status'], string>> = {
  READY: 'bg-emerald-50/70',
  OUT_FOR_DELIVERY: 'bg-sky-50/70',
  DELIVERY_FAILED: 'bg-rose-50/70',
};

function resolveDeliveryHighlight(status: Order['status']): string {
  return deliveryHighlightMap[status] ?? '';
}

type DeliveryOpsFilter =
  | 'all'
  | 'needs_selection'
  | 'waiting_dispatch'
  | 'offered'
  | 'ready_assigned'
  | 'out_for_delivery'
  | 'failed';

function DeliveryMetricChip({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: number;
  tone?: 'default' | 'success' | 'warning' | 'info';
}) {
  const toneClass =
    tone === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : tone === 'warning'
        ? 'border-amber-200 bg-amber-50 text-amber-800'
        : tone === 'info'
          ? 'border-sky-200 bg-sky-50 text-sky-800'
          : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]';

  return (
    <div className={`flex min-h-[44px] items-center justify-between gap-3 rounded-2xl border px-3 py-2 ${toneClass}`}>
      <span className="text-[11px] font-bold opacity-80">{label}</span>
      <span className="text-sm font-black">{value}</span>
    </div>
  );
}

export function DeliveryTeamPage() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const [dispatchTargetByOrder, setDispatchTargetByOrder] = useState<Record<number, string>>({});
  const [operationFilter, setOperationFilter] = useState<DeliveryOpsFilter>('all');

  const driversQuery = useQuery({
    queryKey: ['manager-drivers'],
    queryFn: () => api.managerDrivers(role ?? 'manager'),
    enabled: role === 'manager',
  });

  const providersQuery = useQuery({
    queryKey: ['manager-delivery-providers'],
    queryFn: () => api.managerDeliveryProviders(role ?? 'manager'),
    enabled: role === 'manager',
  });

  const deliveryPoliciesQuery = useQuery({
    queryKey: ['manager-delivery-policies'],
    queryFn: () => api.managerDeliveryPolicies(role ?? 'manager'),
    enabled: role === 'manager',
  });

  const ordersQuery = useQuery({
    queryKey: ['manager-orders-delivery'],
    queryFn: () => api.deliveryOrders(role ?? 'manager', 500),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(3000),
  });

  const capabilitiesQuery = useQuery({
    queryKey: ['manager-operational-capabilities'],
    queryFn: () => api.managerOperationalCapabilities(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(3000),
  });

  const invalidateDeliveryViews = () => {
    queryClient.invalidateQueries({ queryKey: ['manager-drivers'] });
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-providers'] });
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-policies'] });
    queryClient.invalidateQueries({ queryKey: ['manager-orders-delivery'] });
    queryClient.invalidateQueries({ queryKey: ['manager-operational-capabilities'] });
    queryClient.invalidateQueries({ queryKey: ['delivery-orders'] });
    queryClient.invalidateQueries({ queryKey: ['delivery-dispatches'] });
    queryClient.invalidateQueries({ queryKey: ['manager-active-orders'] });
    queryClient.invalidateQueries({ queryKey: ['manager-orders-paged'] });
    queryClient.invalidateQueries({ queryKey: ['manager-dashboard-operational-heart'] });
  };

  const notifyTeamMutation = useMutation({
    mutationFn: (orderId: number) => api.managerNotifyDeliveryTeam(role ?? 'manager', orderId),
    onSuccess: invalidateDeliveryViews,
  });

  const createDispatchMutation = useMutation({
    mutationFn: (payload: { order_id: number; provider_id?: number; driver_id?: number }) =>
      api.managerCreateDeliveryDispatch(role ?? 'manager', payload),
    onSuccess: invalidateDeliveryViews,
  });

  const cancelDispatchMutation = useMutation({
    mutationFn: (dispatchId: number) => api.managerCancelDeliveryDispatch(role ?? 'manager', dispatchId),
    onSuccess: invalidateDeliveryViews,
  });

  const providers = providersQuery.data ?? [];
  const drivers = driversQuery.data ?? [];
  const autoNotifyTeam = deliveryPoliciesQuery.data?.auto_notify_team ?? false;
  const deliveryOrders = useMemo<Order[]>(
    () => (ordersQuery.data ?? []).filter((order) => order.type === 'delivery'),
    [ordersQuery.data]
  );

  const deliveryOpsSummary = useMemo(() => {
    const needsSelection = deliveryOrders.filter((order) => isAwaitingDispatchSelection(order, autoNotifyTeam)).length;
    const waitingDispatch = deliveryOrders.filter((order) => isAwaitingDispatchOffer(order)).length;
    const offered = deliveryOrders.filter((order) => isOfferedDispatch(order)).length;
    const readyAssigned = deliveryOrders.filter((order) => isReadyAssigned(order)).length;
    const outForDelivery = deliveryOrders.filter((order) => order.status === 'OUT_FOR_DELIVERY').length;
    const failedDelivery = deliveryOrders.filter((order) => order.status === 'DELIVERY_FAILED').length;

    if (failedDelivery >= 2 || needsSelection >= 2 || waitingDispatch >= 3) {
      return {
        toneClass: 'border-rose-300 bg-rose-50 text-rose-700',
        title: 'هناك طلبات تحتاج تدخلًا مباشرًا',
        text: `تحديد الجهة ${needsSelection} | إرسال العرض ${waitingDispatch} | بانتظار القبول ${offered} | فشل التوصيل ${failedDelivery}`,
        needsSelection,
        waitingDispatch,
        offered,
        readyAssigned,
        outForDelivery,
        failedDelivery,
      };
    }

    if (needsSelection > 0 || waitingDispatch > 0 || offered > 0 || readyAssigned > 0 || failedDelivery > 0) {
      return {
        toneClass: 'border-amber-300 bg-amber-50 text-amber-700',
        title: 'القناة تحتاج متابعة',
        text: `تحديد الجهة ${needsSelection} | إرسال العرض ${waitingDispatch} | بانتظار القبول ${offered} | جاهز مع عنصر ${readyAssigned}`,
        needsSelection,
        waitingDispatch,
        offered,
        readyAssigned,
        outForDelivery,
        failedDelivery,
      };
    }

    return {
      toneClass: 'border-emerald-300 bg-emerald-50 text-emerald-700',
      title: 'القناة مستقرة',
      text: `خارج للتوصيل ${outForDelivery} | لا توجد طلبات معلقة`,
      needsSelection,
      waitingDispatch,
      offered,
      readyAssigned,
      outForDelivery,
      failedDelivery,
    };
  }, [autoNotifyTeam, deliveryOrders]);

  const filteredOrders = useMemo(() => {
    switch (operationFilter) {
      case 'needs_selection':
        return deliveryOrders.filter((order) => isAwaitingDispatchSelection(order, autoNotifyTeam));
      case 'waiting_dispatch':
        return deliveryOrders.filter((order) => isAwaitingDispatchOffer(order));
      case 'offered':
        return deliveryOrders.filter((order) => isOfferedDispatch(order));
      case 'ready_assigned':
        return deliveryOrders.filter((order) => isReadyAssigned(order));
      case 'out_for_delivery':
        return deliveryOrders.filter((order) => order.status === 'OUT_FOR_DELIVERY');
      case 'failed':
        return deliveryOrders.filter((order) => order.status === 'DELIVERY_FAILED');
      default:
        return deliveryOrders;
    }
  }, [autoNotifyTeam, deliveryOrders, operationFilter]);

  const view = useDataView<Order>({
    rows: filteredOrders,
    search,
    page,
    pageSize: 10,
    sortBy,
    sortDirection,
    searchAccessor: (order) =>
      `${order.id} ${formatOrderTrackingId(order.id)} ${order.status} ${order.phone ?? ''} ${resolveOrderDeliveryAddress(order)} ${
        resolveDispatchTargetLabel(order) ?? ''
      }`,
    sortAccessors: {
      created_at: (order) => parseApiDateMs(order.created_at),
      id: (order) => order.id,
      status: (order) => order.status,
      total: (order) => order.total,
    },
  });

  const deliveryEnabled = capabilitiesQuery.data?.delivery_enabled ?? true;
  const deliveryBlockedReason = sanitizeMojibakeText(
    capabilitiesQuery.data?.delivery_block_reason,
    'نظام التوصيل غير متاح حاليًا. راجع الإعدادات أو عناصر التوصيل.'
  );

  const mutationError =
    (notifyTeamMutation.error as Error | null)?.message ||
    (createDispatchMutation.error as Error | null)?.message ||
    (cancelDispatchMutation.error as Error | null)?.message ||
    '';

  const submitDispatch = async (order: Order, dispatchValue: string) => {
    const [targetType, rawId] = dispatchValue.split(':');
    const targetId = Number(rawId);
    if (!targetType || !Number.isFinite(targetId)) return;
    if (isAwaitingDispatchSelection(order, autoNotifyTeam)) {
      await notifyTeamMutation.mutateAsync(order.id);
    }
    await createDispatchMutation.mutateAsync({
      order_id: order.id,
      provider_id: targetType === 'provider' ? targetId : undefined,
      driver_id: targetType === 'driver' ? targetId : undefined,
    });
  };

  if (ordersQuery.isLoading || driversQuery.isLoading || providersQuery.isLoading || deliveryPoliciesQuery.isLoading) {
    return (
      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تحميل بيانات فريق التوصيل...
      </div>
    );
  }

  if (ordersQuery.isError || driversQuery.isError || providersQuery.isError || deliveryPoliciesQuery.isError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        تعذر تحميل بيانات فريق التوصيل.
      </div>
    );
  }

  return (
    <PageShell
      className="admin-page"
      header={
        <PageHeaderCard
          title="فريق التوصيل"
          description="تابع الطلبات التي تحتاج إجراء الآن، ثم نفذ الإجراء من الصف نفسه."
          icon={<Truck className="h-5 w-5" />}
          actions={
            <Link to="/console/delivery/settings" className="btn-secondary ui-size-sm">
              إعدادات التوصيل
            </Link>
          }
        />
      }
    >
      <div className="space-y-5">
        <div className={`rounded-2xl border px-4 py-3 ${deliveryOpsSummary.toneClass}`}>
          <p className="text-sm font-black">{deliveryOpsSummary.title}</p>
          <p className="text-xs font-semibold">{deliveryOpsSummary.text}</p>
        </div>

        {mutationError ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {mutationError}
          </div>
        ) : null}

        {!deliveryEnabled ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
            {deliveryBlockedReason}
          </div>
        ) : null}

        <div className="grid gap-2 sm:grid-cols-3">
          <DeliveryMetricChip label="بانتظار تحديد الجهة" value={deliveryOpsSummary.needsSelection} tone={deliveryOpsSummary.needsSelection > 0 ? 'warning' : 'default'} />
          <DeliveryMetricChip label="بانتظار القبول" value={deliveryOpsSummary.offered} tone={deliveryOpsSummary.offered > 0 ? 'info' : 'default'} />
          <DeliveryMetricChip
            label="خارج للتوصيل"
            value={deliveryOpsSummary.outForDelivery}
            tone={deliveryOpsSummary.outForDelivery > 0 ? 'success' : 'default'}
          />
        </div>

        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-black text-[var(--text-primary-strong)]">الطلبات الحية</h3>
              <p className="mt-1 text-xs text-[var(--text-muted)]">اختر الفلتر المناسب ثم أكمل الطلبات الظاهرة أمامك.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link to="/console/operations/orders?order_type=delivery" className="btn-secondary ui-size-sm">
                جدول الطلبات
              </Link>
              <Link to="/console/delivery/settings" className="btn-secondary ui-size-sm">
                إعدادات التوصيل
              </Link>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className={`${TABLE_STATUS_CHIP_BASE} border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)]`}>
              فلترة سريعة
            </span>
            {[
              ['all', 'كل الحالات'],
              ['needs_selection', `بانتظار تحديد الجهة (${deliveryOpsSummary.needsSelection})`],
              ['waiting_dispatch', `بانتظار إرسال العرض (${deliveryOpsSummary.waitingDispatch})`],
              ['offered', `بانتظار القبول (${deliveryOpsSummary.offered})`],
              ['ready_assigned', `جاهز مع عنصر (${deliveryOpsSummary.readyAssigned})`],
              ['out_for_delivery', `خارج للتوصيل (${deliveryOpsSummary.outForDelivery})`],
              ['failed', `فشل التوصيل (${deliveryOpsSummary.failedDelivery})`],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setOperationFilter(value as DeliveryOpsFilter);
                  setPage(1);
                }}
                className={`rounded-full border px-3 py-1 text-[11px] font-bold transition ${
                  operationFilter === value
                    ? 'border-[var(--accent-soft)] bg-[var(--surface-card-soft)] text-[var(--text-primary-strong)]'
                    : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)] hover:border-[var(--accent-soft)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <TableControls
            search={search}
            onSearchChange={(value) => {
              setSearch(value);
              setPage(1);
            }}
            sortBy={sortBy}
            onSortByChange={setSortBy}
            sortDirection={sortDirection}
            onSortDirectionChange={setSortDirection}
            sortOptions={[
              { value: 'created_at', label: 'ترتيب: الوقت' },
              { value: 'id', label: 'ترتيب: رقم الطلب' },
              { value: 'status', label: 'ترتيب: الحالة' },
              { value: 'total', label: 'ترتيب: المبلغ' },
            ]}
            searchPlaceholder="ابحث في طلبات التوصيل..."
          />

          <section className="admin-table-shell">
            <div className="adaptive-table overflow-x-auto">
              <table className="table-unified min-w-full text-sm">
                <thead className="bg-brand-50 text-gray-700">
                  <tr>
                    <th className="px-4 py-3 font-bold">رقم الطلب</th>
                    <th className="px-4 py-3 font-bold">الحالة الأساسية</th>
                    <th className="px-4 py-3 font-bold">العميل</th>
                    <th className="px-4 py-3 font-bold">العنوان</th>
                    <th className="px-4 py-3 font-bold">المبلغ</th>
                    <th className="px-4 py-3 font-bold">الجهة / السائق</th>
                    <th className="px-4 py-3 font-bold">المتابعة</th>
                    <th className="px-4 py-3 font-bold">الإجراء التالي</th>
                    <th className="px-4 py-3 font-bold">الوقت</th>
                  </tr>
                </thead>
                <tbody>
                  {view.rows.map((order) => {
                    const highlightClass = resolveDeliveryHighlight(order.status);
                    const cellClass = `px-4 py-3 ${highlightClass}`;
                    const statusTag = resolveDeliveryDispatchSupplementalTag(order, autoNotifyTeam);
                    const operationTime =
                      order.delivery_assignment_delivered_at ??
                      order.delivery_assignment_departed_at ??
                      order.delivery_assignment_assigned_at ??
                      order.delivery_dispatch_responded_at ??
                      order.delivery_dispatch_sent_at ??
                      order.delivery_team_notified_at ??
                      null;

                    return (
                      <tr key={order.id} className={`border-t border-gray-100 table-row--${orderRowTone(order.status)}`}>
                        <td data-label="رقم الطلب" className={`${cellClass} font-bold`}>
                          {formatOrderTrackingId(order.id)}
                        </td>
                        <td data-label="الحالة الأساسية" className={cellClass}>
                          <div className="flex justify-center">
                            <StatusBadge status={order.status} orderType={order.type} paymentStatus={order.payment_status ?? null} />
                          </div>
                        </td>
                        <td data-label="العميل" className={`${cellClass} text-xs`}>
                          {order.phone ?? '-'}
                        </td>
                        <td data-label="العنوان" className={`${cellClass} text-xs`}>
                          {resolveOrderDeliveryAddress(order)}
                        </td>
                        <td data-label="المبلغ" className={`${cellClass} font-bold`}>
                          {order.total.toFixed(2)} د.ج
                        </td>
                        <td data-label="الجهة / السائق" className={`${cellClass} text-xs`}>
                          {resolveDispatchTargetLabel(order) ?? '-'}
                        </td>
                        <td data-label="المتابعة" className={cellClass}>
                          <div className="flex justify-center">
                            {statusTag ? (
                              <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} ${statusTag.className}`}>{statusTag.label}</span>
                            ) : (
                              <span className={`${TABLE_STATUS_CHIP_BORDER_BASE} border-stone-300 bg-stone-100/80 text-stone-700`}>لا متابعة</span>
                            )}
                          </div>
                        </td>
                        <td data-label="الإجراء التالي" className={`${cellClass} text-xs`}>
                          <DeliveryDispatchAction
                            order={order}
                            providers={providers}
                            drivers={drivers}
                            autoNotifyTeam={autoNotifyTeam}
                            selectedValue={dispatchTargetByOrder[order.id] ?? ''}
                            onSelectedValueChange={(value) =>
                              setDispatchTargetByOrder((prev) => ({
                                ...prev,
                                [order.id]: value,
                              }))
                            }
                            onSubmit={() => void submitDispatch(order, dispatchTargetByOrder[order.id] ?? '')}
                            onCancel={(dispatchId) => cancelDispatchMutation.mutate(dispatchId)}
                            submitPending={notifyTeamMutation.isPending || createDispatchMutation.isPending}
                            cancelPending={cancelDispatchMutation.isPending}
                          />
                        </td>
                        <td data-label="الوقت" className={`${cellClass} text-xs`}>
                          {operationTime ? new Date(parseApiDateMs(operationTime)).toLocaleString('ar-DZ-u-nu-latn') : '-'}
                        </td>
                      </tr>
                    );
                  })}
                  {view.rows.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-10 text-center text-gray-500">
                        لا توجد طلبات تحتاج متابعة في هذا الفلتر.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <TablePagination page={view.page} totalPages={view.totalPages} totalRows={view.totalRows} onPageChange={setPage} />
          </section>
        </section>
      </div>
    </PageShell>
  );
}
