import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { LockKeyhole, ShieldCheck, Sparkles, UserRound } from 'lucide-react';

import { masterInitialAccess } from '../data/masterReadModel';
import { useMasterAuthStore } from './masterAuthStore';

export function MasterLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const identity = useMasterAuthStore((state) => state.identity);
  const login = useMasterAuthStore((state) => state.login);
  const loginError = useMasterAuthStore((state) => state.loginError);
  const clearLoginError = useMasterAuthStore((state) => state.clearLoginError);
  const status = useMasterAuthStore((state) => state.status);
  const hydrateSession = useMasterAuthStore((state) => state.hydrateSession);
  const [username, setUsername] = useState(masterInitialAccess.username);
  const [password, setPassword] = useState(masterInitialAccess.password);

  useEffect(() => {
    if (status === 'idle') {
      void hydrateSession();
    }
  }, [hydrateSession, status]);

  const redirectTarget = useMemo(() => {
    const state = location.state as { from?: string } | null;
    const params = new URLSearchParams(location.search);
    return state?.from || params.get('from') || '/master/dashboard';
  }, [location.search, location.state]);

  if (identity) {
    return <Navigate to={redirectTarget} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearLoginError();
    const success = await login({ username, password });
    if (success) {
      navigate(redirectTarget, { replace: true });
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(13,148,136,0.18),_transparent_28%),radial-gradient(circle_at_bottom,_rgba(8,47,73,0.38),_transparent_36%),linear-gradient(160deg,_#07111f_0%,_#091728_52%,_#030711_100%)] text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-center gap-8 px-4 py-8 lg:grid lg:grid-cols-[minmax(0,1.2fr)_minmax(420px,0.9fr)] lg:items-center lg:px-8">
        <section className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-bold text-emerald-200 backdrop-blur">
            <ShieldCheck className="h-4 w-4" />
            <span>اللوحة الأم</span>
          </div>
          <div className="space-y-3">
            <h1 className="text-3xl font-black leading-tight text-white sm:text-4xl lg:text-5xl">
              إدارة العملاء والنسخ والإضافات من لوحة مستقلة
            </h1>
            <p className="max-w-2xl text-sm font-semibold leading-7 text-slate-300 sm:text-base">
              هذه الجلسة مستقلة عن أي لوحة مطعم. من هنا نتابع العملاء، ننشئ النسخ، ونفتح الأدوات لكل مطعم بالترتيب الصحيح.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <article className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur">
              <p className="text-xs font-black tracking-[0.18em] text-emerald-200">العملاء</p>
              <p className="mt-3 text-sm font-bold text-white">سجل مركزي واضح لكل عميل ونسخته الحالية.</p>
            </article>
            <article className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur">
              <p className="text-xs font-black tracking-[0.18em] text-cyan-200">النسخ</p>
              <p className="mt-3 text-sm font-bold text-white">كل مطعم يعمل ضمن Tenant مستقل.</p>
            </article>
            <article className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur">
              <p className="text-xs font-black tracking-[0.18em] text-violet-200">التفعيل</p>
              <p className="mt-3 text-sm font-bold text-white">الأدوات تُفتح على النسخة بشكل مرتب ومنضبط.</p>
            </article>
          </div>
        </section>

        <section className="rounded-[32px] border border-white/10 bg-slate-950/55 p-5 shadow-[0_28px_120px_rgba(0,0,0,0.35)] backdrop-blur sm:p-7">
          <div className="space-y-2">
            <div className="inline-flex h-14 w-14 items-center justify-center rounded-3xl border border-emerald-400/30 bg-emerald-400/10 text-emerald-200">
              <Sparkles className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-black text-white">دخول الإدارة المركزية</h2>
            <p className="text-sm font-semibold text-slate-300">جلسة منفصلة بالكامل عن جلسات المطاعم.</p>
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-bold text-slate-200">اسم الدخول</span>
              <span className="relative block">
                <UserRound className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  dir="ltr"
                  className="h-12 w-full rounded-2xl border border-white/10 bg-white/5 pr-11 pl-4 text-sm font-semibold text-white outline-none transition placeholder:text-slate-500 focus:border-emerald-400/60 focus:bg-white/[0.07]"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="owner@master.local"
                />
              </span>
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-bold text-slate-200">كلمة المرور</span>
              <span className="relative block">
                <LockKeyhole className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  dir="ltr"
                  type="password"
                  className="h-12 w-full rounded-2xl border border-white/10 bg-white/5 pr-11 pl-4 text-sm font-semibold text-white outline-none transition placeholder:text-slate-500 focus:border-emerald-400/60 focus:bg-white/[0.07]"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Master@2026!"
                />
              </span>
            </label>

            {loginError ? (
              <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm font-bold text-rose-200">
                {loginError}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={status === 'checking'}
              className="inline-flex h-12 w-full items-center justify-center rounded-2xl bg-gradient-to-l from-emerald-500 to-cyan-500 px-4 text-sm font-black text-slate-950 transition hover:from-emerald-400 hover:to-cyan-400 disabled:cursor-wait disabled:opacity-70"
            >
              {status === 'checking' ? 'جارٍ التحقق...' : 'دخول اللوحة الأم'}
            </button>
          </form>

          <div className="mt-5 rounded-3xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs font-black tracking-[0.18em] text-slate-400">الوصول الأولي</p>
            <div className="mt-3 space-y-2 text-sm font-semibold text-slate-200">
              <p>
                <span className="text-slate-400">المسار:</span> <span dir="ltr">{masterInitialAccess.route}</span>
              </p>
              <p>
                <span className="text-slate-400">اسم الدخول:</span> <span dir="ltr">{masterInitialAccess.username}</span>
              </p>
              <p>
                <span className="text-slate-400">كلمة المرور:</span> <span dir="ltr">{masterInitialAccess.password}</span>
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
