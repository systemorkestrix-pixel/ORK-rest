import { useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  BellRing,
  LogOut,
  PanelRightOpen,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

import { masterHighlights, masterNavigationItems } from '../data/masterReadModel';
import { useMasterAuthStore } from '../auth/masterAuthStore';

function navItemClass(isActive: boolean) {
  return [
    'group flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-sm font-bold transition',
    isActive
      ? 'border-emerald-400/40 bg-emerald-400/10 text-white shadow-[0_18px_45px_rgba(16,185,129,0.16)]'
      : 'border-white/10 bg-white/[0.03] text-slate-300 hover:border-cyan-400/35 hover:bg-cyan-400/10 hover:text-white',
  ].join(' ');
}

function sectionTone(index: number) {
  const tones = [
    'from-cyan-500/18 to-cyan-500/6 text-cyan-100',
    'from-emerald-500/18 to-emerald-500/6 text-emerald-100',
    'from-violet-500/18 to-violet-500/6 text-violet-100',
    'from-amber-500/18 to-amber-500/6 text-amber-100',
  ];
  return tones[index % tones.length];
}

export function MasterLayout() {
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const identity = useMasterAuthStore((state) => state.identity);
  const logout = useMasterAuthStore((state) => state.logout);

  const currentSection = useMemo(
    () => masterNavigationItems.find((item) => location.pathname.startsWith(item.to)) ?? masterNavigationItems[0],
    [location.pathname]
  );

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(8,145,178,0.16),_transparent_30%),radial-gradient(circle_at_bottom,_rgba(15,23,42,0.64),_transparent_38%),linear-gradient(155deg,_#020712_0%,_#08111f_52%,_#03060d_100%)] text-slate-100">
      <div className="min-h-screen lg:grid lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside
          className={`fixed inset-y-0 right-0 z-40 w-[88vw] max-w-[320px] border-l border-white/10 bg-slate-950/92 p-4 shadow-[0_20px_100px_rgba(0,0,0,0.5)] backdrop-blur transition-transform duration-200 lg:static lg:w-auto lg:max-w-none lg:translate-x-0 lg:bg-slate-950/70 lg:p-5 lg:shadow-none ${
            navOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-start justify-between gap-3 border-b border-white/10 pb-4">
              <div className="space-y-2">
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-3xl border border-cyan-400/30 bg-cyan-400/10 text-cyan-200">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-black tracking-[0.22em] text-cyan-200">MASTER CONTROL</p>
                  <h1 className="text-xl font-black text-white">اللوحة الأم</h1>
                  <p className="text-xs font-semibold text-slate-400">العملاء والنسخ والإضافات في مكان واحد.</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setNavOpen(false)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-slate-300 lg:hidden"
                aria-label="إغلاق التنقل"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            </div>

            <nav className="mt-5 space-y-2">
              {masterNavigationItems.map((item) => {
                const Icon: LucideIcon = item.icon;
                const isActive = location.pathname.startsWith(item.to);
                return (
                  <NavLink key={item.id} to={item.to} className={navItemClass(isActive)} onClick={() => setNavOpen(false)}>
                    <span className="flex items-center gap-3">
                      <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-current">
                        <Icon className="h-4 w-4" />
                      </span>
                      <span>{item.label}</span>
                    </span>
                    <ArrowLeft className="h-4 w-4 opacity-60 transition group-hover:opacity-100" />
                  </NavLink>
                );
              })}
            </nav>

            <div className="mt-6 space-y-3">
              {masterHighlights.map((highlight, index) => (
                <article key={highlight.label} className={`rounded-3xl border border-white/10 bg-gradient-to-l px-4 py-4 ${sectionTone(index)}`}>
                  <p className="text-[11px] font-black tracking-[0.18em] text-slate-200/90">{highlight.label}</p>
                  <p className="mt-2 text-sm font-bold text-white">{highlight.value}</p>
                </article>
              ))}
            </div>

            <div className="mt-auto rounded-3xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs font-black tracking-[0.18em] text-slate-400">الجلسة الحالية</p>
              <p className="mt-2 text-base font-black text-white">{identity?.display_name ?? 'الإدارة المركزية'}</p>
              <p className="text-sm font-semibold text-slate-400" dir="ltr">
                {identity?.username ?? 'owner@master.local'}
              </p>
              <button
                type="button"
                onClick={() => void logout()}
                className="mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 text-sm font-black text-rose-100 transition hover:border-rose-300/40 hover:bg-rose-500/15"
              >
                <LogOut className="h-4 w-4" />
                <span>تسجيل الخروج</span>
              </button>
            </div>
          </div>
        </aside>

        <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/65 px-4 py-4 backdrop-blur lg:px-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setNavOpen(true)}
                  className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-slate-200 lg:hidden"
                  aria-label="إظهار التنقل"
                >
                  <PanelRightOpen className="h-5 w-5" />
                </button>
                <div className="space-y-1">
                  <p className="text-xs font-black tracking-[0.22em] text-cyan-200">SAAS CONTROL PLANE</p>
                  <h2 className="text-xl font-black text-white">{currentSection.label}</h2>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="hidden rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 sm:block">
                  <p className="text-[11px] font-black tracking-[0.18em] text-slate-400">الوضع الحالي</p>
                  <p className="text-sm font-bold text-white">إدارة العملاء والنسخ والإضافات</p>
                </div>
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-400/30 bg-emerald-400/10 text-emerald-200">
                  <BellRing className="h-5 w-5" />
                </div>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-5 lg:px-8 lg:py-6">
            <section className="rounded-[28px] border border-white/10 bg-white/[0.03] p-4 shadow-[0_28px_100px_rgba(0,0,0,0.32)] backdrop-blur lg:p-6">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-white/10 bg-gradient-to-l from-emerald-500/10 via-cyan-500/8 to-transparent px-4 py-4">
                <div className="space-y-1">
                  <p className="text-xs font-black tracking-[0.2em] text-emerald-200">النسخة الأولى</p>
                  <h3 className="text-lg font-black text-white">فصل كامل بين اللوحة الأم ولوحة المطعم</h3>
                </div>
                <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-sm font-black text-cyan-100">
                  <Sparkles className="h-4 w-4" />
                  <span>منتج إداري مستقل</span>
                </div>
              </div>

              <Outlet />
            </section>
          </main>
        </div>
      </div>

      <button
        type="button"
        aria-label="إغلاق التنقل"
        onClick={() => setNavOpen(false)}
        className={`fixed inset-0 z-30 bg-slate-950/60 transition-opacity lg:hidden ${navOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
      />
    </div>
  );
}
