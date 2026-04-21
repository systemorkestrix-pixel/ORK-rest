import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { LockKeyhole, ShieldCheck, UserRound } from 'lucide-react';

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

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

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
    <div className="min-h-screen bg-transparent text-[var(--app-text)]">
      <div className="mx-auto grid min-h-screen w-full max-w-6xl items-center gap-8 px-4 py-8 lg:grid-cols-[minmax(0,1.15fr)_440px] lg:px-8">
        <section className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#dbe7f4] bg-[#eef5ff] px-4 py-2 text-sm font-bold text-[#114488]">
            <ShieldCheck className="h-4 w-4" />
            <span>الإدارة المركزية</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl font-black leading-tight text-[var(--app-text)] sm:text-4xl lg:text-5xl">
              إدارة العملاء والنسخ من لوحة موحدة وواضحة
            </h1>
            <p className="max-w-2xl text-sm font-semibold leading-7 text-slate-200/90 sm:text-base">
              هذه الجلسة مستقلة بالكامل عن جلسات المطاعم. من هنا تتم متابعة العملاء، إنشاء النسخ، والتحكم في التفعيل التشغيلي من مكان واحد.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <article className="rounded-3xl border border-[#e6edf5] bg-white p-4 shadow-sm">
              <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">العملاء</p>
              <p className="mt-3 text-sm font-bold text-[#1b2430]">سجل واضح لكل عميل وربطه بنسخته الحالية.</p>
            </article>
            <article className="rounded-3xl border border-[#e6edf5] bg-white p-4 shadow-sm">
              <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">النسخ</p>
              <p className="mt-3 text-sm font-bold text-[#1b2430]">كل مطعم يعمل على نسخة مستقلة ومحكومة.</p>
            </article>
            <article className="rounded-3xl border border-[#e6edf5] bg-white p-4 shadow-sm">
              <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">التفعيل</p>
              <p className="mt-3 text-sm font-bold text-[#1b2430]">فتح الأدوات وإيقافها يتم ضمن مسار واحد منضبط.</p>
            </article>
          </div>
        </section>

        <section className="rounded-[32px] border border-[#e6edf5] bg-white p-6 shadow-[0_24px_60px_rgba(27,36,48,0.08)] sm:p-7">
          <div className="space-y-2">
            <div className="inline-flex h-14 w-14 items-center justify-center rounded-3xl border border-[#dbe7f4] bg-[#eef5ff] text-[#114488]">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-black text-[#1b2430]">دخول الإدارة المركزية</h2>
            <p className="text-sm font-semibold text-[#607080]">أدخل بيانات الحساب المركزي للوصول إلى لوحة التحكم.</p>
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-bold text-[#405060]">اسم المستخدم</span>
              <span className="relative block">
                <UserRound className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8092a5]" />
                <input
                  dir="ltr"
                  className="h-12 w-full rounded-2xl border border-[#d9e3ef] bg-[#fbfdff] pr-11 pl-4 text-sm font-semibold text-[#1b2430] outline-none transition placeholder:text-[#90a2b4] focus:border-[#9dbdf0] focus:bg-white"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="username"
                  required
                />
              </span>
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-bold text-[#405060]">كلمة المرور</span>
              <span className="relative block">
                <LockKeyhole className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8092a5]" />
                <input
                  dir="ltr"
                  type="password"
                  className="h-12 w-full rounded-2xl border border-[#d9e3ef] bg-[#fbfdff] pr-11 pl-4 text-sm font-semibold text-[#1b2430] outline-none transition placeholder:text-[#90a2b4] focus:border-[#9dbdf0] focus:bg-white"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="password"
                  required
                />
              </span>
            </label>

            {loginError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
                {loginError}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={status === 'checking'}
              className="inline-flex h-12 w-full items-center justify-center rounded-2xl bg-[#114488] px-4 text-sm font-black text-white transition hover:bg-[#0f3c77] disabled:cursor-wait disabled:opacity-70"
            >
              {status === 'checking' ? 'جارٍ التحقق...' : 'دخول'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
