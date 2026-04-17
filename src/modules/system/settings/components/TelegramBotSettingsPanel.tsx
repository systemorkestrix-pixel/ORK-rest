import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';

const HEALTH_TONE_CLASS: Record<'healthy' | 'warning' | 'error', string> = {
  healthy: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  error: 'border-rose-200 bg-rose-50 text-rose-800',
};

const HEALTH_LABEL: Record<'healthy' | 'warning' | 'error', string> = {
  healthy: 'جاهز',
  warning: 'يحتاج متابعة',
  error: 'يوجد خلل',
};

export function TelegramBotSettingsPanel() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ['manager-telegram-bot-settings'],
    queryFn: () => api.managerTelegramBotSettings(role ?? 'manager'),
    enabled: role === 'manager',
  });

  const healthQuery = useQuery({
    queryKey: ['manager-telegram-bot-health'],
    queryFn: () => api.managerTelegramBotHealth(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: 30_000,
  });

  const [enabled, setEnabled] = useState(false);
  const [botToken, setBotToken] = useState('');
  const [botUsername, setBotUsername] = useState('');

  useEffect(() => {
    if (!settingsQuery.data) return;
    setEnabled(settingsQuery.data.enabled);
    setBotToken(settingsQuery.data.bot_token ?? '');
    setBotUsername(settingsQuery.data.bot_username ?? '');
  }, [settingsQuery.data]);

  const updateMutation = useMutation({
    mutationFn: () =>
      api.managerUpdateTelegramBotSettings(role ?? 'manager', {
        enabled,
        bot_token: botToken.trim() || null,
        bot_username: botUsername.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manager-telegram-bot-settings'] });
      queryClient.invalidateQueries({ queryKey: ['manager-telegram-bot-health'] });
      queryClient.invalidateQueries({ queryKey: ['manager-audit-system-logs'] });
    },
  });

  const saveDisabled = updateMutation.isPending || (enabled && (!botToken.trim() || !botUsername.trim()));
  const healthStatus = healthQuery.data?.status ?? 'warning';
  const healthTone = HEALTH_TONE_CLASS[healthStatus];
  const healthLabel = HEALTH_LABEL[healthStatus];
  const lastErrorAtLabel = useMemo(() => {
    if (!healthQuery.data?.last_error_at) return null;
    return new Date(healthQuery.data.last_error_at).toLocaleString('ar-DZ');
  }, [healthQuery.data?.last_error_at]);

  return (
    <section className="admin-card space-y-4 p-4">
      <div className="space-y-1">
        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-[#c7935f]">Telegram</p>
        <h3 className="text-base font-black text-[var(--text-primary-strong)]">بوت عنصر التوصيل</h3>
        <p className="text-xs font-semibold text-[var(--text-muted)]">
          اربط البوت مرة واحدة، ثم استخدمه لتشغيل السائقين من داخل Telegram مع فحص مباشر للحالة من نفس اللوحة.
        </p>
      </div>

      {settingsQuery.isLoading ? <p className="text-sm text-[var(--text-muted)]">جارٍ تحميل إعدادات البوت...</p> : null}

      {settingsQuery.isError ? (
        <p className="text-sm font-semibold text-rose-700">
          {(settingsQuery.error as Error).message || 'تعذر تحميل إعدادات البوت.'}
        </p>
      ) : null}

      <div className={`rounded-2xl border p-3 text-sm font-semibold ${healthTone}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="space-y-1">
            <p className="text-[11px] font-black uppercase tracking-[0.18em]">Health</p>
            <p>{healthQuery.isLoading ? 'جارٍ فحص حالة البوت...' : `حالة البوت: ${healthLabel}`}</p>
          </div>
          <button
            type="button"
            className="btn-secondary ui-size-sm"
            disabled={healthQuery.isFetching}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['manager-telegram-bot-health'] })}
          >
            {healthQuery.isFetching ? 'جارٍ الفحص...' : 'إعادة الفحص'}
          </button>
        </div>

        {healthQuery.data ? (
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <div className="rounded-2xl border border-current/15 bg-white/60 p-3">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] opacity-70">Bot</p>
              <p className="mt-1">التوكن: {healthQuery.data.token_configured ? 'مضبوط' : 'غير مضبوط'}</p>
              <p>اسم المستخدم: {healthQuery.data.bot_username || settingsQuery.data?.bot_username || '-'}</p>
              <p>اتصال Telegram: {healthQuery.data.bot_api_ok ? 'سليم' : 'غير متاح'}</p>
            </div>

            <div className="rounded-2xl border border-current/15 bg-white/60 p-3">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] opacity-70">Webhook</p>
              <p className="mt-1">الحالة: {healthQuery.data.webhook_ok ? 'متصل' : 'غير مكتمل'}</p>
              <p>التحديثات المعلقة: {healthQuery.data.pending_update_count}</p>
              <p>مطابقة المسار: {healthQuery.data.webhook_path_matches ? 'نعم' : 'لا'}</p>
            </div>

            <div className="rounded-2xl border border-current/15 bg-white/60 p-3 md:col-span-2">
              <p className="text-[11px] font-black uppercase tracking-[0.18em] opacity-70">الرابط الحالي</p>
              <p className="mt-1 break-all font-mono text-xs">{healthQuery.data.webhook_url || 'غير مضبوط بعد'}</p>
              <p className="mt-2 break-all font-mono text-xs text-[var(--text-muted)]">
                المسار المتوقع: {healthQuery.data.webhook_expected_path || '-'}
              </p>
            </div>

            {healthQuery.data.last_error_message ? (
              <div className="rounded-2xl border border-current/15 bg-white/60 p-3 md:col-span-2">
                <p className="text-[11px] font-black uppercase tracking-[0.18em] opacity-70">آخر خطأ</p>
                <p className="mt-1">{healthQuery.data.last_error_message}</p>
                {lastErrorAtLabel ? <p className="mt-1 text-xs opacity-80">آخر ظهور: {lastErrorAtLabel}</p> : null}
              </div>
            ) : null}

            {healthQuery.data.issues.length > 0 ? (
              <div className="rounded-2xl border border-current/15 bg-white/60 p-3 md:col-span-2">
                <p className="text-[11px] font-black uppercase tracking-[0.18em] opacity-70">ما يحتاج متابعة</p>
                <ul className="mt-1 space-y-1 text-xs">
                  {healthQuery.data.issues.map((issue) => (
                    <li key={issue}>• {issue}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {healthQuery.isError ? (
          <p className="mt-3 text-xs font-semibold text-rose-700">{(healthQuery.error as Error).message || 'تعذر فحص حالة البوت.'}</p>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1 md:col-span-2">
          <span className="form-label">حالة البوت</span>
          <select className="form-select" value={enabled ? 'enabled' : 'disabled'} onChange={(event) => setEnabled(event.target.value === 'enabled')}>
            <option value="enabled">مفعّل</option>
            <option value="disabled">متوقف</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="form-label">توكن البوت</span>
          <input className="form-input" value={botToken} onChange={(event) => setBotToken(event.target.value)} placeholder="123456:ABC..." />
        </label>

        <label className="space-y-1">
          <span className="form-label">اسم البوت</span>
          <input className="form-input" value={botUsername} onChange={(event) => setBotUsername(event.target.value)} placeholder="my_delivery_bot" />
        </label>
      </div>

      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-xs font-semibold text-[var(--text-secondary)]">
        <p>مسار الويبهوك داخل النظام:</p>
        <p className="mt-1 break-all font-mono text-[var(--text-primary-strong)]">
          {settingsQuery.data?.webhook_secret ? `/api/bot/telegram/${settingsQuery.data.webhook_secret}` : 'سيظهر بعد حفظ الإعدادات.'}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className="btn-primary ui-size-sm" disabled={saveDisabled} onClick={() => updateMutation.mutate()}>
          {updateMutation.isPending ? 'جارٍ الحفظ...' : 'حفظ إعدادات البوت'}
        </button>
        {updateMutation.isSuccess ? <span className="text-xs font-semibold text-emerald-700">تم الحفظ بنجاح.</span> : null}
        {updateMutation.isError ? <span className="text-xs font-semibold text-rose-700">{(updateMutation.error as Error).message}</span> : null}
      </div>
    </section>
  );
}
