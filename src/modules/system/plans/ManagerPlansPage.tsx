import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  Boxes,
  ChefHat,
  CreditCard,
  FileText,
  Package2,
  Sparkles,
  Store,
  Truck,
  Wallet,
} from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { MasterAddon } from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';
import { PageHeaderCard } from '@/shared/ui/PageHeaderCard';
import { PageShell } from '@/shared/ui/PageShell';

type AddonStatus = MasterAddon['status'];
type PurchaseState = MasterAddon['purchase_state'];

const ADDON_ICON_MAP = {
  base: Store,
  kitchen: ChefHat,
  delivery: Truck,
  warehouse: Package2,
  finance: Wallet,
  intelligence: BarChart3,
  reports: FileText,
} as const;

function getAddonStatusLabel(status: AddonStatus) {
  switch (status) {
    case 'active':
      return 'تعمل الآن';
    case 'passive':
      return 'تعمل بصمت';
    case 'paused':
      return 'موقوفة مؤقتًا';
    default:
      return 'مغلقة';
  }
}

function getAddonStatusClass(status: AddonStatus) {
  switch (status) {
    case 'active':
      return 'border-emerald-300 bg-emerald-100 text-emerald-900';
    case 'passive':
      return 'border-sky-300 bg-sky-100 text-sky-900';
    case 'paused':
      return 'border-amber-300 bg-amber-100 text-amber-900';
    default:
      return 'border-stone-300 bg-stone-100 text-stone-700';
  }
}

function getPurchaseStateLabel(state: PurchaseState) {
  switch (state) {
    case 'owned':
      return 'ضمن النسخة';
    case 'next':
      return 'متاحة الآن';
    default:
      return 'لاحقًا';
  }
}

function getPurchaseStateClass(state: PurchaseState) {
  switch (state) {
    case 'owned':
      return 'border-emerald-300 bg-emerald-50 text-emerald-800';
    case 'next':
      return 'border-cyan-300 bg-cyan-50 text-cyan-800';
    default:
      return 'border-stone-300 bg-stone-50 text-stone-700';
  }
}

function getCapabilityStatusLabel(status: AddonStatus) {
  switch (status) {
    case 'active':
      return 'نشطة';
    case 'passive':
      return 'خلفية';
    case 'paused':
      return 'موقوفة';
    default:
      return 'مغلقة';
  }
}

function getCapabilityStatusClass(status: AddonStatus) {
  switch (status) {
    case 'active':
      return 'border-emerald-200 bg-emerald-50 text-emerald-800';
    case 'passive':
      return 'border-sky-200 bg-sky-50 text-sky-800';
    case 'paused':
      return 'border-amber-200 bg-amber-50 text-amber-800';
    default:
      return 'border-stone-200 bg-stone-100 text-stone-700';
  }
}

function getStatusExplanation(addon: MasterAddon) {
  switch (addon.status) {
    case 'active':
      return 'هذه الأداة مفتوحة داخل نسختك الآن، ويمكن استعمال واجهتها مباشرة.';
    case 'passive':
      return 'هذه الأداة تستقبل البيانات في الخلفية من الآن، لكن واجهتها لم تُفتح بعد داخل النسخة.';
    case 'paused':
      return 'هذه الأداة كانت مفعلة سابقًا ثم أوقفت مؤقتًا مع الاحتفاظ ببياناتها.';
    default:
      return 'هذه الأداة غير مفتوحة بعد داخل نسختك الحالية.';
  }
}

function getActivationGuidance(addon: MasterAddon) {
  if (addon.status === 'active') {
    return 'الأداة تعمل الآن ضمن النسخة الحالية.';
  }
  if (addon.can_activate_now) {
    return 'يمكنك طلب فتح هذه الأداة الآن من نفس الصفحة.';
  }
  if (addon.prerequisite_label) {
    return `يلزم فتح ${addon.prerequisite_label} أولًا قبل هذه الأداة.`;
  }
  return 'هذه الأداة مضمنة في النسخة الأساسية.';
}

function countCapabilitiesByStatus(addon: MasterAddon, status: AddonStatus) {
  return addon.capabilities.filter((capability) => capability.status === status).length;
}

export function ManagerPlansPage() {
  const role = useAuthStore((state) => state.role);
  const [selectedAddonId, setSelectedAddonId] = useState<string | null>(null);

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context'],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });

  const addonsQuery = useQuery({
    queryKey: ['manager-addons'],
    queryFn: () => api.managerAddons(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });

  const addons = addonsQuery.data ?? [];
  const currentStageName = tenantContextQuery.data?.activation_stage_name ?? 'النسخة الأساسية';
  const nextAddon = addons.find((addon) => addon.can_activate_now) ?? null;
  const selectedAddon = addons.find((addon) => addon.id === selectedAddonId) ?? null;

  const metrics = useMemo(
    () => [
      { label: 'الوضع الحالي', value: currentStageName, tone: 'info' as const },
      { label: 'الأداة التالية', value: nextAddon?.name ?? 'لا توجد أداة تالية الآن', tone: 'default' as const },
      {
        label: 'أدوات مفتوحة',
        value: addons.filter((addon) => addon.status === 'active').length,
        tone: 'success' as const,
      },
      {
        label: 'أدوات تعمل بصمت',
        value: addons.filter((addon) => addon.status === 'passive').length,
        tone: 'warning' as const,
      },
    ],
    [addons, currentStageName, nextAddon]
  );

  return (
    <PageShell
      className="admin-page"
      header={
        <PageHeaderCard
          title="الإضافات"
          description="عرض مباشر للأدوات التي تعمل داخل نسختك الآن، وما يمكن فتحه لاحقًا وفق ترتيب النظام."
          icon={<Boxes className="h-5 w-5" />}
          metrics={metrics}
          metricsContainerClassName="grid gap-2 md:grid-cols-2 xl:grid-cols-4"
        />
      }
      workspaceClassName="space-y-4"
    >
      {addonsQuery.isLoading ? (
        <section className="admin-card p-5 text-sm font-bold text-[var(--text-muted)]">جارٍ تحميل الأدوات...</section>
      ) : null}

      {addonsQuery.isError ? (
        <section className="rounded-3xl border border-rose-300 bg-rose-50 p-5 text-sm font-bold text-rose-800">
          {addonsQuery.error instanceof Error ? addonsQuery.error.message : 'تعذر تحميل الأدوات الآن.'}
        </section>
      ) : null}

      {!addonsQuery.isLoading && !addonsQuery.isError ? (
        <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {addons.map((addon) => {
            const Icon = ADDON_ICON_MAP[addon.id as keyof typeof ADDON_ICON_MAP] ?? Boxes;
            const activeCapabilities = countCapabilitiesByStatus(addon, 'active');
            const passiveCapabilities = countCapabilitiesByStatus(addon, 'passive');

            return (
              <article
                key={addon.id}
                className="rounded-[28px] border border-[var(--console-border)] bg-[var(--surface-card)] p-4 shadow-[0_16px_30px_rgba(0,0,0,0.08)]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)]">
                      <Icon className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <h3 className="text-base font-black text-[var(--text-primary-strong)]">{addon.name}</h3>
                      <p className="mt-1 line-clamp-2 text-sm font-semibold text-[var(--text-muted)]">{addon.description}</p>
                    </div>
                  </div>

                  <span className={`shrink-0 rounded-full border px-3 py-1 text-[11px] font-black ${getAddonStatusClass(addon.status)}`}>
                    {getAddonStatusLabel(addon.status)}
                  </span>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className={`rounded-full border px-3 py-1 text-xs font-black ${getPurchaseStateClass(addon.purchase_state)}`}>
                    {getPurchaseStateLabel(addon.purchase_state)}
                  </span>
                  {addon.can_activate_now ? (
                    <span className="rounded-full border border-cyan-300 bg-cyan-100 px-3 py-1 text-xs font-black text-cyan-900">
                      متاحة للفتح
                    </span>
                  ) : null}
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3">
                    <p className="text-[11px] font-black tracking-[0.14em] text-[var(--text-muted)]">مكونات نشطة</p>
                    <p className="mt-2 text-xl font-black text-[var(--text-primary-strong)]">{activeCapabilities}</p>
                  </div>
                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3">
                    <p className="text-[11px] font-black tracking-[0.14em] text-[var(--text-muted)]">خلفية صامتة</p>
                    <p className="mt-2 text-xl font-black text-[var(--text-primary-strong)]">{passiveCapabilities}</p>
                  </div>
                </div>

                <div className="mt-4 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3 text-sm font-semibold text-[var(--text-primary)]">
                  {getActivationGuidance(addon)}
                </div>

                <div className="mt-4 flex justify-end">
                  <button type="button" className="btn-secondary ui-size-sm px-4" onClick={() => setSelectedAddonId(addon.id)}>
                    التفاصيل
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      ) : null}

      <Modal
        open={selectedAddon !== null}
        onClose={() => setSelectedAddonId(null)}
        title={selectedAddon?.name ?? 'تفاصيل الأداة'}
        description={selectedAddon ? getStatusExplanation(selectedAddon) : undefined}
        headerActions={
          selectedAddon ? (
            <span className={`rounded-full border px-3 py-1 text-xs font-black ${getAddonStatusClass(selectedAddon.status)}`}>
              {getAddonStatusLabel(selectedAddon.status)}
            </span>
          ) : null
        }
      >
        {selectedAddon ? (
          <div className="space-y-4">
            <section className="grid gap-4 lg:grid-cols-[1.3fr_0.9fr]">
              <div className="rounded-[24px] border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
                <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">ما الذي تضيفه</p>
                <p className="mt-3 text-sm font-bold leading-7 text-[var(--text-primary)]">{selectedAddon.description}</p>
                <p className="mt-3 text-sm font-semibold leading-7 text-[var(--text-muted)]">{selectedAddon.target}</p>
              </div>

              <div className="rounded-[24px] border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
                <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">وضع الأداة</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className={`rounded-full border px-3 py-1 text-xs font-black ${getAddonStatusClass(selectedAddon.status)}`}>
                    {getAddonStatusLabel(selectedAddon.status)}
                  </span>
                  <span className={`rounded-full border px-3 py-1 text-xs font-black ${getPurchaseStateClass(selectedAddon.purchase_state)}`}>
                    {getPurchaseStateLabel(selectedAddon.purchase_state)}
                  </span>
                </div>
                <p className="mt-3 text-sm font-semibold leading-7 text-[var(--text-primary)]">{getActivationGuidance(selectedAddon)}</p>
              </div>
            </section>

            {selectedAddon.status === 'passive' ? (
              <section className="rounded-[24px] border border-sky-300 bg-sky-50 p-4 text-sm font-bold leading-7 text-sky-900">
                هذه الأداة تبني بياناتك في الخلفية من الآن. عند فتحها لاحقًا ستجد سجلك التاريخي حاضرًا داخلها مباشرة.
              </section>
            ) : null}

            {selectedAddon.prerequisite_label && selectedAddon.purchase_state === 'later' ? (
              <section className="rounded-[24px] border border-stone-300 bg-stone-50 p-4 text-sm font-bold leading-7 text-stone-800">
                يجب فتح <span className="font-black">{selectedAddon.prerequisite_label}</span> قبل الوصول إلى هذه الأداة.
              </section>
            ) : null}

            <section className="rounded-[24px] border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-[var(--text-secondary)]" />
                <p className="text-sm font-black text-[var(--text-primary)]">مكونات الأداة</p>
              </div>

              <div className="mt-4 space-y-3">
                {selectedAddon.capabilities.map((capability) => (
                  <div
                    key={capability.key}
                    className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3 py-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-black text-[var(--text-primary-strong)]">{capability.label}</p>
                        <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">{capability.detail}</p>
                      </div>
                      <span className={`rounded-full border px-3 py-1 text-[11px] font-black ${getCapabilityStatusClass(capability.status)}`}>
                        {getCapabilityStatusLabel(capability.status)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {selectedAddon.can_activate_now ? (
              <section className="rounded-[24px] border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
                <div className="flex items-center gap-2">
                  <CreditCard className="h-4 w-4 text-[var(--text-secondary)]" />
                  <p className="text-sm font-black text-[var(--text-primary)]">فتح الأداة</p>
                </div>
                <p className="mt-3 text-sm font-semibold leading-7 text-[var(--text-primary)]">
                  اختر طريقة الفتح المناسبة. سيتم تمرير اسم الأداة والنسخة الحالية ضمن الطلب لتجهيز التفعيل بشكل مباشر.
                </p>

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <a
                    href={selectedAddon.paypal_checkout_url ?? '#'}
                    target={selectedAddon.paypal_checkout_url ? '_blank' : undefined}
                    rel={selectedAddon.paypal_checkout_url ? 'noreferrer' : undefined}
                    className={`flex min-h-[108px] flex-col justify-between rounded-[24px] border p-4 ${
                      selectedAddon.paypal_checkout_url
                        ? 'border-sky-300 bg-sky-50 text-sky-950'
                        : 'cursor-not-allowed border-stone-300 bg-stone-100 text-stone-500'
                    }`}
                  >
                    <div className="space-y-2">
                      <p className="text-sm font-black">PayPal</p>
                      <p className="text-xs font-semibold leading-6">
                        {selectedAddon.paypal_checkout_url
                          ? 'فتح مسار الدفع الإلكتروني المباشر لهذه الأداة.'
                          : 'رابط PayPal غير مضبوط بعد داخل إعدادات المنصة.'}
                      </p>
                    </div>
                    <span className="text-xs font-black">{selectedAddon.paypal_checkout_url ? 'فتح الدفع' : 'غير متاح الآن'}</span>
                  </a>

                  <a
                    href={selectedAddon.telegram_checkout_url ?? '#'}
                    target={selectedAddon.telegram_checkout_url ? '_blank' : undefined}
                    rel={selectedAddon.telegram_checkout_url ? 'noreferrer' : undefined}
                    className={`flex min-h-[108px] flex-col justify-between rounded-[24px] border p-4 ${
                      selectedAddon.telegram_checkout_url
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                        : 'cursor-not-allowed border-stone-300 bg-stone-100 text-stone-500'
                    }`}
                  >
                    <div className="space-y-2">
                      <p className="text-sm font-black">Telegram</p>
                      <p className="text-xs font-semibold leading-6">
                        {selectedAddon.telegram_checkout_url
                          ? 'التواصل المحلي أو الإقليمي لفتح الأداة من خلال Telegram.'
                          : 'رابط Telegram التجاري غير مضبوط بعد داخل إعدادات المنصة.'}
                      </p>
                    </div>
                    <span className="text-xs font-black">{selectedAddon.telegram_checkout_url ? 'فتح المحادثة' : 'غير متاح الآن'}</span>
                  </a>
                </div>
              </section>
            ) : null}

            {selectedAddon.status === 'active' ? (
              <section className="rounded-[24px] border border-emerald-300 bg-emerald-50 p-4 text-sm font-bold leading-7 text-emerald-900">
                هذه الأداة مفعلة الآن ضمن نسختك. إذا فقدت الوصول إلى أداة تشغيلية مرتبطة بها، ستجد إعداداتها داخل القناة الخاصة بها.
              </section>
            ) : null}

            {selectedAddon.status === 'locked' && !selectedAddon.can_activate_now ? (
              <section className="rounded-[24px] border border-stone-300 bg-stone-50 p-4 text-sm font-bold leading-7 text-stone-800">
                ستبقى هذه الأداة مغلقة حتى تصل النسخة إلى ترتيب الفتح المطلوب لها.
              </section>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </PageShell>
  );
}
