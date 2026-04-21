import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  Edit3,
  KeyRound,
  PauseCircle,
  PlayCircle,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

import { api } from '@/shared/api/client';
import type { MasterAddon, MasterTenant, MasterTenantAccess, MasterTenantCreateResult } from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';
import { getTenantStateClass, getTenantStateLabel } from '../data/masterReadModel';

type CreateStep = 'client' | 'tenant' | 'access';
type ClientMode = 'existing' | 'new';
type TenantAddonStatus = MasterAddon['status'];
type TenantAddonRow = {
  addon: MasterAddon;
  status: TenantAddonStatus;
  canPause: boolean;
  canResume: boolean;
};

const PASSIVE_ADDON_IDS = new Set(['finance', 'intelligence', 'reports']);

function Field(props: {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  dir?: 'rtl' | 'ltr';
  readOnly?: boolean;
}) {
  const { label, value, onChange, placeholder, dir, readOnly } = props;
  return (
    <label className="block space-y-2">
      <span className="text-sm font-bold text-stone-700">{label}</span>
      <input
        dir={dir}
        value={value}
        onChange={onChange ? (event) => onChange(event.target.value) : undefined}
        readOnly={readOnly}
        placeholder={placeholder}
        className="form-input h-12 w-full rounded-2xl border-stone-300 bg-white text-stone-900 placeholder:text-stone-400"
      />
    </label>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-stone-300 bg-white px-4 py-3 shadow-sm">
      <p className="text-xs font-black tracking-[0.18em] text-stone-500">{label}</p>
      <p className="mt-2 text-sm font-black text-stone-900">{value}</p>
    </div>
  );
}

function StepCard({ label, active }: { label: string; active: boolean }) {
  return (
    <div
      className={`rounded-2xl border px-4 py-3 text-sm font-black shadow-sm ${
        active ? 'border-emerald-300 bg-emerald-50 text-emerald-950' : 'border-stone-300 bg-white text-stone-700'
      }`}
    >
      {label}
    </div>
  );
}

function ActionButton(props: {
  label: string;
  icon: typeof Edit3;
  tone?: 'default' | 'warning' | 'danger';
  disabled?: boolean;
  onClick: () => void;
}) {
  const { label, icon: Icon, tone = 'default', disabled, onClick } = props;
  const classes =
    tone === 'danger'
      ? 'border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100'
      : tone === 'warning'
        ? 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
        : 'border-stone-300 bg-white text-stone-800 hover:bg-stone-100';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-2xl border px-3 text-xs font-black transition disabled:cursor-wait disabled:opacity-60 ${classes}`}
    >
      <span>{label}</span>
      <Icon className="h-4 w-4" />
    </button>
  );
}

function getTenantAddonStatusLabel(status: TenantAddonStatus) {
  switch (status) {
    case 'active':
      return 'مفعّلة';
    case 'passive':
      return 'خلفية صامتة';
    case 'paused':
      return 'موقوفة مؤقتًا';
    default:
      return 'مغلقة';
  }
}

function getTenantAddonStatusClass(status: TenantAddonStatus) {
  switch (status) {
    case 'active':
      return 'border-emerald-300 bg-emerald-50 text-emerald-900';
    case 'passive':
      return 'border-sky-300 bg-sky-50 text-sky-900';
    case 'paused':
      return 'border-amber-300 bg-amber-50 text-amber-900';
    default:
      return 'border-stone-300 bg-stone-100 text-stone-700';
  }
}

function getTenantAddonHint(status: TenantAddonStatus, addon: MasterAddon) {
  if (status === 'passive') {
    return 'تجمع بياناتها بصمت في الخلفية، لكن واجهتها ما تزال مقفلة داخل نسخة المطعم.';
  }
  if (status === 'paused') {
    return 'الأداة موقوفة مؤقتًا مع الاحتفاظ ببياناتها السابقة.';
  }
  if (status === 'active') {
    return 'الأداة تعمل الآن داخل هذه النسخة.';
  }
  if (addon.prerequisite_label) {
    return `تحتاج إلى ${addon.prerequisite_label} أولًا قبل الوصول إليها.`;
  }
  return 'لم تُفتح هذه الأداة بعد داخل النسخة.';
}

function resolveTenantAddonStatus(
  tenant: MasterTenant,
  addon: MasterAddon,
  currentStageSequence: number
): TenantAddonStatus {
  if (addon.id === 'base') {
    return 'active';
  }
  if (tenant.paused_tools.includes(addon.id)) {
    return 'paused';
  }
  if (PASSIVE_ADDON_IDS.has(addon.id)) {
    return addon.sequence <= currentStageSequence ? 'active' : 'passive';
  }
  return addon.sequence <= currentStageSequence ? 'active' : 'locked';
}

function buildTenantAddonRows(tenant: MasterTenant, addons: MasterAddon[]): TenantAddonRow[] {
  const currentStageSequence = addons.find((addon) => addon.id === tenant.current_stage_id)?.sequence ?? 1;
  const highestActiveSequence = Math.max(
    0,
    ...addons
      .filter(
        (addon) =>
          addon.id !== 'base' &&
          !tenant.paused_tools.includes(addon.id) &&
          addon.sequence <= currentStageSequence
      )
      .map((addon) => addon.sequence)
  );
  const resumableSequence = tenant.paused_tools.length
    ? Math.min(
        ...tenant.paused_tools.map(
          (addonId) => addons.find((candidate) => candidate.id === addonId)?.sequence ?? Number.MAX_SAFE_INTEGER
        )
      )
    : null;

  return addons.map((addon) => {
    const status = resolveTenantAddonStatus(tenant, addon, currentStageSequence);
    return {
      addon,
      status,
      canPause: status === 'active' && addon.id !== 'base' && addon.sequence === highestActiveSequence,
      canResume: status === 'paused' && addon.sequence === resumableSequence,
    };
  });
}

export function MasterTenantsPage() {
  const queryClient = useQueryClient();

  const [createOpen, setCreateOpen] = useState(false);
  const [createStep, setCreateStep] = useState<CreateStep>('client');
  const [clientMode, setClientMode] = useState<ClientMode>('new');
  const [existingClientId, setExistingClientId] = useState('');
  const [clientOwnerName, setClientOwnerName] = useState('');
  const [clientBrandName, setClientBrandName] = useState('');
  const [clientPhone, setClientPhone] = useState('');
  const [clientCity, setClientCity] = useState('');
  const [tenantBrandName, setTenantBrandName] = useState('');
  const [tenantCode, setTenantCode] = useState('');
  const [databaseName, setDatabaseName] = useState('');
  const [createdResult, setCreatedResult] = useState<MasterTenantCreateResult | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const [editingTenant, setEditingTenant] = useState<MasterTenant | null>(null);
  const [editClientOwnerName, setEditClientOwnerName] = useState('');
  const [editClientBrandName, setEditClientBrandName] = useState('');
  const [editClientPhone, setEditClientPhone] = useState('');
  const [editClientCity, setEditClientCity] = useState('');
  const [editBrandName, setEditBrandName] = useState('');
  const [editActivationStageId, setEditActivationStageId] = useState('base');
  const [regeneratedAccess, setRegeneratedAccess] = useState<MasterTenantAccess | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MasterTenant | null>(null);
  const [addonActionId, setAddonActionId] = useState<string | null>(null);

  const tenantsQuery = useQuery({ queryKey: ['master-tenants'], queryFn: api.masterTenants });
  const clientsQuery = useQuery({ queryKey: ['master-clients'], queryFn: api.masterClients });
  const addonsQuery = useQuery({ queryKey: ['master-addons'], queryFn: api.masterAddons });

  const baseAddon = useMemo(() => addonsQuery.data?.find((addon) => addon.id === 'base') ?? null, [addonsQuery.data]);
  const editableAddons = useMemo(() => {
    if (!editingTenant || !addonsQuery.data) return [];
    const current = addonsQuery.data.find((addon) => addon.id === editingTenant.current_stage_id);
    return addonsQuery.data.filter((addon) => addon.sequence <= (current?.sequence ?? 1) + 1);
  }, [addonsQuery.data, editingTenant]);
  const tenantAddonRows = useMemo(() => {
    if (!editingTenant || !addonsQuery.data) return [];
    return buildTenantAddonRows(editingTenant, addonsQuery.data);
  }, [addonsQuery.data, editingTenant]);

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['master-overview'] }),
      queryClient.invalidateQueries({ queryKey: ['master-clients'] }),
      queryClient.invalidateQueries({ queryKey: ['master-tenants'] }),
      queryClient.invalidateQueries({ queryKey: ['master-addons'] }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: api.masterCreateTenant,
    onSuccess: async (result) => {
      setCreatedResult(result);
      setCreateStep('access');
      setCreateError(null);
      await invalidate();
    },
    onError: (error) => setCreateError(error instanceof Error ? error.message : 'تعذر إنشاء النسخة الآن.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ tenantId, payload }: { tenantId: string; payload: Parameters<typeof api.masterUpdateTenant>[1] }) =>
      api.masterUpdateTenant(tenantId, payload),
    onSuccess: async () => {
      setEditingTenant(null);
      setEditError(null);
      await invalidate();
    },
    onError: (error) => setEditError(error instanceof Error ? error.message : 'تعذر حفظ التعديل الآن.'),
  });

  const regenerateMutation = useMutation({
    mutationFn: api.masterRegenerateTenantPassword,
    onSuccess: (result) => setRegeneratedAccess(result),
    onError: (error) => setEditError(error instanceof Error ? error.message : 'تعذر إعادة التوليد الآن.'),
  });

  const pauseAddonMutation = useMutation({
    mutationFn: ({ tenantId, addonId }: { tenantId: string; addonId: string }) =>
      api.masterPauseTenantAddon(tenantId, addonId),
    onSuccess: async (tenant) => {
      setEditingTenant(tenant);
      setAddonActionId(null);
      setEditError(null);
      await invalidate();
    },
    onError: (error) => {
      setAddonActionId(null);
      setEditError(error instanceof Error ? error.message : 'تعذر إيقاف الأداة الآن.');
    },
  });

  const resumeAddonMutation = useMutation({
    mutationFn: ({ tenantId, addonId }: { tenantId: string; addonId: string }) =>
      api.masterResumeTenantAddon(tenantId, addonId),
    onSuccess: async (tenant) => {
      setEditingTenant(tenant);
      setAddonActionId(null);
      setEditError(null);
      await invalidate();
    },
    onError: (error) => {
      setAddonActionId(null);
      setEditError(error instanceof Error ? error.message : 'تعذر استئناف الأداة الآن.');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: api.masterToggleTenantSuspension,
    onSuccess: async () => {
      await invalidate();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.masterDeleteTenant,
    onSuccess: async () => {
      setDeleteTarget(null);
      await invalidate();
    },
  });

  const pageError =
    (tenantsQuery.error instanceof Error && tenantsQuery.error.message) ||
    (clientsQuery.error instanceof Error && clientsQuery.error.message) ||
    (addonsQuery.error instanceof Error && addonsQuery.error.message);

  function resetCreate() {
    setCreateStep('client');
    setClientMode('new');
    setExistingClientId('');
    setClientOwnerName('');
    setClientBrandName('');
    setClientPhone('');
    setClientCity('');
    setTenantBrandName('');
    setTenantCode('');
    setDatabaseName('');
    setCreatedResult(null);
    setCreateError(null);
  }

  function closeCreateModal() {
    setCreateOpen(false);
    resetCreate();
  }

  function closeEditModal() {
    setEditingTenant(null);
    setEditError(null);
    setRegeneratedAccess(null);
    setAddonActionId(null);
  }

  function closeDeleteModal() {
    setDeleteTarget(null);
  }

  function openCreateModal() {
    closeEditModal();
    closeDeleteModal();
    resetCreate();
    setCreateOpen(true);
  }

  function openEditTenant(tenant: MasterTenant) {
    closeCreateModal();
    closeDeleteModal();
    setEditingTenant(tenant);
    setEditClientOwnerName(tenant.client_owner_name);
    setEditClientBrandName(tenant.client_brand_name);
    setEditClientPhone(clientsQuery.data?.find((client) => client.id === tenant.client_id)?.phone ?? '');
    setEditClientCity(clientsQuery.data?.find((client) => client.id === tenant.client_id)?.city ?? '');
    setEditBrandName(tenant.brand_name);
    setEditActivationStageId(tenant.current_stage_id);
    setRegeneratedAccess(null);
    setEditError(null);
    setAddonActionId(null);
  }

  async function handleCreate() {
    if (createStep === 'client') {
      if (clientMode === 'existing' && !existingClientId) {
        setCreateError('اختر العميل أولًا.');
        return;
      }
      if (
        clientMode === 'new' &&
        (!clientOwnerName.trim() || !clientBrandName.trim() || !clientPhone.trim() || !clientCity.trim())
      ) {
        setCreateError('أكمل بيانات العميل أولًا.');
        return;
      }
      setCreateError(null);
      setCreateStep('tenant');
      return;
    }

    if (!tenantBrandName.trim()) {
      setCreateError('أدخل اسم النسخة.');
      return;
    }

    await createMutation.mutateAsync({
      client_mode: clientMode,
      existing_client_id: clientMode === 'existing' ? existingClientId : null,
      client_owner_name: clientMode === 'new' ? clientOwnerName : null,
      client_brand_name: clientMode === 'new' ? clientBrandName : null,
      client_phone: clientMode === 'new' ? clientPhone : null,
      client_city: clientMode === 'new' ? clientCity : null,
      tenant_brand_name: tenantBrandName,
      tenant_code: tenantCode || null,
      database_name: databaseName || null,
    });
  }

  async function handleSaveEdit() {
    if (!editingTenant) return;
    if (
      !editClientOwnerName.trim() ||
      !editClientBrandName.trim() ||
      !editClientPhone.trim() ||
      !editClientCity.trim() ||
      !editBrandName.trim()
    ) {
      setEditError('أكمل البيانات المطلوبة أولًا.');
      return;
    }

    await updateMutation.mutateAsync({
      tenantId: editingTenant.id,
      payload: {
        client_owner_name: editClientOwnerName.trim(),
        client_brand_name: editClientBrandName.trim(),
        client_phone: editClientPhone.trim(),
        client_city: editClientCity.trim(),
        brand_name: editBrandName.trim(),
        activation_stage_id: editActivationStageId,
      },
    });
  }

  async function handlePauseAddon(addonId: string) {
    if (!editingTenant) return;
    setAddonActionId(addonId);
    await pauseAddonMutation.mutateAsync({ tenantId: editingTenant.id, addonId });
  }

  async function handleResumeAddon(addonId: string) {
    if (!editingTenant) return;
    setAddonActionId(addonId);
    await resumeAddonMutation.mutateAsync({ tenantId: editingTenant.id, addonId });
  }

  if (tenantsQuery.isLoading || clientsQuery.isLoading || addonsQuery.isLoading) {
    return (
      <div className="rounded-3xl border border-[#e6edf5] bg-[#f8fbff] p-5 text-sm font-bold text-[#607080]">
        جارٍ تحميل النسخ...
      </div>
    );
  }

  if (pageError || !tenantsQuery.data || !clientsQuery.data || !addonsQuery.data) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-700">
        {pageError || 'تعذر تحميل النسخ الآن.'}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-[28px] border border-[#e6edf5] bg-[#f8fbff] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <p className="text-xs font-black tracking-[0.18em] text-cyan-200">النسخ التشغيلية</p>
            <h3 className="text-lg font-black text-white">النسخ</h3>
          </div>
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#114488] px-5 text-sm font-black text-white transition hover:bg-[#0d356a]"
          >
            <Plus className="h-4 w-4" />
            <span>إنشاء نسخة جديدة</span>
          </button>
        </div>

        <div className="mt-5 overflow-x-auto rounded-[24px] border border-[#e6edf5] bg-white">
          <table className="min-w-full divide-y divide-[#e6edf5] text-right">
            <thead className="bg-[#f3f7fb] text-[#304050]">
              <tr>
                <th className="px-4 py-3 text-sm font-black">النسخة</th>
                <th className="px-4 py-3 text-sm font-black">العميل</th>
                <th className="px-4 py-3 text-sm font-black">الوضع الحالي</th>
                <th className="px-4 py-3 text-sm font-black">الحالة</th>
                <th className="px-4 py-3 text-sm font-black">الوصول</th>
                <th className="px-4 py-3 text-sm font-black">الإجراءات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eef2f6] bg-white">
              {tenantsQuery.data.map((tenant) => (
                <tr key={tenant.id} className="align-top text-[#1b2430]">
                  <td className="px-4 py-4">
                    <p className="text-sm font-black">{tenant.brand_name}</p>
                    <p className="mt-1 text-xs font-semibold text-[#708090]" dir="ltr">
                      {tenant.code}
                    </p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm font-black">{tenant.client_owner_name}</p>
                    <p className="mt-1 text-xs font-semibold text-[#708090]">{tenant.client_brand_name}</p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-black text-sky-800">
                      {tenant.current_stage_name}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span
                      className={`inline-flex rounded-full border px-3 py-1 text-xs font-black ${getTenantStateClass(
                        tenant.environment_state
                      )}`}
                    >
                      {getTenantStateLabel(tenant.environment_state)}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm font-black" dir="ltr">
                      {tenant.manager_username}
                    </p>
                    <p className="mt-1 text-xs font-semibold text-[#708090]" dir="ltr">
                      {tenant.manager_login_path}
                    </p>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex min-w-[280px] flex-wrap gap-2">
                      <ActionButton label="تعديل" icon={Edit3} onClick={() => openEditTenant(tenant)} />
                      <ActionButton
                        label={tenant.environment_state === 'suspended' ? 'إعادة التفعيل' : 'إيقاف مؤقت'}
                        icon={PauseCircle}
                        tone="warning"
                        disabled={toggleMutation.isPending}
                        onClick={() => toggleMutation.mutate(tenant.id)}
                      />
                      <ActionButton
                        label="حذف"
                        icon={Trash2}
                        tone="danger"
                        disabled={deleteMutation.isPending}
                        onClick={() => setDeleteTarget(tenant)}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <Modal
        open={createOpen}
        onClose={closeCreateModal}
        title="إنشاء نسخة جديدة"
        footer={
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              {createStep !== 'client' && createStep !== 'access' ? (
                <button
                  type="button"
                  onClick={() => setCreateStep('client')}
                  className="btn-secondary ui-size-sm gap-2 px-4"
                >
                  <ArrowRight className="h-4 w-4" />
                  <span>رجوع</span>
                </button>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" onClick={closeCreateModal} className="btn-secondary ui-size-sm px-4">
                إغلاق
              </button>
              {createStep !== 'access' ? (
                <button type="button" onClick={() => void handleCreate()} className="btn-primary ui-size-sm gap-2 px-4">
                  <span>{createStep === 'tenant' ? 'إنشاء النسخة' : 'متابعة'}</span>
                  <ArrowLeft className="h-4 w-4" />
                </button>
              ) : null}
            </div>
          </div>
        }
      >
        <div className="space-y-5 rounded-[28px] border border-stone-200 bg-stone-50/80 p-4 sm:p-5">
          <div className="grid gap-3 md:grid-cols-3">
            <StepCard label={clientMode === 'new' ? 'العميل الجديد' : 'اختيار العميل'} active={createStep === 'client'} />
            <StepCard label="النسخة" active={createStep === 'tenant'} />
            <StepCard label="الوصول" active={createStep === 'access'} />
          </div>

          {createError ? (
            <div className="rounded-2xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-800">
              {createError}
            </div>
          ) : null}

          {createStep === 'client' ? (
            <div className="space-y-4 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm">
              <div className="grid gap-3 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setClientMode('new')}
                  className={`rounded-2xl border px-4 py-4 text-right shadow-sm transition ${
                    clientMode === 'new'
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                      : 'border-stone-300 bg-white text-stone-800 hover:border-cyan-300'
                  }`}
                >
                  عميل جديد
                </button>
                <button
                  type="button"
                  onClick={() => setClientMode('existing')}
                  className={`rounded-2xl border px-4 py-4 text-right shadow-sm transition ${
                    clientMode === 'existing'
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                      : 'border-stone-300 bg-white text-stone-800 hover:border-cyan-300'
                  }`}
                >
                  عميل موجود
                </button>
              </div>

              {clientMode === 'existing' ? (
                <label className="block space-y-2">
                  <span className="text-sm font-bold text-stone-700">العميل</span>
                  <select
                    className="form-select h-12 w-full rounded-2xl border-stone-300 bg-white text-stone-900"
                    value={existingClientId}
                    onChange={(event) => setExistingClientId(event.target.value)}
                  >
                    <option value="">اختر العميل</option>
                    {clientsQuery.data.map((client) => (
                      <option key={client.id} value={client.id}>
                        {client.owner_name} - {client.brand_name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  <Field label="اسم العميل" value={clientOwnerName} onChange={setClientOwnerName} />
                  <Field label="العلامة" value={clientBrandName} onChange={setClientBrandName} />
                  <Field label="الهاتف" value={clientPhone} onChange={setClientPhone} dir="ltr" />
                  <Field label="المدينة" value={clientCity} onChange={setClientCity} />
                </div>
              )}
            </div>
          ) : null}

          {createStep === 'tenant' ? (
            <div className="space-y-4">
              <div className="grid gap-3 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm md:grid-cols-2">
                <Field label="اسم النسخة" value={tenantBrandName} onChange={setTenantBrandName} />
                <Field label="الكود" value={tenantCode} onChange={setTenantCode} dir="ltr" placeholder="tenant_code" />
                <div className="md:col-span-2">
                  <Field
                    label="قاعدة البيانات"
                    value={databaseName}
                    onChange={setDatabaseName}
                    dir="ltr"
                    placeholder="tenant_restaurant_a"
                  />
                </div>
              </div>

              <div className="rounded-[24px] border border-emerald-300 bg-emerald-50 p-4 text-sm font-bold text-emerald-950">
                كل نسخة جديدة تبدأ تلقائيًا من {baseAddon?.name ?? 'النسخة الأساسية'}.
              </div>
            </div>
          ) : null}

          {createStep === 'access' && createdResult ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <SummaryCard label="العميل" value={createdResult.client.owner_name} />
                <SummaryCard label="النسخة" value={createdResult.tenant.brand_name} />
                <SummaryCard label="الوضع الأولي" value={createdResult.activation_stage.name} />
                <SummaryCard label="الحالة" value={getTenantStateLabel(createdResult.tenant.environment_state)} />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <SummaryCard label="مسار الدخول" value={createdResult.access.login_path} />
                <SummaryCard label="اسم الدخول" value={createdResult.access.manager_username} />
                <SummaryCard label="كلمة المرور" value={createdResult.access.manager_password} />
                <SummaryCard label="الواجهة العامة" value={createdResult.tenant.public_order_path} />
              </div>
            </div>
          ) : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(editingTenant)}
        onClose={closeEditModal}
        title="تعديل العميل والنسخة"
        footer={
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {editingTenant ? (
                <button
                  type="button"
                  onClick={() => toggleMutation.mutate(editingTenant.id)}
                  disabled={toggleMutation.isPending}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-amber-300 bg-amber-50 px-4 text-sm font-black text-amber-900 transition hover:bg-amber-100 disabled:cursor-wait disabled:opacity-60"
                >
                  {editingTenant.environment_state === 'suspended' ? <PlayCircle className="h-4 w-4" /> : <PauseCircle className="h-4 w-4" />}
                  <span>{editingTenant.environment_state === 'suspended' ? 'استئناف النسخة' : 'إيقاف النسخة مؤقتًا'}</span>
                </button>
              ) : null}
              {editingTenant ? (
                <button
                  type="button"
                  onClick={() => setDeleteTarget(editingTenant)}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-rose-300 bg-rose-50 px-4 text-sm font-black text-rose-700 transition hover:bg-rose-100"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>حذف النسخة</span>
                </button>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" onClick={closeEditModal} className="btn-secondary ui-size-sm px-4">
              إغلاق
            </button>
            <button
              type="button"
              onClick={() => void handleSaveEdit()}
              disabled={updateMutation.isPending}
              className="btn-primary ui-size-sm gap-2 px-4 disabled:cursor-wait disabled:opacity-70"
            >
              <ShieldCheck className="h-4 w-4" />
              <span>{updateMutation.isPending ? 'جارٍ الحفظ...' : 'حفظ التعديل'}</span>
              </button>
            </div>
          </div>
        }
      >
        <div className="space-y-4 rounded-[28px] border border-stone-200 bg-stone-50/80 p-4 sm:p-5">
          {editError ? (
            <div className="rounded-2xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-800">
              {editError}
            </div>
          ) : null}

          <div className="space-y-3 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-black tracking-[0.18em] text-stone-500">بيانات العميل</p>
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="اسم العميل" value={editClientOwnerName} onChange={setEditClientOwnerName} />
              <Field label="اسم العلامة" value={editClientBrandName} onChange={setEditClientBrandName} />
              <Field label="الهاتف" value={editClientPhone} onChange={setEditClientPhone} dir="ltr" />
              <Field label="المدينة" value={editClientCity} onChange={setEditClientCity} />
            </div>
          </div>

          <div className="space-y-3 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-black tracking-[0.18em] text-stone-500">بيانات النسخة</p>
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="اسم النسخة" value={editBrandName} onChange={setEditBrandName} />
              <label className="block space-y-2">
                <span className="text-sm font-bold text-stone-700">الأداة المفتوحة حاليًا</span>
                <select
                  className="form-select h-12 w-full rounded-2xl border-stone-300 bg-white text-stone-900"
                  value={editActivationStageId}
                  onChange={(event) => setEditActivationStageId(event.target.value)}
                >
                  {editableAddons.map((addon) => (
                    <option key={addon.id} value={addon.id}>
                      {addon.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {editingTenant ? (
            <>
              <div className="space-y-3 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-black tracking-[0.18em] text-stone-500">التحكم في الأدوات</p>
                <div className="grid gap-3 lg:grid-cols-2">
                  {tenantAddonRows.map(({ addon, status, canPause, canResume }) => {
                    const isBusy =
                      addonActionId === addon.id &&
                      (pauseAddonMutation.isPending || resumeAddonMutation.isPending);
                    return (
                      <article
                        key={addon.id}
                        className="rounded-[22px] border border-stone-200 bg-stone-50/80 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <p className="text-sm font-black text-stone-900">{addon.name}</p>
                            <p className="text-xs font-semibold leading-6 text-stone-600">
                              {getTenantAddonHint(status, addon)}
                            </p>
                          </div>
                          <span
                            className={`shrink-0 rounded-full border px-3 py-1 text-[11px] font-black ${getTenantAddonStatusClass(
                              status
                            )}`}
                          >
                            {getTenantAddonStatusLabel(status)}
                          </span>
                        </div>

                        <div className="mt-4 flex flex-wrap gap-2">
                          {canPause ? (
                            <button
                              type="button"
                              onClick={() => void handlePauseAddon(addon.id)}
                              disabled={isBusy}
                              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-2xl border border-amber-300 bg-amber-50 px-3 text-xs font-black text-amber-900 transition hover:bg-amber-100 disabled:cursor-wait disabled:opacity-60"
                            >
                              {isBusy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <PauseCircle className="h-4 w-4" />}
                              <span>{isBusy ? 'جارٍ الإيقاف...' : 'إيقاف مؤقت'}</span>
                            </button>
                          ) : null}

                          {canResume ? (
                            <button
                              type="button"
                              onClick={() => void handleResumeAddon(addon.id)}
                              disabled={isBusy}
                              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-2xl border border-emerald-300 bg-emerald-50 px-3 text-xs font-black text-emerald-900 transition hover:bg-emerald-100 disabled:cursor-wait disabled:opacity-60"
                            >
                              {isBusy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
                              <span>{isBusy ? 'جارٍ الاستئناف...' : 'استئناف'}</span>
                            </button>
                          ) : null}

                          {!canPause && !canResume ? (
                            <span className="inline-flex min-h-10 items-center rounded-2xl border border-stone-200 bg-white px-3 text-xs font-black text-stone-500">
                              لا يوجد إجراء مباشر الآن
                            </span>
                          ) : null}
                        </div>
                      </article>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-3 rounded-[24px] border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-black tracking-[0.18em] text-stone-500">الوصول والربط</p>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <SummaryCard label="الكود" value={editingTenant.code} />
                  <SummaryCard label="قاعدة البيانات" value={editingTenant.database_name} />
                  <SummaryCard label="اسم الدخول" value={editingTenant.manager_username} />
                  <SummaryCard label="مسار الدخول" value={editingTenant.manager_login_path} />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <SummaryCard label="الواجهة العامة" value={editingTenant.public_order_path} />
                  <SummaryCard label="الوضع الحالي" value={editingTenant.current_stage_name} />
                </div>
                <div className="rounded-2xl border border-stone-200 bg-stone-50/80 p-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-end">
                    <div className="min-w-0 flex-1">
                      <Field
                        label="كلمة المرور الجديدة"
                        value={regeneratedAccess?.manager_password ?? ''}
                        dir="ltr"
                        placeholder="اضغط على إعادة التوليد لإظهار الكلمة الجديدة"
                        readOnly
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => editingTenant && regenerateMutation.mutate(editingTenant.id)}
                      disabled={regenerateMutation.isPending}
                      className="inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl border border-cyan-300 bg-cyan-50 px-4 text-sm font-black text-cyan-900 transition hover:bg-cyan-100 disabled:cursor-wait disabled:opacity-70"
                    >
                      {regenerateMutation.isPending ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <KeyRound className="h-4 w-4" />
                      )}
                      <span>{regenerateMutation.isPending ? 'جارٍ التوليد...' : 'إعادة التوليد'}</span>
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        onClose={closeDeleteModal}
        title="حذف النسخة"
        footer={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button type="button" onClick={closeDeleteModal} className="btn-secondary ui-size-sm px-4">
              إغلاق
            </button>
            <button
              type="button"
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
              disabled={deleteMutation.isPending}
              className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-rose-300 bg-rose-600 px-4 text-sm font-black text-white transition hover:bg-rose-700 disabled:cursor-wait disabled:opacity-70"
            >
              {deleteMutation.isPending ? 'جارٍ الحذف...' : 'حذف نهائي'}
            </button>
          </div>
        }
      >
        <div className="rounded-[28px] border border-stone-200 bg-stone-50/80 p-4 sm:p-5">
          <p className="text-sm font-bold text-stone-800">
            سيتم حذف سجل النسخة وملف قاعدة بياناتها نهائيًا.
          </p>
          {deleteTarget ? (
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <SummaryCard label="النسخة" value={deleteTarget.brand_name} />
              <SummaryCard label="قاعدة البيانات" value={deleteTarget.database_name} />
            </div>
          ) : null}
        </div>
      </Modal>
    </div>
  );
}
