import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Activity, BellRing, LogOut, ServerCog, ShieldCheck, Users2, type LucideIcon } from 'lucide-react';

import { api } from '@/shared/api/client';
import { useMasterAuthStore } from '../auth/masterAuthStore';
import { masterNavigationItems } from '../data/masterReadModel';

function navItemClass(isActive: boolean) {
  return [
    'inline-flex min-h-11 items-center justify-center rounded-2xl border px-4 text-sm font-black transition',
    isActive
      ? 'border-[#bfd8ff] bg-[#eef5ff] text-[#114488] shadow-sm'
      : 'border-[#e6edf5] bg-white text-[#304050] hover:border-[#bfd8ff] hover:bg-[#f7fbff]',
  ].join(' ');
}

function metricTone(tone: 'blue' | 'green' | 'amber' | 'red') {
  if (tone === 'green') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (tone === 'amber') return 'border-amber-200 bg-amber-50 text-amber-800';
  if (tone === 'red') return 'border-rose-200 bg-rose-50 text-rose-800';
  return 'border-sky-200 bg-sky-50 text-sky-800';
}

function buildHeaderMetrics(overview: Awaited<ReturnType<typeof api.masterOverview>> | undefined) {
  if (!overview) {
    return [
      { label: 'العملاء', value: '--', tone: 'blue' as const },
      { label: 'النسخ', value: '--', tone: 'green' as const },
      { label: 'المؤشرات', value: '--', tone: 'amber' as const },
      { label: 'الاستقرار', value: 'جارٍ الفحص', tone: 'blue' as const },
    ];
  }

  const watchCount = overview.signals.filter((signal) => /موقوف|معلقة|متعثرة|منخفضة|ضغط/i.test(signal.value)).length;
  return [
    {
      label: 'العملاء النشطون',
      value: overview.stats[0]?.value ?? String(overview.base_clients_count),
      tone: 'blue' as const,
    },
    {
      label: 'النسخ الجاهزة',
      value: overview.stats[1]?.value ?? '--',
      tone: 'green' as const,
    },
    {
      label: 'المؤشرات الحية',
      value: String(overview.signals.length),
      tone: watchCount > 0 ? ('amber' as const) : ('blue' as const),
    },
    {
      label: 'الاستقرار',
      value: watchCount > 0 ? 'تحت المتابعة' : 'مستقر',
      tone: watchCount > 0 ? ('amber' as const) : ('green' as const),
    },
  ];
}

export function MasterLayout() {
  const location = useLocation();
  const identity = useMasterAuthStore((state) => state.identity);
  const logout = useMasterAuthStore((state) => state.logout);

  const overviewQuery = useQuery({
    queryKey: ['master-overview-header'],
    queryFn: api.masterOverview,
  });

  const currentSection = useMemo(
    () => masterNavigationItems.find((item) => location.pathname.startsWith(item.to)) ?? masterNavigationItems[0],
    [location.pathname],
  );
  const headerMetrics = buildHeaderMetrics(overviewQuery.data);

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-[#1b2430]">
      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-30 border-b border-[#e6edf5] bg-white/95 backdrop-blur">
          <div className="px-4 py-4 lg:px-8">
            <div className="space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <div className="inline-flex h-14 w-14 items-center justify-center rounded-[22px] border border-[#dbe7f4] bg-[#eef5ff] text-[#114488]">
                    <ShieldCheck className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-xs font-black tracking-[0.22em] text-[#6a7a8c]">الإدارة المركزية</p>
                    <h1 className="mt-2 text-2xl font-black text-[#1b2430]">لوحة النظام</h1>
                    <p className="mt-1 text-sm font-semibold text-[#607080]">
                      متابعة النسخ والعملاء وتشغيل النظام الإداري من مكان واحد.
                    </p>
                  </div>
                </div>

                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  {headerMetrics.map((item) => (
                    <div
                      key={item.label}
                      className={`inline-flex min-h-[54px] min-w-[150px] items-center justify-between gap-3 rounded-2xl border px-4 py-3 ${metricTone(item.tone)}`}
                    >
                      <div>
                        <p className="text-[11px] font-black tracking-[0.16em]">{item.label}</p>
                        <p className="mt-1 text-sm font-black">{item.value}</p>
                      </div>
                      {item.label.includes('العملاء') ? (
                        <Users2 className="h-4 w-4" />
                      ) : item.label.includes('النسخ') ? (
                        <ShieldCheck className="h-4 w-4" />
                      ) : item.label.includes('الاستقرار') ? (
                        <Activity className="h-4 w-4" />
                      ) : (
                        <BellRing className="h-4 w-4" />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 rounded-[26px] border border-[#e6edf5] bg-[#f8fbff] px-4 py-3">
                <div className="min-w-0">
                  <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">القسم الحالي</p>
                  <h2 className="mt-1 text-lg font-black text-[#1b2430]">{currentSection.label}</h2>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="inline-flex min-h-11 items-center gap-2 rounded-2xl border border-[#e6edf5] bg-white px-4 text-sm font-bold text-[#506070]">
                    <ServerCog className="h-4 w-4 text-[#114488]" />
                    <span>{overviewQuery.isLoading ? 'جارٍ التحديث' : 'المؤشرات الحية جاهزة'}</span>
                  </div>
                  <div className="inline-flex min-h-11 items-center gap-2 rounded-2xl border border-[#e6edf5] bg-white px-4 text-sm font-bold text-[#506070]">
                    <Users2 className="h-4 w-4 text-[#114488]" />
                    <span>{identity?.display_name ?? 'الإدارة المركزية'}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void logout()}
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 text-sm font-black text-rose-800 transition hover:bg-rose-100"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>تسجيل الخروج</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-[#e6edf5] bg-white">
            <div className="px-4 py-3 lg:px-8">
              <nav className="flex flex-wrap items-center gap-2">
                {masterNavigationItems.map((item) => {
                  const Icon: LucideIcon = item.icon;
                  const isActive = location.pathname.startsWith(item.to);
                  return (
                    <NavLink key={item.id} to={item.to} className={navItemClass(isActive)}>
                      <span className="inline-flex items-center gap-2">
                        <Icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </span>
                    </NavLink>
                  );
                })}
              </nav>
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-5 lg:px-8 lg:py-6">
          <section className="rounded-[28px] border border-[#e6edf5] bg-white p-4 shadow-[0_18px_45px_rgba(27,36,48,0.06)] lg:p-6">
            <Outlet />
          </section>
        </main>
      </div>
    </div>
  );
}
