import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { DeliveryDriver, DeliveryProvider } from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';
import { TABLE_ACTION_BUTTON_BASE, TABLE_STATUS_CHIP_BASE } from '@/shared/ui/tableAppearance';

interface DeliveryDriversPanelProps {
  drivers: DeliveryDriver[];
  providers: DeliveryProvider[];
  onCreateDriver: (payload: {
    name: string;
    provider_id: number | null;
    phone: string;
    vehicle: string | null;
    active: boolean;
  }) => void;
  onUpdateDriver: (
    driverId: number,
    payload: {
      provider_id: number | null;
      name: string;
      phone: string;
      vehicle: string | null;
      status: DeliveryDriver['status'];
      active: boolean;
    }
  ) => void;
  onDeleteDriver: (driverId: number) => void;
  creating: boolean;
  updating: boolean;
  deleting?: boolean;
  createError?: string;
  updateError?: string;
  title?: string;
  description?: string;
}

type DriverModalStep = 'identity' | 'assignment' | 'review';
type TelegramModalStep = 'status' | 'actions';

function driverStatusLabel(status: DeliveryDriver['status']) {
  if (status === 'available') return 'متاح';
  if (status === 'busy') return 'مشغول';
  return 'متوقف';
}

function formatDateTime(value?: string | null) {
  if (!value) return 'غير مربوط بعد';
  return new Date(value).toLocaleString('ar-DZ-u-nu-latn');
}

function driverStatusTone(status: DeliveryDriver['status']) {
  if (status === 'available') return 'bg-emerald-100 text-emerald-700';
  if (status === 'busy') return 'bg-amber-100 text-amber-700';
  return 'bg-stone-200 text-stone-700';
}

function driverTelegramStateLabel(link?: {
  linked: boolean;
  has_active_task: boolean;
  has_open_offer: boolean;
}) {
  if (!link?.linked) return 'غير مربوط';
  if (link.has_active_task) return 'لديه مهمة جارية';
  if (link.has_open_offer) return 'لديه عرض مفتوح';
  return 'جاهز للاستقبال';
}

export function DeliveryDriversPanel({
  drivers,
  providers,
  onCreateDriver,
  onUpdateDriver,
  onDeleteDriver,
  creating,
  updating,
  deleting = false,
  createError,
  updateError,
  title = 'السائقون',
  description = 'أضف السائقين الداخليين وعدّل بياناتهم واربط Telegram عند الحاجة.',
}: DeliveryDriversPanelProps) {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();
  const [editingDriver, setEditingDriver] = useState<DeliveryDriver | null>(null);
  const [driverModalOpen, setDriverModalOpen] = useState(false);
  const [telegramModalOpen, setTelegramModalOpen] = useState(false);
  const [driverModalStep, setDriverModalStep] = useState<DriverModalStep>('identity');
  const [telegramModalStep, setTelegramModalStep] = useState<TelegramModalStep>('status');
  const [driverModalError, setDriverModalError] = useState<string | null>(null);
  const [telegramActionMessage, setTelegramActionMessage] = useState<string | null>(null);
  const [driverForm, setDriverForm] = useState({
    provider_id: null as number | null,
    name: '',
    phone: '',
    vehicle: '',
    status: 'available' as DeliveryDriver['status'],
    active: true,
  });

  const internalProvider = useMemo(
    () => providers.find((provider) => provider.is_internal_default) ?? providers[0] ?? null,
    [providers]
  );
  const activeDriversCount = useMemo(() => drivers.filter((driver) => driver.active).length, [drivers]);
  const actionBusy = creating || updating || deleting;
  const isCreateMode = editingDriver === null;
  const canSubmitDriver =
    driverForm.name.trim().length > 0 &&
    driverForm.phone.trim().length > 0 &&
    !(isCreateMode ? creating : updating || deleting);
  const driverIdentityError =
    driverForm.name.trim().length === 0
      ? 'أدخل اسم السائق أولًا.'
      : driverForm.phone.trim().length === 0
        ? 'أدخل رقم هاتف السائق أولًا.'
        : null;
  const driverAssignmentError =
    editingDriver && !driverForm.provider_id ? 'اختر جهة التوصيل لهذا السائق.' : null;
  const driverIdentityReady = driverIdentityError === null;
  const driverAssignmentReady = driverAssignmentError === null;

  const telegramLinkQuery = useQuery({
    queryKey: ['manager-driver-telegram-link', editingDriver?.id],
    queryFn: () => api.managerDriverTelegramLinkStatus(role ?? 'manager', editingDriver!.id),
    enabled: role === 'manager' && telegramModalOpen && editingDriver !== null,
  });

  const refreshTelegramLink = () => {
    if (!editingDriver) return;
    queryClient.invalidateQueries({ queryKey: ['manager-driver-telegram-link', editingDriver.id] });
    queryClient.invalidateQueries({ queryKey: ['manager-drivers'] });
  };

  const handleTelegramActionSuccess = (result: { action_message?: string | null }) => {
    setTelegramActionMessage(result.action_message ?? null);
    refreshTelegramLink();
  };

  const createTelegramLinkMutation = useMutation({
    mutationFn: () => api.managerCreateDriverTelegramLink(role ?? 'manager', editingDriver!.id),
    onSuccess: handleTelegramActionSuccess,
  });

  const clearTelegramLinkMutation = useMutation({
    mutationFn: () => api.managerClearDriverTelegramLink(role ?? 'manager', editingDriver!.id),
    onSuccess: handleTelegramActionSuccess,
  });

  const sendTelegramTestMutation = useMutation({
    mutationFn: () => api.managerSendDriverTelegramTestMessage(role ?? 'manager', editingDriver!.id),
    onSuccess: handleTelegramActionSuccess,
  });

  const resendTelegramFlowMutation = useMutation({
    mutationFn: () => api.managerResendDriverTelegramFlow(role ?? 'manager', editingDriver!.id),
    onSuccess: handleTelegramActionSuccess,
  });

  const openCreateDriverModal = () => {
    setEditingDriver(null);
    setDriverModalStep('identity');
    setDriverModalError(null);
    setDriverForm({
      provider_id: internalProvider?.id ?? null,
      name: '',
      phone: '',
      vehicle: '',
      status: 'available',
      active: true,
    });
    setDriverModalOpen(true);
  };

  const openDriverModal = (driver: DeliveryDriver) => {
    setEditingDriver(driver);
    setDriverModalStep('identity');
    setDriverModalError(null);
    setDriverForm({
      provider_id: driver.provider_id ?? null,
      name: driver.name ?? '',
      phone: driver.phone ?? '',
      vehicle: driver.vehicle ?? '',
      status: driver.status,
      active: driver.active,
    });
    setDriverModalOpen(true);
  };

  const openTelegramModal = (driver: DeliveryDriver) => {
    setEditingDriver(driver);
    setTelegramModalStep('status');
    setTelegramActionMessage(null);
    setTelegramModalOpen(true);
  };

  const closeDriverModal = () => {
    setDriverModalOpen(false);
    setDriverModalStep('identity');
    setDriverModalError(null);
    if (!telegramModalOpen) {
      setEditingDriver(null);
    }
  };

  const closeTelegramModal = () => {
    setTelegramModalOpen(false);
    setTelegramModalStep('status');
    setTelegramActionMessage(null);
    if (!driverModalOpen) {
      setEditingDriver(null);
    }
  };

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-black text-[var(--text-primary-strong)]">{title}</h3>
          <p className="mt-1 text-xs text-[var(--text-muted)]">{description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div
            className={`${TABLE_STATUS_CHIP_BASE} border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)]`}
          >
            السائقون النشطون: {activeDriversCount} / {drivers.length}
          </div>
          <button type="button" className="btn-secondary ui-size-sm" onClick={openCreateDriverModal}>
            إضافة سائق داخلي
          </button>
        </div>
      </div>

      <div className="admin-table-shell">
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-[var(--surface-card-subtle)] text-[var(--text-secondary)]">
              <tr>
                <th className="px-4 py-3 font-bold">السائق</th>
                <th className="px-4 py-3 font-bold">الجهة</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">Telegram</th>
                <th className="px-4 py-3 font-bold">الهاتف / المركبة</th>
                <th className="px-4 py-3 font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {drivers.map((driver) => (
                <tr key={driver.id} className="border-t border-[var(--console-border)] align-top">
                  <td data-label="السائق" className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="font-black text-[var(--text-primary-strong)]">{driver.name}</p>
                      <p className="text-xs text-[var(--text-muted)]">مرجع السائق #{driver.id}</p>
                    </div>
                  </td>
                  <td data-label="الجهة" className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="font-black text-[var(--text-primary-strong)]">
                        {driver.provider_name || 'الفريق الداخلي'}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">انتماء تشغيلي واحد فقط</p>
                    </div>
                  </td>
                  <td data-label="الحالة" className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <span className={`${TABLE_STATUS_CHIP_BASE} ${driverStatusTone(driver.status)}`}>
                        {driverStatusLabel(driver.status)}
                      </span>
                      <span
                        className={`${TABLE_STATUS_CHIP_BASE} ${
                          driver.active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                        }`}
                      >
                        {driver.active ? 'نشط' : 'موقوف'}
                      </span>
                    </div>
                  </td>
                  <td data-label="Telegram" className="px-4 py-3">
                    <div className="space-y-1">
                      <span
                        className={`${TABLE_STATUS_CHIP_BASE} ${
                          driver.telegram_enabled ? 'bg-sky-100 text-sky-700' : 'bg-stone-200 text-stone-700'
                        }`}
                      >
                        {driver.telegram_enabled ? 'مربوط' : 'غير مربوط'}
                      </span>
                      <p className="text-xs text-[var(--text-muted)]">
                        {driver.telegram_enabled ? 'الربط متاح ويعمل' : 'يحتاج إلى تفعيل الربط'}
                      </p>
                    </div>
                  </td>
                  <td data-label="الهاتف / المركبة" className="px-4 py-3">
                    <div className="space-y-1">
                      <p className="text-sm font-black text-[var(--text-primary-strong)]" dir="ltr">
                        {driver.phone}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">
                        {driver.vehicle || 'بدون مركبة محددة'}
                      </p>
                    </div>
                  </td>
                  <td data-label="الإجراءات" className="px-4 py-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => openDriverModal(driver)}
                          className={`${TABLE_ACTION_BUTTON_BASE} border-gray-300 text-gray-700`}
                          disabled={actionBusy}
                        >
                          بيانات السائق
                        </button>
                        <button
                          type="button"
                          onClick={() => openTelegramModal(driver)}
                          className={`${TABLE_ACTION_BUTTON_BASE} border-sky-300 text-sky-700`}
                          disabled={actionBusy}
                        >
                          ربط Telegram
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            onUpdateDriver(driver.id, {
                              provider_id: driver.provider_id ?? null,
                              name: driver.name,
                              phone: driver.phone,
                              vehicle: driver.vehicle ?? null,
                              status: driver.active ? 'inactive' : 'available',
                              active: !driver.active,
                            })
                          }
                          className={`${TABLE_ACTION_BUTTON_BASE} ${
                            driver.active ? 'border-amber-300 text-amber-700' : 'border-emerald-300 text-emerald-700'
                          }`}
                          disabled={actionBusy}
                        >
                          {driver.active ? 'تعطيل' : 'تفعيل'}
                        </button>
                        {driver.can_delete ? (
                          <button
                            type="button"
                            onClick={() => {
                              if (window.confirm(`هل تريد حذف السائق "${driver.name}" نهائيًا؟`)) {
                                onDeleteDriver(driver.id);
                              }
                            }}
                            className={`${TABLE_ACTION_BUTTON_BASE} border-rose-300 text-rose-700`}
                            disabled={actionBusy}
                          >
                            حذف
                          </button>
                        ) : null}
                      </div>
                      {!driver.can_delete && driver.delete_block_reason ? (
                        <p className="text-xs leading-6 text-[var(--text-muted)]">{driver.delete_block_reason}</p>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
              {drivers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-[var(--text-muted)]">
                    لا يوجد سائقون بعد.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={driverModalOpen}
        onClose={closeDriverModal}
        title={editingDriver ? `بيانات السائق #${editingDriver.id}` : 'إضافة سائق داخلي جديد'}
        description={editingDriver ? 'أكمل بيانات السائق خطوة بخطوة ثم احفظها.' : 'أدخل بيانات السائق الداخلي ثم راجعه قبل الإنشاء.'}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setDriverModalError(null);
            if (!driverIdentityReady) {
              setDriverModalStep('identity');
              setDriverModalError(driverIdentityError);
              return;
            }
            if (!driverAssignmentReady) {
              setDriverModalStep('assignment');
              setDriverModalError(driverAssignmentError);
              return;
            }

            if (editingDriver) {
              onUpdateDriver(editingDriver.id, {
                provider_id: driverForm.provider_id,
                name: driverForm.name.trim(),
                phone: driverForm.phone.trim(),
                vehicle: driverForm.vehicle.trim() || null,
                status: driverForm.status,
                active: driverForm.active,
              });
              return;
            }

            onCreateDriver({
              name: driverForm.name.trim(),
              provider_id: driverForm.provider_id,
              phone: driverForm.phone.trim(),
              vehicle: driverForm.vehicle.trim() || null,
              active: driverForm.active,
            });
          }}
          className="space-y-4"
        >
          <div className="grid gap-2 sm:grid-cols-3">
            {(
              [
                { id: 'identity', label: '1. الهوية', ready: driverIdentityReady },
                { id: 'assignment', label: '2. الانتماء والحالة', ready: driverIdentityReady && driverAssignmentReady },
                { id: 'review', label: '3. المراجعة', ready: driverIdentityReady && driverAssignmentReady },
              ] as Array<{ id: DriverModalStep; label: string; ready: boolean }>
            ).map((stepCard) => {
              const active = driverModalStep === stepCard.id;
              return (
                <button
                  key={stepCard.id}
                  type="button"
                  onClick={() => {
                    if (stepCard.id === 'identity') {
                      setDriverModalStep('identity');
                      return;
                    }
                    if (stepCard.id === 'assignment') {
                      if (!driverIdentityReady) {
                        setDriverModalStep('identity');
                        setDriverModalError(driverIdentityError);
                        return;
                      }
                      setDriverModalStep('assignment');
                      return;
                    }
                    if (!driverIdentityReady) {
                      setDriverModalStep('identity');
                      setDriverModalError(driverIdentityError);
                      return;
                    }
                    if (!driverAssignmentReady) {
                      setDriverModalStep('assignment');
                      setDriverModalError(driverAssignmentError);
                      return;
                    }
                    setDriverModalStep('review');
                  }}
                  className={`rounded-2xl border px-3 py-3 text-right transition ${
                    active
                      ? 'border-[var(--accent-strong)] bg-[var(--surface-card-soft)] text-[var(--text-primary-strong)]'
                      : stepCard.ready
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                        : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]'
                  }`}
                >
                  <span className="block text-sm font-black">{stepCard.label}</span>
                  <span className="mt-1 block text-xs">
                    {active ? 'أنت هنا الآن' : stepCard.ready ? 'مكتملة' : 'لم تكتمل بعد'}
                  </span>
                </button>
              );
            })}
          </div>

          {driverModalStep !== 'identity' ? (
            <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-[var(--text-muted)]">ملخص الهوية</p>
                  <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">{driverForm.name || '—'}</p>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]" dir="ltr">
                    {driverForm.phone || '—'}
                  </p>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">
                    {driverForm.vehicle.trim() || 'بدون مركبة محددة'}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-secondary ui-size-sm"
                  onClick={() => setDriverModalStep('identity')}
                >
                  تعديل الهوية
                </button>
              </div>
            </div>
          ) : null}

          {driverModalStep === 'identity' ? (
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1">
                <span className="form-label">الاسم</span>
                <input
                  className="form-input"
                  value={driverForm.name}
                  onChange={(event) => setDriverForm((prev) => ({ ...prev, name: event.target.value }))}
                  required
                />
              </label>

              <label className="space-y-1">
                <span className="form-label">الهاتف</span>
                <input
                  className="form-input"
                  value={driverForm.phone}
                  onChange={(event) => setDriverForm((prev) => ({ ...prev, phone: event.target.value }))}
                  required
                />
              </label>

              <label className="space-y-1 md:col-span-2">
                <span className="form-label">المركبة</span>
                <input
                  className="form-input"
                  value={driverForm.vehicle}
                  onChange={(event) => setDriverForm((prev) => ({ ...prev, vehicle: event.target.value }))}
                />
              </label>
            </div>
          ) : null}

          {driverModalStep === 'assignment' ? (
            <div className="space-y-3">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-sm text-[var(--text-secondary)]">
                {editingDriver ? (
                  <>
                    الجهة الحالية:{' '}
                    <span className="font-bold text-[var(--text-primary-strong)]">
                      {editingDriver.provider_name || 'الفريق الداخلي'}
                    </span>
                  </>
                ) : (
                  <>
                    الجهة عند الإنشاء الإداري:{' '}
                    <span className="font-bold text-[var(--text-primary-strong)]">
                      {internalProvider?.name ?? 'الفريق الداخلي'}
                    </span>
                  </>
                )}
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {editingDriver ? (
                  <>
                    <label className="space-y-1 md:col-span-2">
                      <span className="form-label">جهة التوصيل</span>
                      <select
                        className="form-select"
                        value={driverForm.provider_id ?? ''}
                        onChange={(event) =>
                          setDriverForm((prev) => ({
                            ...prev,
                            provider_id: event.target.value ? Number(event.target.value) : null,
                          }))
                        }
                      >
                        {providers.map((provider) => (
                          <option key={provider.id} value={provider.id}>
                            {provider.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="space-y-1">
                      <span className="form-label">الحالة</span>
                      <select
                        className="form-select"
                        value={driverForm.status}
                        onChange={(event) =>
                          setDriverForm((prev) => ({
                            ...prev,
                            status: event.target.value as DeliveryDriver['status'],
                          }))
                        }
                      >
                        <option value="available">متاح</option>
                        <option value="busy">مشغول</option>
                        <option value="inactive">متوقف</option>
                      </select>
                    </label>
                  </>
                ) : (
                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-sm text-[var(--text-secondary)] md:col-span-2">
                    سيبدأ السائق متاحًا إذا كان السجل نشطًا.
                  </div>
                )}

                <label className="flex items-center gap-2 rounded-2xl border border-[var(--console-border)] px-3 py-2 text-sm md:col-span-2">
                  <input
                    type="checkbox"
                    checked={driverForm.active}
                    onChange={(event) => setDriverForm((prev) => ({ ...prev, active: event.target.checked }))}
                  />
                  السجل نشط
                </label>
              </div>
            </div>
          ) : null}

          {driverModalStep === 'review' ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3">
                <p className="text-xs font-bold text-[var(--text-muted)]">الهوية</p>
                <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">{driverForm.name}</p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]" dir="ltr">
                  {driverForm.phone}
                </p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  {driverForm.vehicle.trim() || 'بدون مركبة محددة'}
                </p>
              </div>

              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3">
                <p className="text-xs font-bold text-[var(--text-muted)]">الانتماء والحالة</p>
                <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">
                  {editingDriver
                    ? providers.find((provider) => provider.id === driverForm.provider_id)?.name ||
                      editingDriver.provider_name ||
                      'الفريق الداخلي'
                    : internalProvider?.name ?? 'الفريق الداخلي'}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {editingDriver ? driverStatusLabel(driverForm.status) : 'متاح عند التفعيل'}
                </p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">{driverForm.active ? 'السجل نشط' : 'السجل موقوف'}</p>
              </div>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={closeDriverModal}>
              إغلاق
            </button>
            {driverModalStep !== 'identity' ? (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setDriverModalStep(driverModalStep === 'review' ? 'assignment' : 'identity')}
              >
                رجوع
              </button>
            ) : null}
            {driverModalStep === 'identity' ? (
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  if (!driverIdentityReady) {
                    setDriverModalError(driverIdentityError);
                    return;
                  }
                  setDriverModalError(null);
                  setDriverModalStep('assignment');
                }}
              >
                متابعة الانتماء
              </button>
            ) : null}
            {driverModalStep === 'assignment' ? (
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  if (!driverAssignmentReady) {
                    setDriverModalError(driverAssignmentError);
                    return;
                  }
                  setDriverModalError(null);
                  setDriverModalStep('review');
                }}
              >
                مراجعة السائق
              </button>
            ) : null}
            {driverModalStep === 'review' ? (
              <button type="submit" className="btn-primary" disabled={!canSubmitDriver}>
                {editingDriver
                  ? updating
                    ? 'جارٍ الحفظ...'
                    : 'حفظ بيانات السائق'
                  : creating
                    ? 'جارٍ إنشاء السائق...'
                    : 'إنشاء السائق'}
              </button>
            ) : null}
          </div>

          {driverModalError ? <p className="text-sm font-semibold text-rose-400">{driverModalError}</p> : null}
          {editingDriver && updateError ? <p className="text-sm font-semibold text-rose-400">{updateError}</p> : null}
          {!editingDriver && createError ? <p className="text-sm font-semibold text-rose-400">{createError}</p> : null}
        </form>
      </Modal>

      <Modal
        open={telegramModalOpen}
        onClose={closeTelegramModal}
        title={editingDriver ? `Telegram للسائق #${editingDriver.id}` : 'ربط Telegram'}
        description="راجع حالة الربط أولًا، ثم نفذ إجراء الدعم الذي تحتاجه."
      >
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2">
            {(
              [
                { id: 'status', label: '1. حالة الربط' },
                { id: 'actions', label: '2. إجراءات الدعم' },
              ] as Array<{ id: TelegramModalStep; label: string }>
            ).map((stepCard) => {
              const active = telegramModalStep === stepCard.id;
              return (
                <button
                  key={stepCard.id}
                  type="button"
                  onClick={() => setTelegramModalStep(stepCard.id)}
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

          {telegramLinkQuery.isLoading ? (
            <p className="text-sm text-[var(--text-muted)]">جارٍ تحميل حالة الربط...</p>
          ) : null}
          {telegramLinkQuery.isError ? (
            <p className="text-sm font-semibold text-rose-700">{(telegramLinkQuery.error as Error).message}</p>
          ) : null}

          {telegramLinkQuery.data ? (
            <>
              {telegramModalStep === 'status' ? (
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                    <p className="text-xs font-bold text-[var(--text-muted)]">الحالة</p>
                    <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                      {telegramLinkQuery.data.linked ? 'مربوط' : 'غير مربوط'}
                    </p>
                    <p className="mt-1 text-xs font-semibold text-[var(--text-secondary)]">
                      {driverTelegramStateLabel(telegramLinkQuery.data)}
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      آخر ربط: {formatDateTime(telegramLinkQuery.data.telegram_linked_at)}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      اسم المستخدم: {telegramLinkQuery.data.telegram_username || '-'}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      الجهة: {telegramLinkQuery.data.provider_name || 'الفريق الداخلي'}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                    <p className="text-xs font-bold text-[var(--text-muted)]">رابط الربط</p>
                    <p className="mt-1 break-all font-mono text-xs text-[var(--text-primary-strong)]">
                      {telegramLinkQuery.data.deep_link || 'أنشئ رابط الربط عند الحاجة.'}
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      ينتهي الرابط: {formatDateTime(telegramLinkQuery.data.link_expires_at)}
                    </p>
                    {telegramLinkQuery.data.deep_link ? (
                      <button
                        type="button"
                        className="btn-secondary ui-size-sm mt-3"
                        onClick={() => navigator.clipboard.writeText(telegramLinkQuery.data.deep_link ?? '')}
                      >
                        نسخ الرابط
                      </button>
                    ) : null}
                  </div>

                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                    <p className="text-xs font-bold text-[var(--text-muted)]">المهمة الحالية</p>
                    <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                      {telegramLinkQuery.data.has_active_task
                        ? `الطلب #${telegramLinkQuery.data.active_order_id}`
                        : 'لا توجد مهمة جارية'}
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      {telegramLinkQuery.data.active_order_status || '—'}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                    <p className="text-xs font-bold text-[var(--text-muted)]">العرض المفتوح</p>
                    <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                      {telegramLinkQuery.data.has_open_offer
                        ? `الطلب #${telegramLinkQuery.data.offered_order_id}`
                        : 'لا يوجد عرض مفتوح'}
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      {telegramLinkQuery.data.offered_order_status || '—'}
                    </p>
                  </div>
                </div>
              ) : null}

              {telegramModalStep === 'actions' ? (
                <div className="space-y-3">
                  <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                    <p className="text-xs font-bold text-[var(--text-muted)]">ملخص سريع</p>
                    <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                      {editingDriver?.name || 'السائق المحدد'}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      {telegramLinkQuery.data.provider_name || 'الفريق الداخلي'}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      {driverTelegramStateLabel(telegramLinkQuery.data)}
                    </p>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">
                    <button
                      type="button"
                      className="btn-secondary ui-size-sm"
                      disabled={!editingDriver || createTelegramLinkMutation.isPending}
                      onClick={() => createTelegramLinkMutation.mutate()}
                    >
                      {createTelegramLinkMutation.isPending ? 'جارٍ الإنشاء...' : 'إنشاء رابط ربط'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary ui-size-sm"
                      disabled={!editingDriver || clearTelegramLinkMutation.isPending}
                      onClick={() => clearTelegramLinkMutation.mutate()}
                    >
                      {clearTelegramLinkMutation.isPending ? 'جارٍ الفك...' : 'فك الربط'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary ui-size-sm"
                      disabled={!editingDriver || sendTelegramTestMutation.isPending}
                      onClick={() => sendTelegramTestMutation.mutate()}
                    >
                      {sendTelegramTestMutation.isPending ? 'جارٍ الإرسال...' : 'رسالة اختبار'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary ui-size-sm"
                      disabled={!editingDriver || resendTelegramFlowMutation.isPending}
                      onClick={() => resendTelegramFlowMutation.mutate()}
                    >
                      {resendTelegramFlowMutation.isPending ? 'جارٍ الإرسال...' : 'إعادة إرسال آخر مهمة/عرض'}
                    </button>
                  </div>
                </div>
              ) : null}
            </>
          ) : null}

          {telegramLinkQuery.data?.recovery_hint ? (
            <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3 text-xs text-[var(--text-secondary)]">
              {telegramLinkQuery.data.recovery_hint}
            </div>
          ) : null}

          {telegramActionMessage ? (
            <p className="text-sm font-semibold text-emerald-700">{telegramActionMessage}</p>
          ) : null}
          {createTelegramLinkMutation.isError ? (
            <p className="text-sm font-semibold text-rose-700">
              {(createTelegramLinkMutation.error as Error).message}
            </p>
          ) : null}
          {clearTelegramLinkMutation.isError ? (
            <p className="text-sm font-semibold text-rose-700">
              {(clearTelegramLinkMutation.error as Error).message}
            </p>
          ) : null}
          {sendTelegramTestMutation.isError ? (
            <p className="text-sm font-semibold text-rose-700">
              {(sendTelegramTestMutation.error as Error).message}
            </p>
          ) : null}
          {resendTelegramFlowMutation.isError ? (
            <p className="text-sm font-semibold text-rose-700">
              {(resendTelegramFlowMutation.error as Error).message}
            </p>
          ) : null}
        </div>
      </Modal>
    </section>
  );
}

