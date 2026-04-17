import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, RefreshCcw, ShieldCheck, TimerReset } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';

function findOperationalValue(rows: Array<{ key: string; value: string }>, key: string, fallback: string): string {
  const row = rows.find((item) => item.key === key);
  return row?.value ?? fallback;
}

export function ManagerKitchenSettingsPage() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context', role],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 60_000,
  });

  const tenantScopeKey = tenantContextQuery.data?.tenant_id ?? 'tenant-unknown';

  const accessQuery = useQuery({
    queryKey: ['manager-kitchen-access', tenantScopeKey],
    queryFn: () => api.managerKitchenAccess(role ?? 'manager'),
    enabled: role === 'manager' && tenantContextQuery.isSuccess,
  });

  const operationalSettingsQuery = useQuery({
    queryKey: ['manager-operational-settings', tenantScopeKey],
    queryFn: () => api.managerOperationalSettings(role ?? 'manager'),
    enabled: role === 'manager' && tenantContextQuery.isSuccess,
    staleTime: 60_000,
  });

  const regenerateMutation = useMutation({
    mutationFn: () => api.managerRegenerateKitchenAccessPassword(role ?? 'manager'),
    onSuccess: (result) => {
      queryClient.setQueryData(['manager-kitchen-access', tenantScopeKey], result);
    },
  });

  const updateSettingMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.managerUpdateOperationalSetting(role ?? 'manager', { key, value }),
    onSuccess: (updatedRow) => {
      queryClient.setQueryData(
        ['manager-operational-settings', tenantScopeKey],
        (current: Array<{ key: string; value: string; description: string; editable: boolean }> | undefined) => {
          if (!current) {
            return [updatedRow];
          }
          const next = current.filter((row) => row.key !== updatedRow.key);
          return [...next, updatedRow];
        },
      );
      queryClient.invalidateQueries({ queryKey: ['kitchen-runtime-settings'] });
    },
  });

  const access = regenerateMutation.data ?? accessQuery.data ?? null;
  const operationalSettings = operationalSettingsQuery.data ?? [];
  const pollingMs = useMemo(
    () => findOperationalValue(operationalSettings, 'order_polling_ms', '5000'),
    [operationalSettings],
  );
  const metricsWindow = useMemo(
    () => findOperationalValue(operationalSettings, 'kitchen_metrics_window', 'day'),
    [operationalSettings],
  );

  if ((accessQuery.isLoading || operationalSettingsQuery.isLoading) && !access) {
    return (
      <div className="rounded-3xl border border-[var(--console-border)] bg-[var(--surface-card)] p-6 text-sm font-semibold text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تجهيز ضبط المطبخ...
      </div>
    );
  }

  const errorMessage =
    (accessQuery.error instanceof Error ? accessQuery.error.message : null) ??
    (operationalSettingsQuery.error instanceof Error ? operationalSettingsQuery.error.message : null);

  if (errorMessage && !access) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm font-semibold text-rose-700">
        {errorMessage}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="admin-card space-y-5 p-4 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">KITCHEN ACCESS</p>
            <h2 className="mt-2 text-xl font-black text-[var(--text-primary-strong)]">وصول لوحة المطبخ</h2>
            <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
              عند تفعيل المطبخ، يتم تجهيز الدخول لهذه النسخة مباشرة. من هنا يمكن إعادة توليد كلمة المرور في أي وقت.
            </p>
          </div>
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-300 bg-emerald-50 text-emerald-700">
            <ShieldCheck className="h-5 w-5" />
          </span>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.2fr)]">
          <label className="block space-y-2">
            <span className="text-sm font-bold text-[var(--text-secondary)]">مسار الدخول</span>
            <input
              readOnly
              value={access?.login_path ?? ''}
              dir="ltr"
              className="form-input h-12 w-full rounded-2xl border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-bold text-[var(--text-secondary)]">اسم الدخول</span>
            <input
              readOnly
              value={access?.username ?? ''}
              dir="ltr"
              className="form-input h-12 w-full rounded-2xl border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]"
            />
          </label>

          <div className="space-y-2">
            <span className="text-sm font-bold text-[var(--text-secondary)]">كلمة المرور</span>
            <div className="flex flex-col gap-2 md:flex-row">
              <input
                readOnly
                value={access?.password ?? ''}
                dir="ltr"
                className="form-input h-12 min-w-0 flex-1 rounded-2xl border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]"
              />
              <button
                type="button"
                onClick={() => regenerateMutation.mutate()}
                disabled={regenerateMutation.isPending}
                className="inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-2xl border border-amber-300 bg-amber-100/80 px-4 text-sm font-black text-amber-900 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCcw className="h-4 w-4" />
                <span>{regenerateMutation.isPending ? 'جارٍ التوليد...' : 'إعادة التوليد'}</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="admin-card space-y-5 p-4 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">KITCHEN RUNTIME</p>
            <h3 className="mt-2 text-xl font-black text-[var(--text-primary-strong)]">ضبط التشغيل والإحصائيات</h3>
            <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
              التحكم في سرعة تحديث لوحة المطبخ ونافذة الإحصائيات التي تظهر للمشرف والمطبخ.
            </p>
          </div>
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-sky-300 bg-sky-50 text-sky-700">
            <TimerReset className="h-5 w-5" />
          </span>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <label className="block space-y-2 rounded-3xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
            <span className="text-sm font-bold text-[var(--text-secondary)]">فاصل التحديث</span>
            <select
              value={pollingMs}
              onChange={(event) =>
                updateSettingMutation.mutate({ key: 'order_polling_ms', value: event.target.value })
              }
              className="form-select h-12"
              disabled={updateSettingMutation.isPending}
            >
              <option value="3000">3 ثوان</option>
              <option value="5000">5 ثوان</option>
              <option value="10000">10 ثوان</option>
              <option value="15000">15 ثانية</option>
            </select>
            <p className="text-xs font-semibold text-[var(--text-muted)]">
              هذه القيمة تتحكم في سرعة تحديث شاشة المطبخ الحية.
            </p>
          </label>

          <label className="block space-y-2 rounded-3xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
            <span className="text-sm font-bold text-[var(--text-secondary)]">نافذة الإحصائيات</span>
            <select
              value={metricsWindow}
              onChange={(event) =>
                updateSettingMutation.mutate({ key: 'kitchen_metrics_window', value: event.target.value })
              }
              className="form-select h-12"
              disabled={updateSettingMutation.isPending}
            >
              <option value="day">يومي</option>
              <option value="week">أسبوعي</option>
              <option value="month">شهري</option>
            </select>
            <p className="text-xs font-semibold text-[var(--text-muted)]">
              تتحكم في متوسط التحضير وإحصائيات صرف المطبخ الظاهرة داخل النظام.
            </p>
          </label>
        </div>

        {updateSettingMutation.error instanceof Error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {updateSettingMutation.error.message}
          </div>
        ) : null}
      </section>

      <section className="admin-card p-4 md:p-5">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-violet-300 bg-violet-50 text-violet-700">
            <KeyRound className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-base font-black text-[var(--text-primary-strong)]">منطق الوصول</h3>
            <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
              هذه البيانات تخص لوحة المطبخ لهذه النسخة فقط. لا يحتاج صاحب المطعم إلى إنشاء مستخدم يدويًا لتجهيز الأداة.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
