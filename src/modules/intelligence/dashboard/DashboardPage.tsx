import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChefHat,
  CircleDollarSign,
  ClipboardList,
  Package,
  ShieldAlert,
  ShoppingBasket,
  Truck,
} from 'lucide-react';

import { useManagerAlerts } from '@/app/navigation/ManagerAlertsContext';
import { PageHeaderCard } from '@/shared/ui/PageHeaderCard';
import { PageShell } from '@/shared/ui/PageShell';

type Severity = 'critical' | 'warning' | 'info';

function asMoney(value: number | undefined): string {
  return `${Number(value ?? 0).toFixed(2)} د.ج`;
}

function asMinutes(value: number | undefined): string {
  return `${Number(value ?? 0).toFixed(1)} د`;
}

function asAge(seconds: number | undefined): string {
  if (!seconds || seconds <= 0) return 'الآن';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} د`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours} س ${remainingMinutes} د` : `${hours} س`;
}

function buildConsoleRoute(channel: string, section: string): string {
  return `/console?channel=${channel}&section=${section}`;
}

function normalizeActionRoute(route: string | null | undefined): string {
  if (!route) return buildConsoleRoute('intelligence', 'operationalHeart');
  const url = new URL(route, 'http://localhost');
  const pathname = url.pathname;
  const params = new URLSearchParams(url.search);

  if (pathname === '/console' && params.get('channel') && params.get('section')) {
    return buildConsoleRoute(params.get('channel')!, params.get('section')!);
  }

  if (pathname.includes('/manager/warehouse') || pathname.includes('/warehouse')) {
    return buildConsoleRoute('warehouse', 'warehouseOverview');
  }
  if (pathname.includes('/manager/expenses') || pathname.includes('/expenses')) {
    return buildConsoleRoute('finance', 'financeOverview');
  }
  if (pathname.includes('/manager/financial') || pathname.includes('/finance')) {
    return buildConsoleRoute('finance', 'financeOverview');
  }
  if (pathname.includes('/manager/delivery') || pathname.includes('/delivery')) {
    return buildConsoleRoute('delivery', 'delivery');
  }
  if (pathname.includes('/manager/tables') || pathname.includes('/operations/tables')) {
    return buildConsoleRoute('operations', 'tables');
  }
  if (pathname.includes('/manager/orders') || pathname.includes('/operations/orders')) {
    return buildConsoleRoute('operations', 'orders');
  }
  if (pathname.includes('/system/settings')) {
    return buildConsoleRoute('system', 'settings');
  }
  if (pathname.includes('/system/audit') || pathname.includes('/audit-log')) {
    return buildConsoleRoute('intelligence', 'operationalHeart');
  }

  return buildConsoleRoute('intelligence', 'operationalHeart');
}

function severityMeta(severity: Severity) {
  if (severity === 'critical') {
    return {
      label: 'تحتاج تدخلًا عاجلًا',
      shell: 'border-rose-200 bg-rose-50 text-rose-900',
      icon: ShieldAlert,
    };
  }
  if (severity === 'warning') {
    return {
      label: 'تحتاج متابعة قريبة',
      shell: 'border-amber-200 bg-amber-50 text-amber-900',
      icon: AlertTriangle,
    };
  }
  return {
    label: 'تعمل ضمن النطاق الطبيعي',
    shell: 'border-sky-200 bg-sky-50 text-sky-900',
    icon: AlertCircle,
  };
}

function computeOverallSeverity(params: {
  incidentsCount: number;
  queueAgedCount: number;
  kitchenEnabled: boolean;
  deliveryEnabled: boolean;
  lowStockItems: number;
  shiftClosed: boolean;
}): Severity {
  if (
    params.incidentsCount > 0 ||
    params.queueAgedCount > 0 ||
    params.lowStockItems > 0 ||
    !params.shiftClosed ||
    !params.kitchenEnabled ||
    !params.deliveryEnabled
  ) {
    if (params.incidentsCount > 0 || params.queueAgedCount > 0 || params.lowStockItems > 0 || !params.shiftClosed) {
      return 'critical';
    }
    return 'warning';
  }
  return 'info';
}

export function DashboardPage() {
  const { operationalHeart, unresolvedCount, isLoading, isError } = useManagerAlerts();

  const derived = useMemo(() => {
    const snapshot = operationalHeart;
    const incidents = snapshot?.incidents ?? [];
    const queues = snapshot?.queues ?? [];
    const queueAgedCount = queues.reduce((sum, queue) => sum + (queue.aged_over_sla_count ?? 0), 0);
    const overallSeverity = computeOverallSeverity({
      incidentsCount: incidents.reduce((sum, item) => sum + item.count, 0),
      queueAgedCount,
      kitchenEnabled: snapshot?.capabilities.kitchen_enabled ?? true,
      deliveryEnabled: snapshot?.capabilities.delivery_enabled ?? true,
      lowStockItems: snapshot?.warehouse_control?.low_stock_items ?? 0,
      shiftClosed: snapshot?.financial_control?.shift_closed_today ?? true,
    });
    const overallMeta = severityMeta(overallSeverity);
    const generatedAt = snapshot?.meta?.generated_at
      ? new Date(snapshot.meta.generated_at).toLocaleString('ar-DZ-u-nu-latn')
      : 'غير متاح';

    return {
      overallSeverity,
      overallMeta,
      generatedAt,
      queues,
      incidents,
      timeline: snapshot?.timeline?.slice(0, 6) ?? [],
      reconciliations: snapshot?.reconciliations?.slice(0, 4) ?? [],
    };
  }, [operationalHeart]);

  const overviewCards = useMemo(
    () =>
      [
      {
        label: 'الحالة العامة',
        value: derived.overallMeta.label,
        tone: derived.overallSeverity === 'critical' ? 'danger' : derived.overallSeverity === 'warning' ? 'warning' : 'info',
      },
      { label: 'تنبيهات مفتوحة', value: unresolvedCount, tone: unresolvedCount > 0 ? 'warning' : 'success' },
      { label: 'الطلبات النشطة', value: operationalHeart?.kpis.active_orders ?? 0, tone: 'default' },
      { label: 'صافي اليوم', value: asMoney(operationalHeart?.kpis.today_net), tone: 'success' },
    ] satisfies Array<{
      label: string;
      value: string | number;
      tone?: 'default' | 'success' | 'warning' | 'danger' | 'info';
    }>,
    [derived.overallMeta.label, derived.overallSeverity, operationalHeart?.kpis.active_orders, operationalHeart?.kpis.today_net, unresolvedCount]
  );

  const domainCards = useMemo(
    () => [
      {
        key: 'kitchen',
        title: 'المطبخ',
        icon: ChefHat,
        status: operationalHeart?.capabilities.kitchen_enabled ? 'يعمل' : 'متوقف',
        detail: operationalHeart?.capabilities.kitchen_enabled
          ? `${operationalHeart?.kpis.kitchen_active_orders ?? 0} طلب داخل التحضير`
          : operationalHeart?.capabilities.kitchen_block_reason ?? 'غير متاح حاليًا',
        route: buildConsoleRoute('intelligence', 'operationalHeart'),
        severity: operationalHeart?.capabilities.kitchen_enabled ? 'info' : 'warning',
      },
      {
        key: 'delivery',
        title: 'التوصيل',
        icon: Truck,
        status: operationalHeart?.capabilities.delivery_enabled ? 'يعمل' : 'متوقف',
        detail: operationalHeart?.capabilities.delivery_enabled
          ? `${operationalHeart?.kpis.delivery_active_orders ?? 0} طلب قيد التوصيل`
          : operationalHeart?.capabilities.delivery_block_reason ?? 'غير متاح حاليًا',
        route: buildConsoleRoute('delivery', 'delivery'),
        severity: operationalHeart?.capabilities.delivery_enabled ? 'info' : 'warning',
      },
      {
        key: 'finance',
        title: 'المالية',
        icon: CircleDollarSign,
        status: operationalHeart?.financial_control?.shift_closed_today ? 'مقفلة' : 'مفتوحة',
        detail: `صافي اليوم ${asMoney(operationalHeart?.financial_control?.today_net)}`,
        route: buildConsoleRoute('finance', 'financeOverview'),
        severity: operationalHeart?.financial_control?.shift_closed_today ? 'info' : 'warning',
      },
      {
        key: 'warehouse',
        title: 'المخزون',
        icon: Package,
        status: (operationalHeart?.warehouse_control?.low_stock_items ?? 0) > 0 ? 'منخفض' : 'مستقر',
        detail: `${operationalHeart?.warehouse_control?.low_stock_items ?? 0} صنف عند حد التنبيه`,
        route: buildConsoleRoute('warehouse', 'warehouseOverview'),
        severity: (operationalHeart?.warehouse_control?.low_stock_items ?? 0) > 0 ? 'critical' : 'info',
      },
      {
        key: 'tables',
        title: 'الصالة والطاولات',
        icon: ShoppingBasket,
        status: `${operationalHeart?.tables_control?.active_sessions ?? 0} جلسة نشطة`,
        detail: `${operationalHeart?.tables_control?.unpaid_orders ?? 0} طلب غير مسدد`,
        route: buildConsoleRoute('operations', 'tables'),
        severity: (operationalHeart?.tables_control?.blocked_settlement_tables ?? 0) > 0 ? 'warning' : 'info',
      },
      {
        key: 'orders',
        title: 'التشغيل اليومي',
        icon: ClipboardList,
        status: `${operationalHeart?.kpis.ready_orders ?? 0} طلب جاهز`,
        detail: `متوسط التحضير اليوم ${asMinutes(operationalHeart?.kpis.avg_prep_minutes_today)}`,
        route: buildConsoleRoute('operations', 'orders'),
        severity: (operationalHeart?.kpis.oldest_kitchen_wait_seconds ?? 0) > 0 ? 'warning' : 'info',
      },
    ],
    [operationalHeart]
  );

  const toneClass: Record<Severity, string> = {
    critical: 'border-rose-200 bg-rose-50/80',
    warning: 'border-amber-200 bg-amber-50/80',
    info: 'border-sky-200 bg-sky-50/80',
  };

  return (
    <PageShell
      header={
        <PageHeaderCard
          title="حالة النظام"
          description="نظرة مباشرة على جاهزية المطعم اليوم: ما الذي يعمل الآن، وما الذي يحتاج متابعة، ومن أين تبدأ التدخل."
          icon={<Activity className="h-5 w-5" />}
          metrics={overviewCards}
          metricsContainerClassName="grid gap-2 sm:grid-cols-2 xl:grid-cols-4"
        />
      }
    >
      <div className="space-y-4">
        <section className={`console-surface-transition rounded-2xl border p-4 ${derived.overallMeta.shell}`}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-3">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-current/20 bg-[var(--surface-card)]/80">
                <derived.overallMeta.icon className="h-6 w-6" />
              </span>
              <div>
                <h2 className="text-lg font-black">{derived.overallMeta.label}</h2>
                <p className="mt-1 text-sm font-semibold opacity-90">
                  آخر تحديث: {derived.generatedAt}
                </p>
                <p className="mt-1 text-sm opacity-90">
                  {isLoading ? 'جارٍ مزامنة الحالة الحية...' : 'هذه القراءة تعتمد على حالة الطلبات والمطبخ والتوصيل والمالية والمخزون الآن.'}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-current/20 bg-[var(--surface-card)]/80 px-4 py-3 text-sm font-semibold">
              <p>تاريخ العمل: {operationalHeart?.meta.local_business_date ?? 'غير متاح'}</p>
              <p className="mt-1">عقد البيانات: {operationalHeart?.meta.contract_version ?? 'غير متاح'}</p>
            </div>
          </div>
        </section>

        {isError ? (
          <section className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">
            تعذر تحميل قراءة حالة النظام الآن. يمكنك متابعة الأقسام يدويًا حتى تعود المزامنة.
          </section>
        ) : null}

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {domainCards.map((card) => {
            const Icon = card.icon;
            return (
              <article key={card.key} className={`console-surface-transition rounded-2xl border p-4 ${toneClass[card.severity as Severity]}`}>
                <div className="flex items-start justify-between gap-3">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-current/15 bg-[var(--surface-card)]/80 text-current">
                    <Icon className="h-5 w-5" />
                  </span>
                  <Link to={card.route} className="btn-secondary ui-size-sm !h-10 !px-3">
                    فتح المسار
                  </Link>
                </div>
                <div className="mt-4 space-y-1">
                  <h3 className="text-sm font-black text-gray-900">{card.title}</h3>
                  <p className="text-lg font-black text-gray-900">{card.status}</p>
                  <p className="text-sm font-semibold text-gray-600">{card.detail}</p>
                </div>
              </article>
            );
          })}
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
          <section className="console-surface-transition rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-black text-gray-900">الملفات التي تحتاج متابعة</h3>
                <p className="text-sm font-semibold text-gray-600">الحالات الحية التي تؤثر على سير العمل الآن.</p>
              </div>
              <Bell className="h-5 w-5 text-[var(--text-secondary)]" />
            </div>

            <div className="mt-3 space-y-3">
              {derived.incidents.length === 0 && derived.queues.length === 0 ? (
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-5 text-sm font-semibold text-emerald-800">
                  لا توجد حالات نشطة تحتاج تدخلًا الآن.
                </div>
              ) : null}

              {derived.incidents.map((incident) => {
                const meta = severityMeta((incident.severity as Severity) || 'info');
                const Icon = meta.icon;
                return (
                  <Link
                    key={incident.code}
                    to={normalizeActionRoute(incident.action_route)}
                  className={`console-surface-transition flex flex-col gap-2 rounded-2xl border p-4 transition hover:shadow-sm ${meta.shell}`}
                >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Icon className="h-5 w-5" />
                        <span className="text-sm font-black">{incident.title}</span>
                      </div>
                      <span className="rounded-full border border-current/20 bg-[var(--surface-card)]/80 px-2 py-1 text-xs font-black">{incident.count}</span>
                    </div>
                    <p className="text-sm font-semibold opacity-90">{incident.message}</p>
                  </Link>
                );
              })}

              {derived.queues.map((queue) => {
                const severity: Severity = queue.aged_over_sla_count > 0 ? 'warning' : 'info';
                return (
                  <Link
                    key={queue.key}
                    to={normalizeActionRoute(queue.action_route)}
                    className={`console-surface-transition flex items-center justify-between gap-3 rounded-2xl border p-4 transition hover:shadow-sm ${toneClass[severity]}`}
                  >
                    <div>
                      <p className="text-sm font-black text-gray-900">{queue.label}</p>
                      <p className="text-sm font-semibold text-gray-600">
                        {queue.count} عنصر • الأقدم منذ {asAge(queue.oldest_age_seconds)}
                      </p>
                    </div>
                    <span className="rounded-full border border-current/20 bg-[var(--surface-card)]/80 px-2 py-1 text-xs font-black">
                      {queue.aged_over_sla_count} متجاوز
                    </span>
                  </Link>
                );
              })}
            </div>
          </section>

          <div className="space-y-4">
            <section className="console-surface-transition rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4">
              <h3 className="text-base font-black text-gray-900">مطابقات الرقابة</h3>
              <p className="text-sm font-semibold text-gray-600">نتيجة المطابقة بين التشغيل والمال والمخزون.</p>
              <div className="mt-3 space-y-2">
                {derived.reconciliations.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm font-semibold text-slate-600">
                    لا توجد عناصر مطابقة إضافية لعرضها الآن.
                  </div>
                ) : (
                  derived.reconciliations.map((item) => (
                    <Link
                      key={item.key}
                      to={normalizeActionRoute(item.action_route)}
                      className={`console-surface-transition block rounded-2xl border px-4 py-3 transition hover:shadow-sm ${item.ok ? 'border-emerald-200 bg-emerald-50/80' : toneClass[(item.severity as Severity) || 'warning']}`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-black text-gray-900">{item.label}</p>
                        {item.ok ? <CheckCircle2 className="h-5 w-5 text-emerald-700" /> : <AlertTriangle className="h-5 w-5 text-amber-700" />}
                      </div>
                      <p className="mt-1 text-sm font-semibold text-gray-600">{item.detail}</p>
                    </Link>
                  ))
                )}
              </div>
            </section>

            <section className="console-surface-transition rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4">
              <h3 className="text-base font-black text-gray-900">آخر الأحداث</h3>
              <p className="text-sm font-semibold text-gray-600">آخر ما تم تسجيله على الخط الزمني للتشغيل.</p>
              <div className="mt-3 space-y-3">
                {derived.timeline.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm font-semibold text-slate-600">
                    لا توجد أحداث حديثة لعرضها الآن.
                  </div>
                ) : (
                  derived.timeline.map((item, index) => (
                    <article key={`${item.timestamp}-${index}`} className="console-surface-transition rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-black text-gray-900">{item.title}</p>
                        <span className="text-xs font-bold text-gray-500">
                          {new Date(item.timestamp).toLocaleTimeString('ar-DZ-u-nu-latn', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="mt-1 text-sm font-semibold text-gray-600">{item.description}</p>
                    </article>
                  ))
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
