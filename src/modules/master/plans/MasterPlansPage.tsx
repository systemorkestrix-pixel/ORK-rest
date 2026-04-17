import { useQuery } from '@tanstack/react-query';

import { api } from '@/shared/api/client';
import { getCapabilityModeClass, getCapabilityModeLabel } from '../data/masterReadModel';

export function MasterPlansPage() {
  const addonsQuery = useQuery({
    queryKey: ['master-addons'],
    queryFn: api.masterAddons,
  });

  if (addonsQuery.isLoading) {
    return <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-sm font-bold text-slate-300">جارٍ تحميل الإضافات...</div>;
  }

  if (addonsQuery.isError || !addonsQuery.data) {
    const message = addonsQuery.error instanceof Error ? addonsQuery.error.message : 'تعذر تحميل الإضافات الآن.';
    return <div className="rounded-3xl border border-rose-400/30 bg-rose-500/10 p-5 text-sm font-bold text-rose-100">{message}</div>;
  }

  return (
    <div className="space-y-5">
      <section className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
        <div className="space-y-1">
          <p className="text-xs font-black tracking-[0.18em] text-cyan-200">الإضافات</p>
          <h3 className="text-lg font-black text-white">كتالوج الأدوات المرتبة</h3>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {addonsQuery.data.map((addon) => (
            <article key={addon.id} className="rounded-[26px] border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h4 className="text-lg font-black text-white">{addon.name}</h4>
                  <p className="mt-1 text-sm font-semibold text-slate-300">{addon.description}</p>
                </div>
                <span className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-sm font-black text-cyan-100">
                  #{addon.sequence}
                </span>
              </div>

              <div className="mt-4 rounded-3xl border border-white/10 bg-slate-950/55 p-4">
                <p className="text-xs font-black tracking-[0.18em] text-slate-400">الفتح</p>
                <p className="mt-2 text-sm font-bold text-white">{addon.unlock_note}</p>
                <p className="mt-2 text-sm font-semibold text-slate-300">{addon.target}</p>
              </div>

              {addon.prerequisite_label ? (
                <div className="mt-4 rounded-3xl border border-white/10 bg-slate-950/55 p-4">
                  <p className="text-xs font-black tracking-[0.18em] text-slate-400">الشرط السابق</p>
                  <p className="mt-2 text-sm font-bold text-white">{addon.prerequisite_label}</p>
                </div>
              ) : null}

              <div className="mt-4 space-y-2">
                {addon.capabilities.map((capability) => (
                  <div key={capability.key} className="rounded-2xl border border-white/10 bg-slate-950/55 px-3 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-black text-white">{capability.label}</p>
                      <span className={`rounded-full border px-3 py-1 text-xs font-black ${getCapabilityModeClass(capability.mode)}`}>
                        {getCapabilityModeLabel(capability.mode)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs font-semibold text-slate-400">{capability.detail}</p>
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
