import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, CircleSlash2, Layers3 } from 'lucide-react';

import { api } from '@/shared/api/client';
import { getCapabilityModeClass, getCapabilityModeLabel, getMasterOverviewIcon, getMasterToneClasses } from '../data/masterReadModel';

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
    return <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-sm font-bold text-slate-300">جارٍ تحميل المتابعة...</div>;
  }

  if (overviewQuery.isError || addonsQuery.isError || !overviewQuery.data || !addonsQuery.data) {
    const error =
      (overviewQuery.error instanceof Error && overviewQuery.error.message) ||
      (addonsQuery.error instanceof Error && addonsQuery.error.message) ||
      'تعذر تحميل بيانات اللوحة الأم الآن.';

    return <div className="rounded-3xl border border-rose-400/30 bg-rose-500/10 p-5 text-sm font-bold text-rose-100">{error}</div>;
  }

  const overview = overviewQuery.data;
  const addons = addonsQuery.data;

  return (
    <div className="space-y-5">
      <section className="grid gap-4 lg:grid-cols-4">
        {overview.stats.map((stat) => {
          const Icon = getMasterOverviewIcon(stat.icon_key);
          return (
            <article
              key={stat.id}
              className={`rounded-[26px] border border-white/10 bg-gradient-to-l p-4 shadow-[0_22px_65px_rgba(0,0,0,0.24)] ${getMasterToneClasses(stat.tone)}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-black tracking-[0.18em] text-white/70">{stat.label}</p>
                  <p className="mt-3 text-3xl font-black text-white">{stat.value}</p>
                </div>
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-3xl border border-white/10 bg-white/10 text-current">
                  <Icon className="h-5 w-5" />
                </span>
              </div>
              <p className="mt-4 text-sm font-semibold text-white/80">{stat.detail}</p>
            </article>
          );
        })}
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <section className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
          <div className="grid gap-3 md:grid-cols-2">
            <article className="rounded-3xl border border-emerald-400/25 bg-emerald-500/10 p-4">
              <div className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-400/25 bg-emerald-500/15 text-emerald-100">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <h4 className="mt-3 text-sm font-black text-white">مفعّل داخل النسخة</h4>
              <p className="mt-1 text-sm font-semibold text-emerald-100/90">أدوات يراها صاحب المطعم مباشرة داخل نسخته.</p>
            </article>
            <article className="rounded-3xl border border-amber-400/25 bg-amber-500/10 p-4">
              <div className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-amber-400/25 bg-amber-500/15 text-amber-100">
                <CircleSlash2 className="h-5 w-5" />
              </div>
              <h4 className="mt-3 text-sm font-black text-white">مغلق حتى التفعيل</h4>
              <p className="mt-1 text-sm font-semibold text-amber-100/90">أدوات لا تدخل دورة المطعم قبل فتحها من اللوحة الأم.</p>
            </article>
          </div>

          <div className="mt-5 rounded-[26px] border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-black tracking-[0.18em] text-cyan-200">الإشارات</p>
                <h4 className="mt-1 text-base font-black text-white">الوضع الحالي</h4>
              </div>
              <span className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-sm font-black text-cyan-100">
                {overview.base_clients_count}
              </span>
            </div>
            <div className="mt-4 space-y-3">
              {overview.signals.map((signal) => (
                <div key={signal.label} className="rounded-2xl border border-white/10 bg-slate-950/55 px-4 py-3">
                  <p className="text-xs font-black tracking-[0.18em] text-slate-400">{signal.label}</p>
                  <p className="mt-1 text-sm font-bold text-white">{signal.value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <article className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-3xl border border-violet-400/25 bg-violet-500/10 text-violet-100">
                <Layers3 className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs font-black tracking-[0.18em] text-violet-200">الترتيب</p>
                <h3 className="text-lg font-black text-white">سلسلة فتح الأدوات</h3>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              {addons.map((addon) => (
                <div key={addon.id} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-black text-white">{addon.name}</p>
                    <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs font-black text-cyan-100">
                      #{addon.sequence}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-slate-300">{addon.unlock_note}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
            <p className="text-xs font-black tracking-[0.18em] text-emerald-200">آخر النسخ</p>
            <h3 className="mt-1 text-lg font-black text-white">أحدث السجلات</h3>
            <div className="mt-4 space-y-3">
              {overview.latest_tenants.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm font-semibold text-slate-400">
                  لا توجد نسخ بعد.
                </div>
              ) : (
                overview.latest_tenants.map((tenant) => (
                  <div key={tenant.tenant_id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                    <p className="text-sm font-black text-white">{tenant.brand_name}</p>
                    <p className="mt-1 text-xs font-semibold text-slate-400" dir="ltr">
                      {tenant.code}
                    </p>
                    <p className="mt-2 text-sm font-semibold text-cyan-100">{tenant.activation_stage_name}</p>
                  </div>
                ))
              )}
            </div>
          </article>
        </section>
      </div>

      <section className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
        <div className="space-y-1">
          <p className="text-xs font-black tracking-[0.18em] text-cyan-200">الإضافات</p>
          <h3 className="text-lg font-black text-white">مصفوفة الأدوات</h3>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          {addons.map((addon) => (
            <article key={addon.id} className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h4 className="text-base font-black text-white">{addon.name}</h4>
                  <p className="text-sm font-semibold text-slate-300">{addon.description}</p>
                </div>
                <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-sm font-black text-cyan-100">
                  #{addon.sequence}
                </span>
              </div>
              <div className="mt-4 space-y-2">
                {addon.capabilities.map((capability) => (
                  <div key={capability.key} className="rounded-2xl border border-white/10 bg-slate-950/55 px-3 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-black text-white">{capability.label}</span>
                      <span className={`rounded-full border px-3 py-1 text-xs font-black ${getCapabilityModeClass(capability.mode)}`}>
                        {getCapabilityModeLabel(capability.mode)}
                      </span>
                    </div>
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
