import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ShieldCheck, Store } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { AccountSession, User } from '@/shared/api/types';
import { PageHeaderCard } from '@/shared/ui/PageHeaderCard';
import { PageShell } from '@/shared/ui/PageShell';
import { parseApiDateMs } from '@/shared/utils/date';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { StorefrontSettingsPanel } from './components/StorefrontSettingsPanel';

function formatDateTime(value: string): string {
  return new Date(parseApiDateMs(value)).toLocaleString('ar-DZ-u-nu-latn');
}

function sessionStatusMeta(session: AccountSession): { label: string; className: string } {
  if (session.is_active) {
    return { label: 'نشطة', className: 'text-emerald-700' };
  }
  if (session.revoked_at) {
    return { label: 'منهية', className: 'text-rose-700' };
  }
  return { label: 'منتهية', className: 'text-amber-700' };
}

type SettingsBranchId = 'home' | 'storefront' | 'account';

interface SettingsBranchDefinition {
  id: Exclude<SettingsBranchId, 'home'>;
  title: string;
  description: string;
  icon: typeof Store;
  path: string;
}

const SETTINGS_BRANCHES: SettingsBranchDefinition[] = [
  {
    id: 'storefront',
    title: 'الواجهة العامة',
    description: 'هوية الواجهة وروابط التواصل التي يراها الزبون.',
    icon: Store,
    path: '/console/system/settings/storefront',
  },
  {
    id: 'account',
    title: 'الحساب والأمان',
    description: 'بيانات المدير والجلسات النشطة في مكان واحد.',
    icon: ShieldCheck,
    path: '/console/system/settings/account',
  },
];

function branchButtonClass(active: boolean): string {
  return active
    ? 'border-[#b98757] bg-[var(--surface-card)] text-[var(--text-primary-strong)] shadow-[var(--console-shadow)]'
    : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)] hover:border-[#b98757] hover:text-[var(--text-primary)]';
}

function resolveSettingsBranch(pathname: string): SettingsBranchId {
  if (pathname.startsWith('/console/system/settings/storefront')) {
    return 'storefront';
  }
  if (pathname.startsWith('/console/system/settings/account')) {
    return 'account';
  }
  return 'home';
}

function SettingsDirectoryGrid({
  activeBranch,
  onOpenBranch,
}: {
  activeBranch: SettingsBranchId;
  onOpenBranch: (branch: Exclude<SettingsBranchId, 'home'>) => void;
}) {
  return (
    <section className="admin-card p-3">
      <div className="grid gap-2 md:grid-cols-2">
        {SETTINGS_BRANCHES.map((branch) => {
          const Icon = branch.icon;
          const isActive = activeBranch === branch.id;
          return (
            <button
              key={branch.id}
              type="button"
              onClick={() => onOpenBranch(branch.id)}
              className={`rounded-2xl border px-4 py-3 text-right transition ${branchButtonClass(isActive)}`}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-[#f3b36b]">
                  <Icon className="h-5 w-5" />
                </span>
                <div className="space-y-1">
                  <p className="text-sm font-black">{branch.title}</p>
                  <p className="text-xs font-semibold text-[var(--text-muted)]">{branch.description}</p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SettingsBranchLinks({
  activeBranch,
  onOpenBranch,
}: {
  activeBranch: SettingsBranchId;
  onOpenBranch: (branch: Exclude<SettingsBranchId, 'home'>) => void;
}) {
  return (
    <section className="admin-card p-3">
      <div className="grid gap-2 sm:grid-cols-2">
        {SETTINGS_BRANCHES.map((branch) => {
          const isActive = activeBranch === branch.id;
          return (
            <button
              key={branch.id}
              type="button"
              onClick={() => onOpenBranch(branch.id)}
              className={`rounded-2xl border px-3 py-3 text-right transition ${branchButtonClass(isActive)}`}
            >
              <p className="text-sm font-black">{branch.title}</p>
              <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">{branch.description}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SettingsSectionCard({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="admin-card space-y-4 p-4">
      <div className="space-y-1">
        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-[#c7935f]">{eyebrow}</p>
        <h3 className="text-base font-black text-[var(--text-primary-strong)]">{title}</h3>
        <p className="text-xs font-semibold text-[var(--text-muted)]">{description}</p>
      </div>
      {children}
    </section>
  );
}

export function SettingsPage() {
  const role = useAuthStore((state) => state.role);
  const currentUser = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const location = useLocation();
  const navigate = useNavigate();

  const [managerName, setManagerName] = useState('');
  const [managerPassword, setManagerPassword] = useState('');
  const [managerPasswordConfirm, setManagerPasswordConfirm] = useState('');

  const activeBranch = resolveSettingsBranch(location.pathname);

  useEffect(() => {
    if (
      location.pathname.startsWith('/console/system/settings/operations') ||
      location.pathname.startsWith('/console/system/settings/maintenance')
    ) {
      navigate('/console/system/settings', { replace: true });
    }
  }, [location.pathname, navigate]);

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context'],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });
  const tenantScopeKey = tenantContextQuery.data?.tenant_id ?? 'tenant-unknown';

  const meQuery = useQuery({
    queryKey: ['auth-me', tenantScopeKey],
    queryFn: () => api.me(),
    enabled: role === 'manager' && tenantContextQuery.isSuccess && activeBranch === 'account',
  });

  const sessionsQuery = useQuery({
    queryKey: ['manager-account-sessions', tenantScopeKey],
    queryFn: () => api.managerAccountSessions(role ?? 'manager'),
    enabled: role === 'manager' && tenantContextQuery.isSuccess && activeBranch === 'account',
    refetchInterval: adaptiveRefetchInterval(15000),
  });

  const managerProfile = useMemo<User | null>(() => meQuery.data ?? currentUser ?? null, [currentUser, meQuery.data]);

  const updateManagerAccountMutation = useMutation({
    mutationFn: async () => {
      if (!managerProfile) {
        throw new Error('تعذر تحميل بيانات حساب المدير.');
      }
      const nextName = managerName.trim();
      if (nextName.length < 2) {
        throw new Error('الاسم يجب أن يكون حرفين على الأقل.');
      }

      const nextPassword = managerPassword.trim();
      if (nextPassword.length > 0 && nextPassword.length < 8) {
        throw new Error('كلمة المرور يجب أن تكون 8 أحرف على الأقل.');
      }
      if (nextPassword.length > 0) {
        const hasLetter = /[A-Za-z\u0600-\u06FF]/.test(nextPassword);
        const hasNumber = /\d/.test(nextPassword);
        if (!hasLetter || !hasNumber) {
          throw new Error('كلمة المرور يجب أن تحتوي على أحرف وأرقام على الأقل.');
        }
        if (/\s/.test(nextPassword)) {
          throw new Error('كلمة المرور يجب ألا تحتوي على مسافات.');
        }
      }

      return api.managerUpdateAccountProfile(role ?? 'manager', {
        name: nextName,
        password: nextPassword.length > 0 ? nextPassword : undefined,
      });
    },
    onSuccess: () => {
      setManagerPassword('');
      setManagerPasswordConfirm('');
      queryClient.invalidateQueries({ queryKey: ['auth-me', tenantScopeKey] });
      queryClient.invalidateQueries({ queryKey: ['manager-users'] });
    },
  });

  const revokeSessionsMutation = useMutation({
    mutationFn: () => api.managerRevokeAllAccountSessions(role ?? 'manager'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manager-account-sessions', tenantScopeKey] });
    },
  });

  useEffect(() => {
    if (managerProfile?.name) {
      setManagerName(managerProfile.name);
    }
  }, [managerProfile?.name]);

  const sessions = sessionsQuery.data ?? [];
  const activeSessionsCount = sessions.filter((session) => session.is_active).length;

  const managerPasswordMismatch =
    managerPassword.length > 0 && managerPasswordConfirm.length > 0 && managerPassword !== managerPasswordConfirm;
  const managerPasswordPolicyError = useMemo(() => {
    const value = managerPassword.trim();
    if (value.length === 0) return '';
    if (value.length < 8) return 'كلمة المرور يجب أن تكون 8 أحرف على الأقل.';
    if (!/[A-Za-z\u0600-\u06FF]/.test(value) || !/\d/.test(value)) {
      return 'كلمة المرور يجب أن تحتوي على أحرف وأرقام على الأقل.';
    }
    if (/\s/.test(value)) return 'كلمة المرور يجب ألا تحتوي على مسافات.';
    return '';
  }, [managerPassword]);

  const managerAccountError = updateManagerAccountMutation.isError
    ? updateManagerAccountMutation.error instanceof Error
      ? updateManagerAccountMutation.error.message
      : 'تعذر تحديث بيانات الحساب.'
    : '';

  const sessionsError = revokeSessionsMutation.isError
    ? revokeSessionsMutation.error instanceof Error
      ? revokeSessionsMutation.error.message
      : 'تعذر إنهاء الجلسات.'
    : '';

  const trimmedName = managerName.trim();
  const hasNameChange = !!managerProfile && trimmedName.length >= 2 && trimmedName !== managerProfile.name;
  const hasPasswordInput = managerPassword.trim().length > 0;
  const canSubmitAccount =
    !updateManagerAccountMutation.isPending &&
    !!managerProfile &&
    trimmedName.length >= 2 &&
    !managerPasswordMismatch &&
    !managerPasswordPolicyError &&
    (hasNameChange || hasPasswordInput);

  if (role !== 'manager') {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm font-semibold text-amber-700">
        هذه الصفحة مخصصة لحساب المدير فقط.
      </div>
    );
  }

  if (activeBranch === 'account' && (meQuery.isLoading || sessionsQuery.isLoading)) {
    return (
      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تحميل إعدادات الحساب...
      </div>
    );
  }

  if (activeBranch === 'account' && (meQuery.isError || sessionsQuery.isError)) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        تعذر تحميل إعدادات الحساب.
      </div>
    );
  }

  const currentBranchMeta = SETTINGS_BRANCHES.find((branch) => branch.id === activeBranch) ?? SETTINGS_BRANCHES[0];
  const CurrentBranchIcon = currentBranchMeta.icon;
  const openBranch = (branch: Exclude<SettingsBranchId, 'home'>) => {
    const target = SETTINGS_BRANCHES.find((item) => item.id === branch)?.path ?? '/console/system/settings';
    navigate(target);
  };
  const goToSettingsHome = () => navigate('/console/system/settings');
  const pageTitle = activeBranch === 'home' ? 'الإعدادات' : currentBranchMeta.title;
  const pageDescription =
    activeBranch === 'home'
      ? 'هنا تبقى الأدوات المحلية التي يتحكم بها صاحب المطعم مباشرة.'
      : currentBranchMeta.description;

  return (
    <PageShell
      className="admin-page"
      header={
        <PageHeaderCard
          title={pageTitle}
          description={pageDescription}
          icon={<CurrentBranchIcon className="h-5 w-5" />}
          actions={
            <div className="flex flex-wrap gap-2">
              {activeBranch === 'home' ? null : (
                <button type="button" className="btn-secondary ui-size-sm" onClick={goToSettingsHome}>
                  العودة إلى الإعدادات
                </button>
              )}
            </div>
          }
          metrics={[
            { label: 'الفروع المحلية', value: SETTINGS_BRANCHES.length, tone: 'info' },
            { label: 'الجلسات النشطة', value: activeSessionsCount, tone: activeSessionsCount > 0 ? 'success' : 'default' },
            { label: 'نطاق الإعدادات', value: 'محلي', tone: 'default' },
          ]}
        />
      }
      toolbar={activeBranch === 'home' ? null : <SettingsBranchLinks activeBranch={activeBranch} onOpenBranch={openBranch} />}
      workspaceClassName="space-y-4"
    >
      {activeBranch === 'home' ? <SettingsDirectoryGrid activeBranch={activeBranch} onOpenBranch={openBranch} /> : null}
      {activeBranch === 'storefront' ? <StorefrontSettingsPanel /> : null}

      {activeBranch === 'account' ? (
        <div className="space-y-4">
          <SettingsSectionCard
            eyebrow="الحساب"
            title="الحساب الشخصي"
            description="حدّث الاسم وكلمة المرور لحساب المدير. عند تغيير كلمة المرور تُنهى جميع الجلسات النشطة تلقائيًا."
          >
            <div className="grid gap-2 text-sm sm:grid-cols-3">
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-[11px] text-gray-500">اسم المستخدم</p>
                <p className="font-bold text-gray-800">{managerProfile?.username ?? '-'}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-[11px] text-gray-500">الدور</p>
                <p className="font-bold text-gray-800">{managerProfile?.role === 'manager' ? 'مدير النظام' : '-'}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-[11px] text-gray-500">الجلسات النشطة</p>
                <p className="font-bold text-brand-700">{activeSessionsCount}</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <label className="space-y-1">
                <span className="form-label">الاسم</span>
                <input className="form-input" value={managerName} onChange={(event) => setManagerName(event.target.value)} placeholder="اسم المدير" />
              </label>
              <label className="space-y-1">
                <span className="form-label">كلمة المرور الجديدة (اختياري)</span>
                <input
                  type="password"
                  className="form-input"
                  placeholder="8 أحرف على الأقل وتحتوي أحرفًا وأرقامًا"
                  value={managerPassword}
                  onChange={(event) => setManagerPassword(event.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="form-label">تأكيد كلمة المرور</span>
                <input
                  type="password"
                  className="form-input"
                  placeholder="أعد إدخال كلمة المرور"
                  value={managerPasswordConfirm}
                  onChange={(event) => setManagerPasswordConfirm(event.target.value)}
                />
              </label>
            </div>

            {managerPasswordMismatch ? <p className="text-xs font-semibold text-amber-700">تأكيد كلمة المرور غير مطابق.</p> : null}
            {managerPasswordPolicyError ? <p className="text-xs font-semibold text-amber-700">{managerPasswordPolicyError}</p> : null}
            {managerAccountError ? <p className="text-xs font-semibold text-rose-700">{managerAccountError}</p> : null}
            {updateManagerAccountMutation.isSuccess ? <p className="text-xs font-semibold text-emerald-700">تم حفظ بيانات الحساب بنجاح.</p> : null}

            <button type="button" className="btn-primary" disabled={!canSubmitAccount} onClick={() => updateManagerAccountMutation.mutate()}>
              {updateManagerAccountMutation.isPending ? 'جارٍ الحفظ...' : 'حفظ بيانات الحساب'}
            </button>
          </SettingsSectionCard>

          <SettingsSectionCard
            eyebrow="الأمان"
            title="الجلسات النشطة"
            description="يمكنك إنهاء جميع جلسات الحساب الحالية عند الحاجة. الحد الأقصى للجلسات النشطة هو 3 جلسات."
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs font-semibold text-[var(--text-muted)]">تُعرض هنا آخر الجلسات المعتمدة للحساب الإداري.</div>
              <button
                type="button"
                className="btn-danger ui-size-sm"
                disabled={revokeSessionsMutation.isPending || sessions.length === 0}
                onClick={() => revokeSessionsMutation.mutate()}
              >
                {revokeSessionsMutation.isPending ? 'جارٍ الإنهاء...' : 'إنهاء جميع الجلسات'}
              </button>
            </div>
            {sessionsError ? <p className="text-xs font-semibold text-rose-700">{sessionsError}</p> : null}
            {revokeSessionsMutation.isSuccess ? (
              <p className="text-xs font-semibold text-emerald-700">تم إنهاء {revokeSessionsMutation.data?.revoked_count ?? 0} جلسة.</p>
            ) : null}

            <section className="admin-table-shell">
              <div className="adaptive-table overflow-x-auto">
                <table className="table-unified min-w-full text-sm">
                  <thead className="bg-brand-50 text-gray-700">
                    <tr>
                      <th className="px-4 py-3 font-bold">#</th>
                      <th className="px-4 py-3 font-bold">بداية الجلسة</th>
                      <th className="px-4 py-3 font-bold">انتهاء الصلاحية</th>
                      <th className="px-4 py-3 font-bold">حالة الجلسة</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((session) => {
                      const meta = sessionStatusMeta(session);
                      return (
                        <tr key={session.id} className="border-t border-gray-100">
                          <td data-label="#" className="px-4 py-3 font-bold">{session.id}</td>
                          <td data-label="بداية الجلسة" className="px-4 py-3 text-xs text-gray-600">{formatDateTime(session.created_at)}</td>
                          <td data-label="انتهاء الصلاحية" className="px-4 py-3 text-xs text-gray-600">{formatDateTime(session.expires_at)}</td>
                          <td data-label="حالة الجلسة" className={`px-4 py-3 text-xs font-bold ${meta.className}`}>{meta.label}</td>
                        </tr>
                      );
                    })}
                    {sessions.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                          لا توجد جلسات مسجلة.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </SettingsSectionCard>
        </div>
      ) : null}
    </PageShell>
  );
}
