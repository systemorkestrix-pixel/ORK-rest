import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Layers3, PauseCircle, ShieldCheck } from 'lucide-react';

import { api } from '@/shared/api/client';
import { getCapabilityModeClass, getCapabilityModeLabel, getMasterOverviewIcon } from '../data/masterReadModel';

function sectionCardClass(tone: 'blue' | 'green' | 'amber') {
  if (tone === 'green') return 'border-emerald-200 bg-emerald-50';
  if (tone === 'amber') return 'border-amber-200 bg-amber-50';
  return 'border-sky-200 bg-sky-50';
}

export function MasterDashboardPage() {
  const overviewQuery = useQuery({
    queryKey: ['master-overview'],
    queryFn: api.masterOverview,
  });

  const addonsQuery = useQuery({
    queryKey: ['master-addons'],
    queryFn: api.masterAddons,
  });

  if (overviewQuery.isLoading || addonsQuery.isLoading) {
    return <div className="rounded-3xl border border-[#e6edf5] bg-[#f8fbff] p-5 text-sm font-bold text-[#607080]">جارٍ تحميل المتابعة...</div>;
  }

  if (overviewQuery.isError || addonsQuery.isError || !overviewQuery.data || !addonsQuery.data) {
    const error =
      (overviewQuery.error instanceof Error && overviewQuery.error.message) ||
      (addonsQuery.error instanceof Error && addonsQuery.error.message) ||
      'تعذر تحميل بيانات اللوحة الآن.';

    return <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-700">{error}</div>;
  }

  const overview = overviewQuery.data;
  const addons = addonsQuery.data;
  const activeAddon = addons.filter((addon) => addon.status === 'active').length;
  const passiveAddon = addons.filter((addon) => addon.status === 'passive').length;
  const pausedAddon = addons.filter((addon) => addon.status === 'paused').length;

  return (
    <div className="space-y-5">
      <section className="grid gap-4 lg:grid-cols-4">
        {overview.stats.map((stat) => {
          const Icon = getMasterOverviewIcon(stat.icon_key);
          return (
            <article key={stat.id} className="rounded-[24px] border border-[#e6edf5] bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-black tracking-[0.16em] text-[#6a7a8c]">{stat.label}</p>
                  <p className="mt-3 text-3xl font-black text-[#1b2430]">{stat.value}</p>
                </div>
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-[#e6edf5] bg-[#f8fbff] text-[#114488]">
                  <Icon className="h-5 w-5" />
                </span>
              </div>
              <p className="mt-4 text-sm font-semibold text-[#607080]">{stat.detail}</p>
            </article>
          );
        })}
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <section className="space-y-4 rounded-[28px] border border-[#e6edf5] bg-white p-5 shadow-sm">
          <div className="space-y-1">
            <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">المتابعة العامة</p>
            <h3 className="text-lg font-black text-[#1b2430]">وضع النظام الآن</h3>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <article className={`rounded-[22px] border p-4 ${sectionCardClass('green')}`}>
              <div className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-200 bg-white text-emerald-700">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <p className="mt-3 text-sm font-black text-emerald-900">الأدوات العاملة</p>
              <p className="mt-1 text-sm font-semibold text-emerald-800">عدد الأدوات المفعلة الآن داخل النسخ: {activeAddon}</p>
            </article>

            <article className={`rounded-[22px] border p-4 ${sectionCardClass('blue')}`}>
              <div className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-sky-200 bg-white text-sky-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <p className="mt-3 text-sm font-black text-sky-900">الأدوات الصامتة</p>
              <p className="mt-1 text-sm font-semibold text-sky-800">الأدوات التي تستقبل البيانات بصمت: {passiveAddon}</p>
            </article>

            <article className={`rounded-[22px] border p-4 ${sectionCardClass('amber')}`}>
              <div className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-amber-200 bg-white text-amber-700">
                <PauseCircle className="h-5 w-5" />
              </div>
              <p className="mt-3 text-sm font-black text-amber-900">الأدوات الموقوفة</p>
              <p className="mt-1 text-sm font-semibold text-amber-800">إيقاف مؤقت محفوظ مع الاحتفاظ بالبيانات: {pausedAddon}</p>
            </article>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {overview.signals.map((signal) => (
              <div key={signal.label} className="rounded-[22px] border border-[#e6edf5] bg-[#f8fbff] px-4 py-3">
                <p className="text-[11px] font-black tracking-[0.16em] text-[#6a7a8c]">{signal.label}</p>
                <p className="mt-2 text-sm font-bold text-[#1b2430]">{signal.value}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-4 rounded-[28px] border border-[#e6edf5] bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#dbe7f4] bg-[#eef5ff] text-[#114488]">
              <Layers3 className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">التفعيل</p>
              <h3 className="text-lg font-black text-[#1b2430]">سلسلة فتح الأدوات</h3>
            </div>
          </div>
          <div className="space-y-3">
            {addons.map((addon) => (
              <div key={addon.id} className="rounded-[22px] border border-[#e6edf5] bg-[#f8fbff] px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-black text-[#1b2430]">{addon.name}</p>
                  <span className="rounded-full border border-[#dbe7f4] bg-white px-3 py-1 text-xs font-black text-[#114488]">
                    {addon.sequence}
                  </span>
                </div>
                <p className="mt-2 text-sm font-semibold text-[#607080]">{addon.unlock_note}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-[28px] border border-[#e6edf5] bg-white p-5 shadow-sm">
        <div className="space-y-1">
          <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">كتالوج الأدوات</p>
          <h3 className="text-lg font-black text-[#1b2430]">مصوفة الحالات الحالية</h3>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          {addons.map((addon) => (
            <article key={addon.id} className="rounded-[24px] border border-[#e6edf5] bg-[#fbfdff] p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h4 className="text-base font-black text-[#1b2430]">{addon.name}</h4>
                  <p className="mt-1 text-sm font-semibold text-[#607080]">{addon.description}</p>
                </div>
                <span className="rounded-full border border-[#dbe7f4] bg-white px-3 py-1 text-xs font-black text-[#114488]">
                  {addon.status}
                </span>
              </div>

              <div className="mt-4 space-y-2">
                {addon.capabilities.map((capability) => (
                  <div key={capability.key} className="rounded-2xl border border-[#e6edf5] bg-white px-3 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-black text-[#1b2430]">{capability.label}</span>
                      <span className={`rounded-full border px-3 py-1 text-xs font-black ${getCapabilityModeClass(capability.mode)}`}>
                        {getCapabilityModeLabel(capability.mode)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs font-semibold text-[#607080]">{capability.detail}</p>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
