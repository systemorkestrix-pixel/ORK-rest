import { FormEvent, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import { api } from '@/shared/api/client';
import type { UserRole } from '@/shared/api/types';
import { useAuthStore } from '../store';

interface LoginPageProps {
  role: UserRole;
}

export function LoginPage({ role }: LoginPageProps) {
  const params = useParams<{ tenantCode?: string }>();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const setSession = useAuthStore((state) => state.setSession);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

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

  const title = useMemo(() => {
    if (role === 'manager') {
      return tenantEntryQuery.data?.tenant_brand_name || 'دخول لوحة المدير';
    }
    if (role === 'kitchen') {
      return tenantEntryQuery.data?.tenant_brand_name
        ? `المطبخ • ${tenantEntryQuery.data.tenant_brand_name}`
        : 'دخول لوحة المطبخ';
    }
    return tenantEntryQuery.data?.tenant_brand_name
      ? `التوصيل • ${tenantEntryQuery.data.tenant_brand_name}`
      : 'دخول لوحة التوصيل';
  }, [role, tenantEntryQuery.data?.tenant_brand_name]);

  const subtitle = useMemo(() => {
    if (role === 'manager') {
      if (tenantEntryQuery.data) {
        return `${tenantEntryQuery.data.client_brand_name} • وصول خاص بهذه النسخة فقط`;
      }
      return 'وصول خاص بإدارة النظام';
    }
    if (role === 'kitchen') {
      return tenantEntryQuery.data
        ? `${tenantEntryQuery.data.client_brand_name} • وصول خاص بمطبخ هذه النسخة`
        : 'وصول خاص بمستخدمي المطبخ';
    }
    return tenantEntryQuery.data
      ? `${tenantEntryQuery.data.client_brand_name} • وصول خاص بالتوصيل لهذه النسخة`
      : 'وصول خاص بمستخدمي التوصيل';
  }, [role, tenantEntryQuery.data]);

  const devDefaults = useMemo(() => {
    if (!import.meta.env.DEV) {
      return null;
    }
    return {
      manager: {
        username: import.meta.env.VITE_DEV_MANAGER_USERNAME ?? 'manager',
        password: import.meta.env.VITE_DEV_MANAGER_PASSWORD ?? 'ChangeMe-Manager-2026!',
      },
      kitchen: {
        username: import.meta.env.VITE_DEV_KITCHEN_USERNAME ?? 'kitchen',
        password: import.meta.env.VITE_DEV_KITCHEN_PASSWORD ?? 'ChangeMe-Kitchen-2026!',
      },
      delivery: {
        username: import.meta.env.VITE_DEV_DELIVERY_USERNAME ?? 'delivery',
        password: import.meta.env.VITE_DEV_DELIVERY_PASSWORD ?? 'ChangeMe-Delivery-2026!',
      },
    } satisfies Record<UserRole, { username: string; password: string }>;
  }, []);

  const devPreset = devDefaults ? devDefaults[role] : null;

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
      setSession({
        user: session.user,
      });
      navigate(role === 'manager' ? '/console' : role === 'kitchen' ? '/kitchen/console' : '/delivery/console');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'فشل تسجيل الدخول');
    } finally {
      setLoading(false);
    }
  };

  const tenantEntryError =
    tenantEntryQuery.error instanceof Error ? tenantEntryQuery.error.message : 'تعذر تحميل بيانات النسخة.';
  const submitDisabled = loading || (Boolean(tenantCode) && tenantEntryQuery.isError);

  return (
    <div className="min-h-screen bg-[var(--app-bg)] px-4 py-10 text-[var(--text-primary)] transition-colors">
      <div className="mx-auto max-w-md rounded-3xl border border-[var(--console-border)] bg-[var(--surface-card)] p-6 shadow-[var(--console-shadow)]">
        <div className="mb-5 text-center">
          <div className="mx-auto mb-3 w-fit rounded-2xl bg-brand-600 px-3 py-1 text-sm font-black text-white">سريع</div>
          <h2 className="text-2xl font-black text-[var(--text-primary-strong)]">{title}</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{subtitle}</p>
        </div>

        {tenantCode ? (
          tenantEntryQuery.isError ? (
            <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm font-bold text-rose-700">
              {tenantEntryError}
            </div>
          ) : tenantEntryQuery.data ? (
            <div className="mb-4 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 py-3">
              <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">النسخة</p>
              <p className="mt-2 text-lg font-black text-[var(--text-primary-strong)]">
                {tenantEntryQuery.data.tenant_brand_name}
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-secondary)]">
                {tenantEntryQuery.data.client_brand_name}
              </p>
            </div>
          ) : null
        ) : null}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-bold text-[var(--text-secondary)]" htmlFor="username">
              اسم المستخدم
            </label>
            <input
              id="username"
              dir="ltr"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="form-input"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-bold text-[var(--text-secondary)]" htmlFor="password">
              كلمة المرور
            </label>
            <input
              id="password"
              type="password"
              dir="ltr"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="form-input"
              required
            />
          </div>

          {error ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

          {devPreset ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <p className="font-bold">بيانات دخول التطوير</p>
              <p className="mt-1">
                المستخدم:{' '}
                <span dir="ltr" className="font-semibold">
                  {devPreset.username}
                </span>
              </p>
              <p>
                كلمة المرور:{' '}
                <span dir="ltr" className="font-semibold">
                  {devPreset.password}
                </span>
              </p>
              <button
                type="button"
                className="mt-2 w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-bold text-amber-900 hover:bg-amber-100"
                onClick={() => {
                  setUsername(devPreset.username);
                  setPassword(devPreset.password);
                  setError('');
                }}
              >
                ملء بيانات الدخول
              </button>
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitDisabled}
            className="w-full rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {loading ? 'جارٍ التحقق...' : 'تسجيل الدخول'}
          </button>
        </form>
      </div>
    </div>
  );
}
