import { useMemo, useState } from 'react';

import type { DeliveryDriver, DeliveryProvider, User } from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';
import { TABLE_ACTION_BUTTON_BASE, TABLE_STATUS_CHIP_BASE } from '@/shared/ui/tableAppearance';

type ProviderType = 'internal_team' | 'partner_company';
type AccountMode = 'create' | 'link';
type ProviderModalStep = 'identity' | 'account' | 'review';

interface ProviderAccountDraft {
  name: string;
  username: string;
  password: string;
  active: boolean;
}

interface ProviderCreatePayload {
  account_user_id: number | null;
  name: string;
  provider_type: ProviderType;
  active: boolean;
  account_user?: ProviderAccountDraft | null;
}

interface ProviderUpdatePayload {
  account_user_id: number | null;
  name: string;
  provider_type: ProviderType;
  active: boolean;
}

interface DeliveryProvidersPanelProps {
  providers: DeliveryProvider[];
  drivers: DeliveryDriver[];
  availableAccountUsers: User[];
  onCreateProvider: (payload: ProviderCreatePayload) => void;
  onUpdateProvider: (providerId: number, payload: ProviderUpdatePayload) => void;
  onDeleteProvider: (providerId: number) => void;
  creating: boolean;
  updating: boolean;
  deleting?: boolean;
  error?: string;
}

function providerTypeLabel(providerType: DeliveryProvider['provider_type']) {
  return providerType === 'internal_team' ? 'فريق داخلي' : 'شركة توصيل';
}

const emptyAccountDraft: ProviderAccountDraft = {
  name: '',
  username: '',
  password: '',
  active: true,
};

export function DeliveryProvidersPanel({
  providers,
  drivers,
  availableAccountUsers,
  onCreateProvider,
  onUpdateProvider,
  onDeleteProvider,
  creating,
  updating,
  deleting = false,
  error,
}: DeliveryProvidersPanelProps) {
  const [open, setOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<DeliveryProvider | null>(null);
  const [modalStep, setModalStep] = useState<ProviderModalStep>('identity');
  const [form, setForm] = useState({
    account_mode: 'create' as AccountMode,
    account_user_id: null as number | null,
    name: '',
    provider_type: 'partner_company' as ProviderType,
    active: true,
    account: emptyAccountDraft,
  });

  const providerDriverCount = useMemo(() => {
    const counts = new Map<number, number>();
    for (const driver of drivers) {
      if (!driver.provider_id) continue;
      counts.set(driver.provider_id, (counts.get(driver.provider_id) ?? 0) + 1);
    }
    return counts;
  }, [drivers]);

  const busy = creating || updating || deleting;

  const openCreate = () => {
    setEditingProvider(null);
    setModalStep('identity');
    setForm({
      account_mode: 'create',
      account_user_id: null,
      name: '',
      provider_type: 'partner_company',
      active: true,
      account: emptyAccountDraft,
    });
    setOpen(true);
  };

  const openEdit = (provider: DeliveryProvider) => {
    setEditingProvider(provider);
    setModalStep('identity');
    setForm({
      account_mode: 'link',
      account_user_id: provider.account_user_id ?? null,
      name: provider.name,
      provider_type: provider.provider_type === 'internal_team' ? 'internal_team' : 'partner_company',
      active: provider.active,
      account: {
        ...emptyAccountDraft,
        name: provider.account_user_name ?? '',
        username: provider.account_username ?? '',
      },
    });
    setOpen(true);
  };

  const accountOptions = useMemo(() => {
    const map = new Map<number, User>();
    for (const user of availableAccountUsers) {
      map.set(user.id, user);
    }
    if (editingProvider?.account_user_id && editingProvider.account_user_name && editingProvider.account_username) {
      map.set(editingProvider.account_user_id, {
        id: editingProvider.account_user_id,
        name: editingProvider.account_user_name,
        username: editingProvider.account_username,
        role: 'delivery',
        active: true,
      });
    }
    return Array.from(map.values()).sort((left, right) => left.name.localeCompare(right.name, 'ar'));
  }, [availableAccountUsers, editingProvider]);

  const requiresProviderAccount = form.provider_type === 'partner_company';
  const supportsLinkingExisting = !editingProvider && accountOptions.length > 0;
  const usingNewAccount = requiresProviderAccount && !editingProvider && form.account_mode === 'create';
  const usingLinkedAccount = requiresProviderAccount && (editingProvider !== null || form.account_mode === 'link');
  const providerIdentityError = form.name.trim().length < 2 ? 'أدخل اسم جهة التوصيل أولًا.' : null;
  const providerAccountError =
    usingLinkedAccount && !form.account_user_id
      ? 'اختر حساب لوحة لهذه الجهة.'
      : usingNewAccount &&
          (form.account.name.trim().length < 2 ||
            form.account.username.trim().length < 3 ||
            form.account.password.length < 8)
        ? 'أكمل بيانات حساب لوحة الجهة أولًا.'
        : null;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-black text-[var(--text-primary-strong)]">جهات التوصيل</h3>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            أضف الجهة واضبط حساب لوحتها من هنا. إذا دخلت الجهة دورة تشغيل فعلية فالإجراء الصحيح لاحقًا يكون التعطيل لا الحذف.
          </p>
        </div>
        <button type="button" className="btn-secondary ui-size-sm" onClick={openCreate}>
          إضافة جهة
        </button>
      </div>

      <div className="admin-table-shell">
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-[var(--surface-card-subtle)] text-[var(--text-secondary)]">
              <tr>
                <th className="px-4 py-3 font-bold">الجهة</th>
                <th className="px-4 py-3 font-bold">النوع</th>
                <th className="px-4 py-3 font-bold">حساب اللوحة</th>
                <th className="px-4 py-3 font-bold">السائقون</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.id} className="border-t border-[var(--console-border)] align-top">
                  <td data-label="الجهة" className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="font-black text-[var(--text-primary-strong)]">{provider.name}</p>
                      <p className="text-xs text-[var(--text-muted)]">مرجع الجهة #{provider.id}</p>
                    </div>
                  </td>
                  <td data-label="النوع" className="px-4 py-3">
                    <span className={`${TABLE_STATUS_CHIP_BASE} bg-[#fff4e6] text-[#8f5126]`}>
                      {providerTypeLabel(provider.provider_type)}
                    </span>
                  </td>
                  <td data-label="حساب اللوحة" className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="font-black text-[var(--text-primary-strong)]">
                        {provider.account_user_name || 'بدون حساب لوحة'}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]" dir="ltr">
                        {provider.account_username ? `@${provider.account_username}` : 'لا يوجد ربط دخول بعد'}
                      </p>
                    </div>
                  </td>
                  <td data-label="السائقون" className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="font-black text-[var(--text-primary-strong)]">{providerDriverCount.get(provider.id) ?? 0}</p>
                      <p className="text-xs text-[var(--text-muted)]">
                        {provider.is_internal_default ? 'الجهة الداخلية الافتراضية للنظام' : 'عدد السائقين التابعين لهذه الجهة'}
                      </p>
                    </div>
                  </td>
                  <td data-label="الحالة" className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <span
                        className={`${TABLE_STATUS_CHIP_BASE} ${
                          provider.active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                        }`}
                      >
                        {provider.active ? 'نشطة' : 'موقوفة'}
                      </span>
                      {provider.is_internal_default ? (
                        <span className={`${TABLE_STATUS_CHIP_BASE} bg-sky-100 text-sky-700`}>افتراضية</span>
                      ) : null}
                    </div>
                  </td>
                  <td data-label="الإجراءات" className="px-4 py-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap gap-2">
                        {provider.is_internal_default ? (
                          <span className={`${TABLE_STATUS_CHIP_BASE} bg-sky-100 text-sky-700`}>جهة داخلية ثابتة</span>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => openEdit(provider)}
                              className={`${TABLE_ACTION_BUTTON_BASE} border-gray-300 text-gray-700`}
                              disabled={busy}
                            >
                              تعديل
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                onUpdateProvider(provider.id, {
                                  account_user_id: provider.account_user_id ?? null,
                                  name: provider.name,
                                  provider_type:
                                    provider.provider_type === 'internal_team' ? 'internal_team' : 'partner_company',
                                  active: !provider.active,
                                })
                              }
                              className={`${TABLE_ACTION_BUTTON_BASE} ${
                                provider.active ? 'border-amber-300 text-amber-700' : 'border-emerald-300 text-emerald-700'
                              }`}
                              disabled={busy}
                            >
                              {provider.active ? 'تعطيل' : 'تفعيل'}
                            </button>
                            {provider.can_delete ? (
                              <button
                                type="button"
                                onClick={() => {
                                  if (window.confirm(`هل تريد حذف جهة "${provider.name}" نهائيًا؟`)) {
                                    onDeleteProvider(provider.id);
                                  }
                                }}
                                className={`${TABLE_ACTION_BUTTON_BASE} border-rose-300 text-rose-700`}
                                disabled={busy}
                              >
                                حذف
                              </button>
                            ) : null}
                          </>
                        )}
                      </div>
                      {!provider.can_delete && provider.delete_block_reason ? (
                        <p className="text-xs leading-6 text-[var(--text-muted)]">{provider.delete_block_reason}</p>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
              {providers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-[var(--text-muted)]">
                    لا توجد جهات توصيل بعد.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={open}
        onClose={() => {
          setOpen(false);
          setModalStep('identity');
        }}
        title={editingProvider ? 'تعديل جهة التوصيل' : 'إضافة جهة توصيل'}
        description={
          editingProvider
            ? 'أكمل بيانات الجهة خطوة بخطوة ثم احفظها.'
            : 'أنشئ الجهة وحساب لوحتها في مسار واحد واضح.'
        }
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const payloadBase = {
              name: form.name.trim(),
              provider_type: form.provider_type,
              active: form.active,
            };
            if (!payloadBase.name || busy) return;

            if (editingProvider) {
              onUpdateProvider(editingProvider.id, {
                ...payloadBase,
                account_user_id: requiresProviderAccount ? form.account_user_id : null,
              });
              return;
            }

            onCreateProvider({
              ...payloadBase,
              account_user_id: requiresProviderAccount && usingLinkedAccount ? form.account_user_id : null,
              account_user:
                requiresProviderAccount && usingNewAccount
                  ? {
                      name: form.account.name.trim(),
                      username: form.account.username.trim(),
                      password: form.account.password,
                      active: form.account.active,
                    }
                  : null,
            });
          }}
          className="space-y-4"
        >
          <div className="grid gap-2 sm:grid-cols-3">
            {(
              [
                { id: 'identity', label: '1. تعريف الجهة' },
                { id: 'account', label: '2. حساب اللوحة' },
                { id: 'review', label: '3. المراجعة' },
              ] as Array<{ id: ProviderModalStep; label: string }>
            ).map((stepCard) => {
              const active = modalStep === stepCard.id;
              return (
                <button
                  key={stepCard.id}
                  type="button"
                  onClick={() => {
                    if (stepCard.id === 'identity') {
                      setModalStep('identity');
                      return;
                    }
                    if (stepCard.id === 'account' && providerIdentityError) {
                      return;
                    }
                    if (stepCard.id === 'review' && (providerIdentityError || providerAccountError)) {
                      return;
                    }
                    setModalStep(stepCard.id);
                  }}
                  className={`rounded-2xl border px-3 py-3 text-right transition ${
                    active
                      ? 'border-[var(--accent-strong)] bg-[var(--surface-card-soft)] text-[var(--text-primary-strong)]'
                      : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]'
                  }`}
                >
                  <span className="block text-sm font-black">{stepCard.label}</span>
                  <span className="mt-1 block text-xs">{active ? 'أنت هنا الآن' : 'انتقل لهذا الجزء'}</span>
                </button>
              );
            })}
          </div>

          {modalStep === 'identity' ? (
            <div className="grid gap-3">
              <label className="space-y-1">
                <span className="form-label">اسم الجهة</span>
                <input
                  className="form-input"
                  value={form.name}
                  onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                  required
                />
              </label>

              <label className="space-y-1">
                <span className="form-label">نوع الجهة</span>
                <select
                  className="form-select"
                  value={form.provider_type}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      provider_type: event.target.value as ProviderType,
                      account_mode: event.target.value === 'partner_company' ? prev.account_mode : 'create',
                      account_user_id: event.target.value === 'partner_company' ? prev.account_user_id : null,
                    }))
                  }
                >
                  <option value="partner_company">شركة توصيل</option>
                  <option value="internal_team">فريق داخلي</option>
                </select>
              </label>

              <label className="flex items-center gap-2 rounded-2xl border border-[var(--console-border)] px-3 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(event) => setForm((prev) => ({ ...prev, active: event.target.checked }))}
                />
                الجهة نشطة
              </label>
            </div>
          ) : null}

          {modalStep === 'account' ? (
            requiresProviderAccount ? (
              <div className="space-y-3 rounded-2xl border border-[var(--console-border)] p-3">
                <div className="space-y-1">
                  <p className="text-sm font-black text-[var(--text-primary-strong)]">حساب لوحة الجهة</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {editingProvider
                      ? 'راجع ربط الحساب الحالي أو استبدله بحساب آخر متاح.'
                      : 'اختر إنشاء حساب جديد أو ربط حساب موجود لهذه الجهة.'}
                  </p>
                </div>

                {!editingProvider ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className={`rounded-full border px-3 py-1 text-xs font-black ${
                        form.account_mode === 'create'
                          ? 'border-[var(--accent-soft)] bg-[var(--surface-card-soft)] text-[var(--text-primary-strong)]'
                          : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]'
                      }`}
                      onClick={() => setForm((prev) => ({ ...prev, account_mode: 'create', account_user_id: null }))}
                    >
                      إنشاء حساب جديد
                    </button>
                    {supportsLinkingExisting ? (
                      <button
                        type="button"
                        className={`rounded-full border px-3 py-1 text-xs font-black ${
                          form.account_mode === 'link'
                            ? 'border-[var(--accent-soft)] bg-[var(--surface-card-soft)] text-[var(--text-primary-strong)]'
                            : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]'
                        }`}
                        onClick={() => setForm((prev) => ({ ...prev, account_mode: 'link' }))}
                      >
                        ربط حساب موجود
                      </button>
                    ) : null}
                  </div>
                ) : null}

                {usingLinkedAccount ? (
                  <label className="space-y-1">
                    <span className="form-label">الحساب المرتبط</span>
                    <select
                      className="form-select"
                      value={form.account_user_id ?? ''}
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          account_user_id: event.target.value ? Number(event.target.value) : null,
                        }))
                      }
                    >
                      <option value="">اختر حساب لوحة جهة التوصيل</option>
                      {accountOptions.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.name} ({user.username})
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}

                {usingNewAccount ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="space-y-1">
                      <span className="form-label">اسم صاحب اللوحة</span>
                      <input
                        className="form-input"
                        value={form.account.name}
                        onChange={(event) =>
                          setForm((prev) => ({ ...prev, account: { ...prev.account, name: event.target.value } }))
                        }
                        required={usingNewAccount}
                      />
                    </label>
                    <label className="space-y-1">
                      <span className="form-label">اسم المستخدم</span>
                      <input
                        className="form-input"
                        value={form.account.username}
                        onChange={(event) =>
                          setForm((prev) => ({ ...prev, account: { ...prev.account, username: event.target.value } }))
                        }
                        dir="ltr"
                        required={usingNewAccount}
                      />
                    </label>
                    <label className="space-y-1 md:col-span-2">
                      <span className="form-label">كلمة المرور</span>
                      <input
                        type="password"
                        className="form-input"
                        value={form.account.password}
                        onChange={(event) =>
                          setForm((prev) => ({ ...prev, account: { ...prev.account, password: event.target.value } }))
                        }
                        required={usingNewAccount}
                      />
                    </label>
                    <label className="flex items-center gap-2 rounded-2xl border border-[var(--console-border)] px-3 py-2 text-sm md:col-span-2">
                      <input
                        type="checkbox"
                        checked={form.account.active}
                        onChange={(event) =>
                          setForm((prev) => ({ ...prev, account: { ...prev.account, active: event.target.checked } }))
                        }
                      />
                      حساب اللوحة نشط
                    </label>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="rounded-2xl border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-700">
                الجهة الداخلية لا تحتاج حساب لوحة مستقل من هذا المسار.
              </div>
            )
          ) : null}

          {modalStep === 'review' ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3">
                <p className="text-xs font-bold text-[var(--text-muted)]">الجهة</p>
                <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">{form.name || '—'}</p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{providerTypeLabel(form.provider_type)}</p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">{form.active ? 'الجهة نشطة' : 'الجهة موقوفة'}</p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3">
                <p className="text-xs font-bold text-[var(--text-muted)]">حساب اللوحة</p>
                <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">
                  {requiresProviderAccount
                    ? usingLinkedAccount
                      ? accountOptions.find((user) => user.id === form.account_user_id)?.name || 'حساب مرتبط'
                      : form.account.name || 'حساب جديد'
                    : 'غير مطلوب'}
                </p>
                <p className="mt-1 text-xs text-[var(--text-muted)]" dir="ltr">
                  {requiresProviderAccount
                    ? usingLinkedAccount
                      ? `@${accountOptions.find((user) => user.id === form.account_user_id)?.username || ''}`
                      : `@${form.account.username || ''}`
                    : 'لا يوجد ربط لوحة'}
                </p>
              </div>
            </div>
          ) : null}

          <div className="flex gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setOpen(false);
                setModalStep('identity');
              }}
            >
              إلغاء
            </button>
            {modalStep !== 'identity' ? (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setModalStep(modalStep === 'review' ? 'account' : 'identity')}
              >
                رجوع
              </button>
            ) : null}
            {modalStep === 'identity' ? (
              <button
                type="button"
                className="btn-primary"
                disabled={Boolean(providerIdentityError)}
                onClick={() => setModalStep('account')}
              >
                متابعة حساب اللوحة
              </button>
            ) : null}
            {modalStep === 'account' ? (
              <button
                type="button"
                className="btn-primary"
                disabled={Boolean(providerIdentityError || providerAccountError)}
                onClick={() => setModalStep('review')}
              >
                مراجعة الجهة
              </button>
            ) : null}
            {modalStep === 'review' ? (
              <button type="submit" className="btn-primary" disabled={busy || Boolean(providerIdentityError || providerAccountError)}>
                {busy ? 'جارٍ الحفظ...' : 'حفظ'}
              </button>
            ) : null}
          </div>
          {error ? <p className="text-sm font-semibold text-rose-400">{error}</p> : null}
        </form>
      </Modal>
    </section>
  );
}
