import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { DeliveryDriver } from '@/shared/api/types';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { parseApiDateMs } from '@/shared/utils/date';
import { sanitizeMojibakeText } from '@/shared/utils/textSanitizer';
import { formatOrderTrackingId, orderTypeLabel, resolveOrderDeliveryAddress } from '@/shared/utils/order';
import { resolveDriverFacingTaskStatusLabel } from '@/shared/utils/orderStatusPresentation';

function driverStatusLabel(status: DeliveryDriver['status']) {
  if (status === 'available') return 'متاح';
  if (status === 'busy') return 'مشغول';
  return 'متوقف';
}

function assignmentRowTone(status: string): 'success' | 'warning' | 'danger' {
  if (status === 'delivered') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}

export function DeliveryPanelPage() {
  const role = useAuthStore((state) => state.role);
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const [driverTargetByDispatch, setDriverTargetByDispatch] = useState<Record<number, number>>({});

  const ordersQuery = useQuery({
    queryKey: ['delivery-orders'],
    queryFn: () => api.deliveryOrders(role ?? 'delivery'),
    enabled: role === 'delivery',
    refetchInterval: adaptiveRefetchInterval(3000),
  });

  const historyQuery = useQuery({
    queryKey: ['delivery-history'],
    queryFn: () => api.deliveryHistory(role ?? 'delivery'),
    enabled: role === 'delivery',
    refetchInterval: adaptiveRefetchInterval(4000),
  });

  const teamDriversQuery = useQuery({
    queryKey: ['delivery-team-drivers'],
    queryFn: () => api.deliveryTeamDrivers(role ?? 'delivery'),
    enabled: role === 'delivery',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const invalidateDeliveryViews = (options?: { includeDashboard?: boolean }) => {
    const keys = [
      'delivery-orders',
      'delivery-history',
      'delivery-team-drivers',
      'delivery-dispatches',
      'manager-orders-paged',
      'manager-orders-delivery',
      'manager-dashboard-operational-heart',
      'manager-dashboard-smart-orders',
    ];
    for (const key of keys) {
      queryClient.invalidateQueries({ queryKey: [key] });
    }
    if (options?.includeDashboard) {
      queryClient.invalidateQueries({ queryKey: ['manager-dashboard-operational-heart'] });
      queryClient.invalidateQueries({ queryKey: ['manager-dashboard-smart-orders'] });
    }
  };

  const assignDispatchToDriverMutation = useMutation({
    mutationFn: ({ dispatchId, driverId }: { dispatchId: number; driverId: number }) =>
      api.deliveryAssignDispatchToDriver(role ?? 'delivery', dispatchId, driverId),
    onSuccess: () => invalidateDeliveryViews(),
  });

  const rejectDispatchMutation = useMutation({
    mutationFn: (dispatchId: number) => api.deliveryRejectDispatch(role ?? 'delivery', dispatchId),
    onSuccess: () => invalidateDeliveryViews({ includeDashboard: true }),
  });

  const loading = ordersQuery.isLoading || historyQuery.isLoading || teamDriversQuery.isLoading;
  const hasError = ordersQuery.isError || historyQuery.isError || teamDriversQuery.isError;

  if (loading) {
    return (
      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تحميل لوحة جهة التوصيل...
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        تعذر تحميل بيانات جهة التوصيل.
      </div>
    );
  }

  const orders = ordersQuery.data ?? [];
  const historyRows = historyQuery.data ?? [];
  const teamDrivers = teamDriversQuery.data ?? [];

  const providerName =
    teamDrivers[0]?.provider_name ??
    orders.find((order) => order.delivery_dispatch_provider_name)?.delivery_dispatch_provider_name ??
    user?.name ??
    'جهة التوصيل';

  const providerOffers = orders.filter(
    (order) => order.delivery_dispatch_status === 'offered' && order.delivery_dispatch_scope === 'provider' && order.delivery_dispatch_id
  );
  const driverOffers = orders.filter(
    (order) => order.delivery_dispatch_status === 'offered' && order.delivery_dispatch_scope === 'driver'
  );
  const providerActiveOrders = orders.filter(
    (order) =>
      order.delivery_assignment_status === 'assigned' ||
      order.delivery_assignment_status === 'departed' ||
      order.status === 'OUT_FOR_DELIVERY'
  );
  const failedOrders = orders.filter((order) => order.status === 'DELIVERY_FAILED' && !order.delivery_failure_resolution_status);
  const completedToday = historyRows.filter((row) => row.assignment_status === 'delivered').length;

  const activeDrivers = teamDrivers.filter((driver) => driver.active && driver.status !== 'inactive');
  const availableDrivers = teamDrivers.filter((driver) => driver.active && driver.status === 'available');
  const actionError =
    (assignDispatchToDriverMutation.error as Error | undefined)?.message ??
    (rejectDispatchMutation.error as Error | undefined)?.message ??
    '';

  return (
    <div className="space-y-6 text-[var(--text-primary)]">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-black text-[var(--text-primary-strong)]">لوحة جهة التوصيل</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {providerName} | وزّع العروض على السائقين وتابع التنفيذ من هنا.
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 py-3 text-sm font-semibold text-[var(--text-secondary)]">
          حساب اللوحة الحالي: <span className="font-black text-[var(--text-primary-strong)]">{user?.name ?? 'جلسة غير معروفة'}</span>
        </div>
      </div>

      {actionError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{actionError}</div>
      ) : null}

      <section className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4 shadow-[var(--console-shadow)]">
        <div className="space-y-1">
          <h3 className="text-base font-black text-[var(--text-primary-strong)]">ابدأ بالعروض الجديدة</h3>
          <p className="text-sm text-[var(--text-muted)]">
            وزّع العروض على السائقين، ثم تابع الطلبات الجارية وسجل اليوم من نفس الصفحة.
          </p>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4 shadow-[var(--console-shadow)]">
          <p className="text-xs font-bold text-[var(--text-muted)]">عروض واردة للجهة</p>
          <p className="mt-2 text-3xl font-black text-[var(--text-primary-strong)]">{providerOffers.length}</p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4 shadow-[var(--console-shadow)]">
          <p className="text-xs font-bold text-[var(--text-muted)]">بانتظار قبول السائق</p>
          <p className="mt-2 text-3xl font-black text-[var(--text-primary-strong)]">{driverOffers.length}</p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4 shadow-[var(--console-shadow)]">
          <p className="text-xs font-bold text-[var(--text-muted)]">طلبات جارية</p>
          <p className="mt-2 text-3xl font-black text-[var(--text-primary-strong)]">{providerActiveOrders.length}</p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4 shadow-[var(--console-shadow)]">
          <p className="text-xs font-bold text-[var(--text-muted)]">تم التسليم اليوم</p>
          <p className="mt-2 text-3xl font-black text-[var(--text-primary-strong)]">{completedToday}</p>
        </div>
      </section>

      {providerOffers.length > 0 ? (
        <section className="overflow-hidden rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] shadow-[var(--console-shadow)]">
          <div className="border-b border-[var(--console-border)] px-4 py-3">
            <h3 className="text-base font-black text-[var(--text-primary)]">الطلبات الواردة للجهة</h3>
            <p className="text-xs text-[var(--text-muted)]">اختر السائق المناسب لكل طلب ثم مرر العرض إليه.</p>
          </div>
          <div className="grid gap-3 p-4">
            {providerOffers.map((order) => {
              const selectedDriverId =
                driverTargetByDispatch[order.delivery_dispatch_id!] ?? availableDrivers[0]?.id ?? activeDrivers[0]?.id ?? null;
              const selectedDriver = teamDrivers.find((driver) => driver.id === selectedDriverId) ?? null;

              return (
                <article key={order.id} className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-lg font-black text-[var(--text-primary-strong)]">طلب {formatOrderTrackingId(order.id)}</p>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">{orderTypeLabel(order.type)}</p>
                      <p className="text-sm text-[var(--text-secondary)]">الهاتف: {order.phone ?? '-'}</p>
                      <p className="text-sm text-[var(--text-secondary)]">العنوان: {resolveOrderDeliveryAddress(order)}</p>
                    </div>
                    <StatusBadge status={order.status} orderType={order.type} paymentStatus={order.payment_status ?? null} />
                  </div>

                  <div className="mt-3 grid gap-2 rounded-xl bg-[var(--surface-card)] p-3 text-sm md:grid-cols-3">
                    <p className="font-semibold text-[var(--text-primary)]">قيمة الطلب: {order.subtotal.toFixed(2)} د.ج</p>
                    <p className="font-semibold text-[var(--text-primary)]">رسوم التوصيل: {order.delivery_fee.toFixed(2)} د.ج</p>
                    <p className="font-black text-brand-700">الإجمالي: {order.total.toFixed(2)} د.ج</p>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <select
                      className="form-select min-w-[220px]"
                      value={selectedDriverId ?? ''}
                      onChange={(event) =>
                        setDriverTargetByDispatch((previous) => ({
                          ...previous,
                          [order.delivery_dispatch_id!]: Number(event.target.value),
                        }))
                      }
                    >
                      {activeDrivers.map((driver) => (
                        <option key={driver.id} value={driver.id}>
                          {driver.name} | {driverStatusLabel(driver.status)}
                        </option>
                      ))}
                    </select>

                    <button
                      type="button"
                      onClick={() =>
                        selectedDriverId
                          ? assignDispatchToDriverMutation.mutate({
                              dispatchId: order.delivery_dispatch_id!,
                              driverId: selectedDriverId,
                            })
                          : undefined
                      }
                      disabled={!selectedDriverId || assignDispatchToDriverMutation.isPending}
                      className="rounded-lg bg-sky-600 px-3 py-2 text-sm font-bold text-white hover:bg-sky-700 disabled:opacity-60"
                    >
                      {assignDispatchToDriverMutation.isPending ? 'جارٍ الإرسال...' : 'تسليم إلى سائق'}
                    </button>

                    <button
                      type="button"
                      onClick={() => rejectDispatchMutation.mutate(order.delivery_dispatch_id!)}
                      disabled={rejectDispatchMutation.isPending}
                      className="rounded-lg border border-rose-300 bg-white px-3 py-2 text-sm font-bold text-rose-700 hover:bg-rose-50 disabled:opacity-60"
                    >
                      {rejectDispatchMutation.isPending ? 'جارٍ الرفض...' : 'رفض العرض'}
                    </button>
                  </div>

                  {selectedDriver ? (
                    <p className="mt-2 text-xs font-semibold text-[var(--text-muted)]">السائق المحدد: {selectedDriver.name}</p>
                  ) : null}
                </article>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="overflow-hidden rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] shadow-[var(--console-shadow)]">
        <div className="border-b border-[var(--console-border)] px-4 py-3">
          <h3 className="text-base font-black text-[var(--text-primary)]">فريق الجهة</h3>
          <p className="text-xs text-[var(--text-muted)]">السائقون التابعون لهذه الجهة فقط، مع حالة التنفيذ والاستعداد.</p>
        </div>
        <div className="grid gap-3 p-4 md:grid-cols-3">
          {teamDrivers.map((driver) => (
            <article key={driver.id} className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-black text-[var(--text-primary-strong)]">{driver.name}</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">{driver.phone}</p>
                  <p className="text-sm text-[var(--text-secondary)]">{driver.vehicle || 'بدون مركبة محددة'}</p>
                </div>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ${
                    driver.status === 'available'
                      ? 'bg-emerald-500/15 text-emerald-700'
                      : driver.status === 'busy'
                        ? 'bg-amber-500/15 text-amber-700'
                        : 'bg-rose-500/15 text-rose-700'
                  }`}
                >
                  {driverStatusLabel(driver.status)}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className={`rounded-full px-2 py-1 text-xs font-bold ${driver.telegram_enabled ? 'bg-sky-500/15 text-sky-700' : 'bg-stone-500/15 text-stone-700'}`}>
                  {driver.telegram_enabled ? 'Telegram مربوط' : 'Telegram غير مربوط'}
                </span>
                <span className={`rounded-full px-2 py-1 text-xs font-bold ${driver.active ? 'bg-emerald-500/15 text-emerald-700' : 'bg-rose-500/15 text-rose-700'}`}>
                  {driver.active ? 'نشط' : 'موقوف'}
                </span>
              </div>
            </article>
          ))}

          {teamDrivers.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[var(--console-border)] px-4 py-8 text-center text-sm text-[var(--text-muted)] md:col-span-3">
              لا يوجد سائقون مرتبطون بهذه الجهة بعد.
            </div>
          ) : null}
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] shadow-[var(--console-shadow)]">
        <div className="border-b border-[var(--console-border)] px-4 py-3">
          <h3 className="text-base font-black text-[var(--text-primary)]">سجل الجهة</h3>
          <p className="text-xs text-[var(--text-muted)]">آخر عمليات التسليم والفشل داخل هذه الجهة.</p>
        </div>
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-brand-50 text-gray-700">
              <tr>
                <th className="px-4 py-3 font-bold">الطلب</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">قيمة الطلب</th>
                <th className="px-4 py-3 font-bold">رسوم التوصيل</th>
                <th className="px-4 py-3 font-bold">الإجمالي</th>
                <th className="px-4 py-3 font-bold">العنوان</th>
                <th className="px-4 py-3 font-bold">وقت الإنهاء</th>
              </tr>
            </thead>
            <tbody>
              {historyRows.map((row) => (
                <tr key={row.assignment_id} className={`border-t border-gray-100 table-row--${assignmentRowTone(row.assignment_status)}`}>
                  <td data-label="الطلب" className="px-4 py-3 font-bold">{formatOrderTrackingId(row.order_id)}</td>
                  <td data-label="الحالة" className="px-4 py-3 text-xs">
                    {resolveDriverFacingTaskStatusLabel({
                      orderStatus:
                        row.assignment_status === 'delivered'
                          ? 'DELIVERED'
                          : row.assignment_status === 'failed'
                            ? 'DELIVERY_FAILED'
                            : row.assignment_status === 'departed'
                              ? 'OUT_FOR_DELIVERY'
                              : 'READY',
                      assignmentStatus: row.assignment_status,
                    })}
                  </td>
                  <td data-label="قيمة الطلب" className="px-4 py-3 font-semibold">{row.order_subtotal.toFixed(2)} د.ج</td>
                  <td data-label="رسوم التوصيل" className="px-4 py-3 font-semibold">{row.delivery_fee.toFixed(2)} د.ج</td>
                  <td data-label="الإجمالي" className="px-4 py-3 font-black text-brand-700">{row.order_total.toFixed(2)} د.ج</td>
                  <td data-label="العنوان" className="px-4 py-3 text-xs text-[var(--text-muted)]">
                    {sanitizeMojibakeText(row.address, '-')}
                  </td>
                  <td data-label="وقت الإنهاء" className="px-4 py-3 text-xs text-[var(--text-muted)]">
                    {row.delivered_at ? new Date(parseApiDateMs(row.delivered_at)).toLocaleString('ar-DZ-u-nu-latn') : '-'}
                  </td>
                </tr>
              ))}
              {historyRows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    لا يوجد سجل عمليات حتى الآن.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      {failedOrders.length > 0 ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
          توجد حالات فشل توصيل تحتاج قرار معالجة من لوحة المدير قبل أن تُغلق الدورة بالكامل.
        </div>
      ) : null}

      {providerOffers.length === 0 && driverOffers.length === 0 && providerActiveOrders.length === 0 && historyRows.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--console-border)] bg-[var(--surface-card)] p-8 text-center text-sm text-[var(--text-muted)]">
          لا توجد مهام أو عمليات تخص هذه الجهة حاليًا.
        </div>
      ) : null}
    </div>
  );
}
