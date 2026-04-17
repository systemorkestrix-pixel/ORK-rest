import type { DeliveryPolicies, DeliverySettings, SystemContext } from '@/shared/api/types';

interface DeliveryPolicySettingsPanelProps {
  settings: DeliverySettings;
  policies: DeliveryPolicies;
  systemContext?: SystemContext | null;
  deliveryFeeInput: string;
  deliveryMinOrderInput: string;
  deliveryAutoNotifyTeam: boolean;
  onDeliveryFeeInputChange: (value: string) => void;
  onDeliveryMinOrderInputChange: (value: string) => void;
  onDeliveryAutoNotifyTeamChange: (value: boolean) => void;
  onSaveSettings: () => void;
  onSavePolicies: () => void;
  savingSettings: boolean;
  savingPolicies: boolean;
  settingsError?: string;
  policiesError?: string;
  settingsSuccess?: boolean;
  policiesSuccess?: boolean;
}

export function DeliveryPolicySettingsPanel({
  settings,
  policies,
  systemContext,
  deliveryFeeInput,
  deliveryMinOrderInput,
  deliveryAutoNotifyTeam,
  onDeliveryFeeInputChange,
  onDeliveryMinOrderInputChange,
  onDeliveryAutoNotifyTeamChange,
  onSaveSettings,
  onSavePolicies,
  savingSettings,
  savingPolicies,
  settingsError,
  policiesError,
  settingsSuccess,
  policiesSuccess,
}: DeliveryPolicySettingsPanelProps) {
  const countryName = systemContext?.country_name ?? settings.system_context?.country_name ?? 'غير محددة';
  const currencyLabel = `${systemContext?.currency_symbol ?? settings.system_context?.currency_symbol ?? '...'} ${
    systemContext?.currency_code ?? settings.system_context?.currency_code ?? ''
  }`.trim();

  return (
    <section className="admin-card space-y-4 p-4">
      <div className="space-y-1">
        <h3 className="text-sm font-black text-[var(--text-primary-strong)]">سياسات التوصيل</h3>
        <p className="text-xs text-[var(--text-muted)]">حدد الحد الأدنى والرسم الاحتياطي وطريقة الإبلاغ.</p>
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
          <p className="font-bold text-[var(--text-muted)]">الدولة</p>
          <p className="mt-1 font-black text-[var(--text-primary-strong)]">{countryName}</p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
          <p className="font-bold text-[var(--text-muted)]">العملة</p>
          <p className="mt-1 font-black text-[var(--text-primary-strong)]">{currencyLabel || 'غير محددة'}</p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
          <p className="font-bold text-[var(--text-muted)]">العناوين المسعّرة</p>
          <p className="mt-1 font-black text-[var(--text-primary-strong)]">{settings.active_zones_count ?? 0}</p>
        </div>
      </div>

      <div className="grid gap-3">
        <label className="space-y-1">
          <span className="form-label">الرسم الاحتياطي</span>
          <input
            type="number"
            min={0}
            step="0.1"
            value={deliveryFeeInput}
            onChange={(event) => onDeliveryFeeInputChange(event.target.value)}
            className="form-input"
          />
          <p className="text-xs text-[var(--text-muted)]">يستخدم إذا لم يكن للعناوين سعر محدد.</p>
        </label>

        <label className="space-y-1">
          <span className="form-label">الحد الأدنى لطلب التوصيل</span>
          <input
            type="number"
            min={0}
            step="0.1"
            value={deliveryMinOrderInput}
            onChange={(event) => onDeliveryMinOrderInputChange(event.target.value)}
            className="form-input"
          />
          <p className="text-xs text-[var(--text-muted)]">يمنع طلبات التوصيل الأقل من هذا المبلغ.</p>
        </label>

        <label className="flex min-h-[var(--ui-control-height)] items-center gap-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-[var(--surface-control-border)]"
            checked={deliveryAutoNotifyTeam}
            onChange={(event) => onDeliveryAutoNotifyTeamChange(event.target.checked)}
          />
          <div>
            <p className="text-sm font-black text-[var(--text-primary-strong)]">إبلاغ فريق التوصيل تلقائيًا</p>
            <p className="text-xs text-[var(--text-muted)]">عطّله إذا كنت تريد تحديد الجهة يدويًا لكل طلب.</p>
          </div>
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={onSaveSettings} disabled={savingSettings} className="btn-primary">
          {savingSettings ? 'جارٍ حفظ الرسم...' : 'حفظ الرسم'}
        </button>
        <button type="button" onClick={onSavePolicies} disabled={savingPolicies} className="btn-secondary">
          {savingPolicies ? 'جارٍ حفظ السياسات...' : 'حفظ السياسات'}
        </button>
      </div>

      <div className="flex flex-wrap gap-3 text-xs font-bold text-[var(--text-secondary)]">
        <span>الرسم الحالي: {(settings.delivery_fee ?? 0).toFixed(2)}</span>
        <span>الحد الأدنى الحالي: {(policies.min_order_amount ?? 0).toFixed(2)}</span>
      </div>

      {settingsError ? <p className="text-xs font-semibold text-rose-400">{settingsError}</p> : null}
      {policiesError ? <p className="text-xs font-semibold text-rose-400">{policiesError}</p> : null}
      {settingsSuccess ? <p className="text-xs font-semibold text-emerald-400">تم حفظ الرسم.</p> : null}
      {policiesSuccess ? <p className="text-xs font-semibold text-emerald-400">تم حفظ السياسات.</p> : null}
    </section>
  );
}
