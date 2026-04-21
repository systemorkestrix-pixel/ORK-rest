import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Store } from 'lucide-react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import { api } from '@/shared/api/client';
import type { UserRole } from '@/shared/api/types';
import { useAuthStore } from '../store';

interface LoginPageProps {
  role: UserRole;
}

function resolveRoleTitle(role: UserRole): string {
  if (role === 'manager') {
    return 'دخول الإدارة';
  }
  if (role === 'kitchen') {
    return 'دخول المطبخ';
  }
  return 'دخول التوصيل';
}

function resolveRoleSubtitle(role: UserRole, hasTenantScope: boolean): string {
  if (role === 'manager') {
    return hasTenantScope ? 'أدخل بيانات الحساب للوصول إلى هذه النسخة مباشرة.' : '';
  }
  if (role === 'kitchen') {
    return 'وصول تشغيلي مباشر لفريق المطبخ داخل هذه النسخة.';
  }
  return 'وصول تشغيلي مباشر لفريق التوصيل داخل هذه النسخة.';
}

export function LoginPage({ role }: LoginPageProps) {
  const params = useParams<{ tenantCode?: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem('restaurants-theme-mode', 'light');
    document.documentElement.dataset.theme = 'light';
  }, []);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const setSession = useAuthStore((state) => state.setSession);

  const tenantCode = useMemo(() => {
    if (params.tenantCode) {
      return params.tenantCode;
    }
    const queryCode = new URLSearchParams(location.search).get('tenant');
    return queryCode?.trim() || '';
  }, [location.search, params.tenantCode]);

  const tenantEntryQuery = useQuery({
    queryKey: ['tenant-entry', tenantCode],
    queryFn: () => api.publicTenantEntry(tenantCode),
    enabled: tenantCode.length > 0,
    staleTime: 60_000,
  });

  const roleTitle = resolveRoleTitle(role);
  const roleSubtitle = resolveRoleSubtitle(role, tenantCode.length > 0);
  const brandTitle = tenantEntryQuery.data?.tenant_brand_name || roleTitle;
  const ownerLabel = tenantEntryQuery.data?.client_brand_name || roleSubtitle;
  const tenantEntryError =
    tenantEntryQuery.error instanceof Error ? tenantEntryQuery.error.message : 'تعذر تحميل بيانات النسخة الآن.';

  const brandIconSrc = '/brand/icon.png';

  const submitDisabled = loading || (Boolean(tenantCode) && tenantEntryQuery.isError);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (tenantCode) {
        window.sessionStorage.setItem('active_tenant_code', tenantCode);
      }
      const session = await api.login({ username, password, role });
      queryClient.clear();
      setSession({ user: session.user });
      navigate(role === 'manager' ? '/console' : role === 'kitchen' ? '/kitchen/console' : '/delivery/console');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'تعذر تسجيل الدخول.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent px-4 py-8 text-[var(--app-text)]">
      <div
        className={
          role === 'manager'
            ? 'mx-auto flex min-h-[calc(100vh-4rem)] max-w-md items-center'
            : 'mx-auto grid min-h-[calc(100vh-4rem)] max-w-5xl items-center gap-6 lg:grid-cols-[minmax(0,1fr)_420px]'
        }
      >
        {role === 'manager' ? null : (
          <section className="rounded-[32px] border border-[#ead9bf] bg-white/88 p-6 shadow-[0_24px_60px_rgba(70,45,20,0.12)] backdrop-blur md:p-8">
            <div className="inline-flex h-14 w-14 items-center justify-center rounded-[22px] border border-[#ead9bf] bg-[#fff1dd] text-[#b66b21]">
              <Store className="h-6 w-6" />
            </div>
            <p className="mt-5 text-xs font-black tracking-[0.24em] text-[#9a7f62]">منصة التشغيل</p>
            <h1 className="mt-3 text-3xl font-black text-[#2f2218] md:text-4xl">{roleTitle}</h1>
            <p className="mt-3 max-w-2xl text-sm font-semibold leading-7 text-[#6b5644] md:text-base">{roleSubtitle}</p>
          </section>
        )}

        <section className="w-full rounded-[32px] border border-[#f0dcc0] bg-white p-6 shadow-[0_24px_60px_rgba(70,45,20,0.14)] md:p-8">
          <div className="mb-5 text-center">
            <div className="mx-auto inline-flex h-16 w-16 items-center justify-center rounded-[24px] border border-[#f0dcc0] bg-white shadow-[0_10px_25px_rgba(70,45,20,0.10)]">
              <img src={brandIconSrc} alt="Brand" className="h-11 w-11" />
            </div>
            <h2 className="mt-4 text-2xl font-black text-[#2f2218]">{brandTitle}</h2>
            {ownerLabel ? <p className="mt-2 text-sm font-semibold text-[#6b5644]">{ownerLabel}</p> : null}
          </div>

          {tenantCode ? (
            tenantEntryQuery.isError ? (
              <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
                {tenantEntryError}
              </div>
            ) : tenantEntryQuery.data ? (
              <div className="mb-4 rounded-[24px] border border-[#ead9bf] bg-[#fff8ee] px-4 py-4">
                <p className="text-[11px] font-black tracking-[0.2em] text-[#9a7f62]">النسخة الحالية</p>
                <p className="mt-2 text-lg font-black text-[#2f2218]">{tenantEntryQuery.data.tenant_brand_name}</p>
                <p className="mt-1 text-sm font-semibold text-[#6b5644]">{tenantEntryQuery.data.client_brand_name}</p>
              </div>
            ) : null
          ) : null}

          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block space-y-1.5">
              <span className="text-sm font-black text-[#6b5644]">اسم المستخدم</span>
              <input
                dir="ltr"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="form-input !rounded-2xl !border-[#e7caa2] !bg-[#fffdfa] !text-[#2f2218] focus:!border-[#ff3d1f] focus:!ring-2 focus:!ring-[#ff3d1f]/15"
                required
              />
            </label>

            <label className="block space-y-1.5">
              <span className="text-sm font-black text-[#6b5644]">كلمة المرور</span>
              <input
                type="password"
                dir="ltr"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="form-input !rounded-2xl !border-[#e7caa2] !bg-[#fffdfa] !text-[#2f2218] focus:!border-[#ff3d1f] focus:!ring-2 focus:!ring-[#ff3d1f]/15"
                required
              />
            </label>

            {error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={submitDisabled}
              className="inline-flex h-12 w-full items-center justify-center rounded-2xl bg-[#ff3d1f] px-4 text-sm font-black text-white transition hover:bg-[#e23419] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'جارٍ التحقق...' : 'دخول'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
