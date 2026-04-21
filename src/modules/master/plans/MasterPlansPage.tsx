import { useQuery } from '@tanstack/react-query';
import { PauseCircle, PlayCircle, ShieldCheck } from 'lucide-react';

import { api } from '@/shared/api/client';
import { getCapabilityModeClass, getCapabilityModeLabel } from '../data/masterReadModel';

function statusBadgeClass(status: 'locked' | 'passive' | 'active' | 'paused') {
  if (status === 'active') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (status === 'passive') return 'border-sky-200 bg-sky-50 text-sky-800';
  if (status === 'paused') return 'border-amber-200 bg-amber-50 text-amber-800';
  return 'border-slate-200 bg-slate-50 text-slate-700';
}

export function MasterPlansPage() {
  const addonsQuery = useQuery({
    queryKey: ['master-addons'],
    queryFn: api.masterAddons,
  });

  if (addonsQuery.isLoading) {
    return <div className="rounded-3xl border border-[#e6edf5] bg-[#f8fbff] p-5 text-sm font-bold text-[#607080]">جارٍ تحميل الأدوات...</div>;
  }

  if (addonsQuery.isError || !addonsQuery.data) {
    const message = addonsQuery.error instanceof Error ? addonsQuery.error.message : 'تعذر تحميل الأدوات الآن.';
    return <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-700">{message}</div>;
  }

  return (
    <div className="space-y-5">
      <section className="rounded-[28px] border border-[#e6edf5] bg-white p-5 shadow-sm">
        <div className="space-y-1">
          <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">الأدوات</p>
          <h3 className="text-lg font-black text-[#1b2430]">كتالوج التفعيل والإيقاف</h3>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {addonsQuery.data.map((addon) => (
            <article key={addon.id} className="rounded-[26px] border border-[#e6edf5] bg-[#fbfdff] p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h4 className="text-lg font-black text-[#1b2430]">{addon.name}</h4>
                  <p className="mt-1 text-sm font-semibold text-[#607080]">{addon.description}</p>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-black ${statusBadgeClass(addon.status)}`}>{addon.status}</span>
              </div>

              <div className="mt-4 space-y-3 rounded-[22px] border border-[#e6edf5] bg-white p-4">
                <div className="flex items-center gap-2 text-[#405060]">
                  <ShieldCheck className="h-4 w-4 text-[#114488]" />
                  <span className="text-sm font-black">منطق التفعيل</span>
                </div>
                <p className="text-sm font-semibold text-[#607080]">{addon.unlock_note}</p>
                <p className="text-sm font-semibold text-[#607080]">{addon.target}</p>
                {addon.prerequisite_label ? (
                  <p className="text-xs font-bold text-[#6a7a8c]">يبدأ بعد: {addon.prerequisite_label}</p>
                ) : null}
              </div>

              <div className="mt-4 grid gap-2">
                {addon.capabilities.map((capability) => (
                  <div key={capability.key} className="rounded-2xl border border-[#e6edf5] bg-white px-3 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-black text-[#1b2430]">{capability.label}</p>
                      <span className={`rounded-full border px-3 py-1 text-xs font-black ${getCapabilityModeClass(capability.mode)}`}>
                        {getCapabilityModeLabel(capability.mode)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs font-semibold text-[#607080]">{capability.detail}</p>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex items-center gap-2 text-sm font-bold text-[#607080]">
                {addon.status === 'paused' ? <PauseCircle className="h-4 w-4 text-amber-700" /> : <PlayCircle className="h-4 w-4 text-emerald-700" />}
                <span>{addon.status === 'paused' ? 'الأداة موقوفة مؤقتًا مع الاحتفاظ ببياناتها.' : 'الأداة تتبع حالة النسخة الحالية.'}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
