import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, AlertTriangle, Bell, ShieldAlert } from 'lucide-react';

import { useManagerAlerts, type AlertDomainKey, type AlertSeverity } from '@/app/navigation/ManagerAlertsContext';
import { PageHeaderCard } from '@/shared/ui/PageHeaderCard';
import { PageShell } from '@/shared/ui/PageShell';
import { sanitizeMojibakeText } from '@/shared/utils/textSanitizer';

type DomainFilter = AlertDomainKey | 'all';

const deliveryStatusFilters = new Set(['OUT_FOR_DELIVERY', 'DELIVERY_FAILED']);

function buildConsoleRoute(
  channel: string,
  section: string,
  params?: Record<string, string | null | undefined>
): string {
  const searchParams = new URLSearchParams({ channel, section });

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (!value) {
        continue;
      }
      searchParams.set(key, value);
    }
  }

  return `/console?${searchParams.toString()}`;
}

const domainRoutes: Record<AlertDomainKey, string> = {
  orders: buildConsoleRoute('operations', 'orders'),
  kitchen: buildConsoleRoute('kitchen', 'kitchenMonitor'),
  inventory: buildConsoleRoute('warehouse', 'warehouseOverview'),
  financial: buildConsoleRoute('finance', 'financeOverview'),
  delivery: buildConsoleRoute('delivery', 'delivery'),
  system: buildConsoleRoute('system', 'settings'),
  audit: buildConsoleRoute('intelligence', 'operationalHeart'),
};

function normalizeAlertRoute(route: string | null | undefined, domain: AlertDomainKey): string {
  if (!route) {
    return domainRoutes[domain];
  }

  const url = new URL(route, 'http://localhost');
  const pathname = url.pathname;
  const params = new URLSearchParams(url.search);

  const ensureDeliveryOrderType = (status: string | null) => {
    if (status && deliveryStatusFilters.has(status) && !params.get('order_type')) {
      params.set('order_type', 'delivery');
    }
  };

  if (pathname === '/console' && params.get('channel') && params.get('section')) {
    const channel = params.get('channel')!;
    const section = params.get('section')!;
    params.delete('channel');
    params.delete('section');
    return buildConsoleRoute(channel, section, Object.fromEntries(params.entries()));
  }

  if (pathname.startsWith('/console/operations/orders')) {
    ensureDeliveryOrderType(params.get('status'));
    return buildConsoleRoute('operations', 'orders', Object.fromEntries(params.entries()));
  }

  if (pathname.includes('/manager/orders') || pathname.includes('/operations/orders')) {
    ensureDeliveryOrderType(params.get('status'));
    return buildConsoleRoute('operations', 'orders', Object.fromEntries(params.entries()));
  }

  if (pathname.includes('/manager/delivery-team') || pathname.includes('/delivery-team')) {
    params.set('status', 'OUT_FOR_DELIVERY');
    ensureDeliveryOrderType('OUT_FOR_DELIVERY');
    return buildConsoleRoute('operations', 'orders', Object.fromEntries(params.entries()));
  }

  if (pathname.includes('/manager/kitchen-monitor') || pathname.includes('/kitchen-monitor')) {
    return buildConsoleRoute('kitchen', 'kitchenMonitor');
  }

  if (pathname.includes('/manager/expenses') || pathname.includes('/expenses')) {
    return buildConsoleRoute('finance', 'financeOverview');
  }
  if (pathname.includes('/manager/financial') || pathname.includes('/finance')) {
    return buildConsoleRoute('finance', 'financeOverview');
  }
  if (pathname.includes('/manager/warehouse') || pathname.includes('/warehouse')) {
    return buildConsoleRoute('warehouse', 'warehouseOverview');
  }
  if (pathname.includes('/manager/tables') || pathname.includes('/operations/tables')) {
    return buildConsoleRoute('operations', 'tables');
  }
  if (pathname.includes('/manager/products') || pathname.includes('/restaurant/menu') || pathname.includes('/operations/menu')) {
    return buildConsoleRoute('operations', 'menu');
  }
  if (pathname.includes('/manager/delivery') || pathname.includes('/delivery')) {
    return buildConsoleRoute('delivery', 'delivery');
  }
  if (pathname.includes('/system/audit') || pathname.includes('/audit-log')) {
    return buildConsoleRoute('intelligence', 'operationalHeart');
  }
  if (pathname.includes('/system/settings') || pathname.includes('/manager/settings')) {
    return buildConsoleRoute('system', 'settings');
  }
  if (pathname.includes('/intelligence') || pathname.includes('/reports')) {
    return buildConsoleRoute('intelligence', 'operationalHeart');
  }

  return domainRoutes[domain];
}

const severityMeta: Record<
  AlertSeverity,
  { label: string; chip: string; card: string; icon: typeof AlertCircle }
> = {
  critical: {
    label: 'حرج',
    chip: 'border-rose-300 bg-rose-100 text-rose-900',
    card: 'border-rose-200 bg-rose-50/70',
    icon: ShieldAlert,
  },
  warning: {
    label: 'تنبيه',
    chip: 'border-amber-300 bg-amber-100 text-amber-900',
    card: 'border-amber-200 bg-amber-50/70',
    icon: AlertTriangle,
  },
  info: {
    label: 'معلومة',
    chip: 'border-sky-300 bg-sky-100 text-sky-900',
    card: 'border-sky-200 bg-sky-50/70',
    icon: AlertCircle,
  },
};

export function ManagerAlertsPage() {
  const { notifications, unresolvedCount, operationalHeart, isLoading, isError, toggleAlertRead } = useManagerAlerts();
  const [activeDomain, setActiveDomain] = useState<DomainFilter>('all');

  const generatedAtLabel = useMemo(() => {
    if (!operationalHeart?.meta?.generated_at) {
      return 'جارٍ التحديث';
    }
    const parsed = new Date(operationalHeart.meta.generated_at);
    if (Number.isNaN(parsed.getTime())) {
      return 'جارٍ التحديث';
    }
    return parsed.toLocaleString('ar-DZ-u-nu-latn', { hour12: false });
  }, [operationalHeart?.meta?.generated_at]);

  const actionItems = useMemo(
    () =>
      notifications.flatMap((domain) =>
        domain.actions.map((action) => ({
          ...action,
          domainKey: domain.key,
          domainLabel: domain.label,
        }))
      ),
    [notifications]
  );

  const filteredActions = useMemo(() => {
    if (activeDomain === 'all') {
      return actionItems;
    }
    return actionItems.filter((action) => action.domainKey === activeDomain);
  }, [actionItems, activeDomain]);

  const sortedActions = useMemo(
    () =>
      [...filteredActions].sort((a, b) => {
        const aRead = a.isRead ? 1 : 0;
        const bRead = b.isRead ? 1 : 0;
        return aRead - bRead;
      }),
    [filteredActions]
  );

  const unreadActions = useMemo(() => filteredActions.filter((action) => !action.isRead), [filteredActions]);

  const severityCounts = useMemo(
    () =>
      unreadActions.reduce(
        (acc, item) => {
          acc[item.severity] += 1;
          return acc;
        },
        { critical: 0, warning: 0, info: 0 }
      ),
    [unreadActions]
  );

  const hasAlerts = unresolvedCount > 0 || unreadActions.length > 0;
  const hasAnyActions = filteredActions.length > 0;

  return (
    <PageShell
      className="admin-page space-y-4"
      header={
        <PageHeaderCard
          title="مركز التنبيهات التشغيلية"
          description="نظرة مركزة على الحالات التي تحتاج متابعة فورية داخل لوحة الإدارة."
          icon={<Bell className="h-5 w-5" />}
          metricsContainerClassName="flex gap-2 overflow-x-auto pb-1 md:grid md:grid-cols-3 md:overflow-visible [&>*]:min-w-[150px] md:[&>*]:min-w-0"
          actions={
            <div className="console-surface-transition rounded-xl border border-brand-100 bg-[var(--surface-card-soft)] px-3 py-2 text-xs font-semibold text-[var(--text-secondary)]">
              آخر تحديث: {generatedAtLabel}
            </div>
          }
          metrics={[
            { label: 'إجمالي التنبيهات', value: unresolvedCount },
            { label: 'حرج', value: severityCounts.critical, tone: severityCounts.critical > 0 ? 'danger' : 'default' },
            { label: 'تنبيه', value: severityCounts.warning, tone: severityCounts.warning > 0 ? 'warning' : 'default' },
          ]}
        />
      }
    >
      <section className="grid gap-4 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <div className="admin-card space-y-3 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-black text-gray-800">القنوات التشغيلية</h3>
            <span className="text-xs font-semibold text-gray-500">اختر نطاق التنبيهات</span>
          </div>

          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setActiveDomain('all')}
              className={`console-surface-transition flex w-full items-center justify-between rounded-xl border px-3 py-2 text-sm font-bold ${
                activeDomain === 'all'
                  ? 'border-brand-200 bg-brand-50 text-brand-700'
                  : 'border-gray-200 bg-white text-gray-700'
              }`}
            >
              <span>كل القنوات</span>
              <span className="text-xs font-black">{unresolvedCount}</span>
            </button>

            {notifications.map((domain) => {
              const chipTone = severityMeta[domain.severity].chip;
              return (
                <button
                  key={domain.key}
                  type="button"
                  onClick={() => setActiveDomain(domain.key)}
                  className={`console-surface-transition flex w-full items-center justify-between rounded-xl border px-3 py-2 text-sm font-bold ${
                    activeDomain === domain.key
                      ? 'border-brand-200 bg-brand-50 text-brand-700'
                      : 'border-gray-200 bg-white text-gray-700'
                  }`}
                >
                  <span>{domain.label}</span>
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] ${chipTone}`}>{domain.badge}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="admin-card space-y-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-black text-gray-800">التنبيهات القابلة للإجراء</h3>
              <p className="text-xs text-gray-600">اضغط على التنبيه للانتقال إلى المسار المرتبط.</p>
            </div>
            {activeDomain !== 'all' ? (
              <Link to={domainRoutes[activeDomain]} className="btn-secondary ui-size-sm !h-10 !px-3">
                فتح القسم
              </Link>
            ) : null}
          </div>

          {isError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
              تعذر تحميل التنبيهات في الوقت الحالي. جرّب التحديث بعد قليل.
            </div>
          ) : null}

          {isLoading ? (
            <div className="rounded-xl border border-brand-100 bg-white px-4 py-3 text-sm font-semibold text-gray-600">
              جارٍ مزامنة التنبيهات التشغيلية...
            </div>
          ) : null}

          {!hasAlerts && !isLoading && !hasAnyActions ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-5 text-sm font-semibold text-emerald-800">
              لا توجد تنبيهات مفتوحة حاليًا. النظام يعمل ضمن الحالة الطبيعية.
            </div>
          ) : null}

          {!hasAlerts && !isLoading && hasAnyActions ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-5 text-sm font-semibold text-emerald-800">
              لا توجد تنبيهات غير مقروءة حاليًا. يمكنك مراجعة التنبيهات المقروءة أدناه.
            </div>
          ) : null}

          <div className="space-y-2">
            {sortedActions.map((action) => {
              const meta = severityMeta[action.severity];
              const Icon = meta.icon;

              return (
                <div
                  key={action.id}
                  className={`console-surface-transition flex flex-wrap items-start justify-between gap-3 rounded-2xl border px-4 py-3 ${meta.card} ${action.isRead ? 'opacity-70' : ''}`}
                >
                  <div className="flex items-start gap-3">
                    <span className={`mt-1 flex h-9 w-9 items-center justify-center rounded-xl border ${meta.chip}`}>
                      <Icon className="h-4 w-4" />
                    </span>

                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-black text-gray-900">{sanitizeMojibakeText(action.title)}</p>
                        <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-[11px] font-bold text-gray-600">
                          {action.domainLabel}
                        </span>
                        {action.isRead ? (
                          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700">
                            مقروء
                          </span>
                        ) : null}
                      </div>

                      <p className="mt-1 text-xs text-gray-600">{sanitizeMojibakeText(action.detail)}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={normalizeAlertRoute(action.actionRoute, action.domainKey)} className="btn-secondary ui-size-sm !h-10 !px-3">
                      فتح المسار
                    </Link>
                    <button
                      type="button"
                      onClick={() => toggleAlertRead(action.id)}
                      className={`btn-secondary ui-size-sm !h-10 !px-3 ${action.isRead ? '!border-emerald-300 !bg-emerald-50 !text-emerald-800' : ''}`}
                    >
                      {action.isRead ? 'تحديد كغير مقروء' : 'تحديد كمقروء'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </PageShell>
  );
}
