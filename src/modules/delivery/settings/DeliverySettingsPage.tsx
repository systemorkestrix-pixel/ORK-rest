import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Settings2 } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { DeliveryProvidersPanel } from '@/modules/delivery/drivers/components/DeliveryProvidersPanel';
import { api } from '@/shared/api/client';
import type {
  DeliveryAddressNode,
  DeliveryAddressNodeCreatePayload,
  DeliveryAddressNodeUpdatePayload,
  DeliveryDriver,
  DeliveryPolicies,
  DeliverySettings,
  SystemContext,
  User,
} from '@/shared/api/types';
import { PageHeaderCard } from '@/shared/ui/PageHeaderCard';
import { PageShell } from '@/shared/ui/PageShell';

import { DeliveryAddressPricingManager } from './components/DeliveryAddressPricingManager';
import { DeliveryAddressTreeManager } from './components/DeliveryAddressTreeManager';
import { DeliveryDriversPanel } from './components/DeliveryDriversPanel';
import { DeliveryPolicySettingsPanel } from './components/DeliveryPolicySettingsPanel';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function mapLevelLabel(level: string) {
  switch (level) {
    case 'admin_area_level_1':
      return 'المنطقة الرئيسية';
    case 'admin_area_level_2':
      return 'الفرع الإداري';
    case 'locality':
      return 'المدينة';
    case 'sublocality':
      return 'الحي';
    default:
      return level;
  }
}

export function DeliverySettingsPage() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const [deliveryFeeInput, setDeliveryFeeInput] = useState('0');
  const [deliveryMinOrderInput, setDeliveryMinOrderInput] = useState('0');
  const [deliveryAutoNotifyTeam, setDeliveryAutoNotifyTeam] = useState(false);
  const [selectedLevel1Id, setSelectedLevel1Id] = useState<number | null>(null);
  const [selectedLevel2Id, setSelectedLevel2Id] = useState<number | null>(null);
  const [selectedLocalityId, setSelectedLocalityId] = useState<number | null>(null);
  const [selectedSublocalityId, setSelectedSublocalityId] = useState<number | null>(null);
  const [pricingSearch, setPricingSearch] = useState('');
  const [pricingActiveOnly, setPricingActiveOnly] = useState<boolean | null>(null);

  const isManager = role === 'manager';

  const systemContextQuery = useQuery({
    queryKey: ['manager-system-context'],
    queryFn: () => api.managerSystemContext(role ?? 'manager'),
    enabled: isManager,
  });

  const deliverySettingsQuery = useQuery({
    queryKey: ['manager-delivery-settings'],
    queryFn: () => api.managerDeliverySettings(role ?? 'manager'),
    enabled: isManager,
  });

  const deliveryPoliciesQuery = useQuery({
    queryKey: ['manager-delivery-policies'],
    queryFn: () => api.managerDeliveryPolicies(role ?? 'manager'),
    enabled: isManager,
  });

  const providersQuery = useQuery({
    queryKey: ['manager-delivery-providers'],
    queryFn: () => api.managerDeliveryProviders(role ?? 'manager'),
    enabled: isManager,
  });

  const driversQuery = useQuery({
    queryKey: ['manager-drivers'],
    queryFn: () => api.managerDrivers(role ?? 'manager'),
    enabled: isManager,
  });

  const usersQuery = useQuery({
    queryKey: ['manager-users'],
    queryFn: () => api.managerUsers(role ?? 'manager'),
    enabled: isManager,
  });

  const level1Query = useQuery({
    queryKey: ['manager-delivery-address-nodes', 'root'],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager'),
    enabled: isManager,
  });

  const level2Query = useQuery({
    queryKey: ['manager-delivery-address-nodes', selectedLevel1Id],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager', selectedLevel1Id ?? undefined),
    enabled: isManager && selectedLevel1Id !== null,
  });

  const localityQuery = useQuery({
    queryKey: ['manager-delivery-address-nodes', selectedLevel2Id],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager', selectedLevel2Id ?? undefined),
    enabled: isManager && selectedLevel2Id !== null,
  });

  const sublocalityQuery = useQuery({
    queryKey: ['manager-delivery-address-nodes', selectedLocalityId],
    queryFn: () => api.managerDeliveryAddressNodes(role ?? 'manager', selectedLocalityId ?? undefined),
    enabled: isManager && selectedLocalityId !== null,
  });

  const pricingQuery = useQuery({
    queryKey: ['manager-delivery-address-pricing', pricingSearch, pricingActiveOnly],
    queryFn: () =>
      api.managerDeliveryAddressPricing(role ?? 'manager', {
        search: pricingSearch || undefined,
        activeOnly: pricingActiveOnly,
      }),
    enabled: isManager,
  });

  const selectedNodeId =
    selectedSublocalityId ?? selectedLocalityId ?? selectedLevel2Id ?? selectedLevel1Id ?? undefined;

  const quoteQuery = useQuery({
    queryKey: ['manager-delivery-address-pricing-quote', selectedNodeId],
    queryFn: () => api.managerQuoteDeliveryAddressPricing(role ?? 'manager', selectedNodeId),
    enabled: isManager && selectedNodeId !== undefined,
  });

  useEffect(() => {
    if (deliverySettingsQuery.data) {
      setDeliveryFeeInput(String(deliverySettingsQuery.data.delivery_fee));
    }
  }, [deliverySettingsQuery.data]);

  useEffect(() => {
    if (deliveryPoliciesQuery.data) {
      setDeliveryMinOrderInput(String(deliveryPoliciesQuery.data.min_order_amount));
      setDeliveryAutoNotifyTeam(deliveryPoliciesQuery.data.auto_notify_team);
    }
  }, [deliveryPoliciesQuery.data]);

  const invalidateDeliverySettingsViews = () => {
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-settings'] });
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-policies'] });
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-providers'] });
    queryClient.invalidateQueries({ queryKey: ['manager-drivers'] });
    queryClient.invalidateQueries({ queryKey: ['manager-users'] });
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-address-nodes'] });
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-address-pricing'] });
    queryClient.invalidateQueries({ queryKey: ['manager-delivery-address-pricing-quote'] });
    queryClient.invalidateQueries({ queryKey: ['public-delivery-settings'] });
    queryClient.invalidateQueries({ queryKey: ['public-delivery-address-nodes'] });
    queryClient.invalidateQueries({ queryKey: ['public-delivery-pricing-quote'] });
    queryClient.invalidateQueries({ queryKey: ['delivery-team-drivers'] });
    queryClient.invalidateQueries({ queryKey: ['delivery-orders'] });
    queryClient.invalidateQueries({ queryKey: ['manager-orders-delivery'] });
    queryClient.invalidateQueries({ queryKey: ['manager-dashboard-operational-heart'] });
  };

  const updateDeliverySettingsMutation = useMutation({
    mutationFn: (deliveryFee: number) =>
      api.managerUpdateDeliverySettings(role ?? 'manager', { delivery_fee: deliveryFee }),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const updateDeliveryPoliciesMutation = useMutation({
    mutationFn: (payload: { min_order_amount: number; auto_notify_team: boolean }) =>
      api.managerUpdateDeliveryPolicies(role ?? 'manager', payload),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const createAddressNodeMutation = useMutation({
    mutationFn: (payload: DeliveryAddressNodeCreatePayload) =>
      api.managerCreateDeliveryAddressNode(role ?? 'manager', payload),
    onSuccess: (node) => {
      invalidateDeliverySettingsViews();
      if (node.level === 'admin_area_level_1') {
        setSelectedLevel1Id(node.id);
        setSelectedLevel2Id(null);
        setSelectedLocalityId(null);
        setSelectedSublocalityId(null);
      } else if (node.level === 'admin_area_level_2') {
        setSelectedLevel2Id(node.id);
        setSelectedLocalityId(null);
        setSelectedSublocalityId(null);
      } else if (node.level === 'locality') {
        setSelectedLocalityId(node.id);
        setSelectedSublocalityId(null);
      } else if (node.level === 'sublocality') {
        setSelectedSublocalityId(node.id);
      }
    },
  });

  const updateAddressNodeMutation = useMutation({
    mutationFn: ({ nodeId, payload }: { nodeId: number; payload: DeliveryAddressNodeUpdatePayload }) =>
      api.managerUpdateDeliveryAddressNode(role ?? 'manager', nodeId, payload),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const deleteAddressNodeMutation = useMutation({
    mutationFn: (nodeId: number) => api.managerDeleteDeliveryAddressNode(role ?? 'manager', nodeId),
    onSuccess: () => {
      invalidateDeliverySettingsViews();
      setSelectedLevel1Id(null);
      setSelectedLevel2Id(null);
      setSelectedLocalityId(null);
      setSelectedSublocalityId(null);
    },
  });

  const upsertPricingMutation = useMutation({
    mutationFn: (payload: { node_id: number; delivery_fee: number; active: boolean; sort_order: number }) =>
      api.managerUpsertDeliveryAddressPricing(role ?? 'manager', payload),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const deletePricingMutation = useMutation({
    mutationFn: (pricingId: number) => api.managerDeleteDeliveryAddressPricing(role ?? 'manager', pricingId),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const updateDriverMutation = useMutation({
    mutationFn: (payload: {
      driverId: number;
      data: {
        provider_id: number | null;
        name: string;
        phone: string;
        vehicle: string | null;
        status: DeliveryDriver['status'];
        active: boolean;
      };
    }) => api.managerUpdateDriver(role ?? 'manager', payload.driverId, payload.data),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const createDriverMutation = useMutation({
    mutationFn: (payload: {
      name: string;
      provider_id: number | null;
      phone: string;
      vehicle: string | null;
      active: boolean;
    }) => api.managerCreateDriver(role ?? 'manager', payload),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const deleteDriverMutation = useMutation({
    mutationFn: (driverId: number) => api.managerDeleteDriver(role ?? 'manager', driverId),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const createProviderMutation = useMutation({
    mutationFn: async (payload: {
      account_user_id: number | null;
      name: string;
      provider_type: 'internal_team' | 'partner_company';
      active: boolean;
      account_user?: {
        name: string;
        username: string;
        password: string;
        active: boolean;
      } | null;
    }) => {
      let createdAccountUserId: number | null = null;
      try {
        if (payload.account_user) {
          const createdUser = await api.managerCreateUser(role ?? 'manager', {
            name: payload.account_user.name,
            username: payload.account_user.username,
            password: payload.account_user.password,
            role: 'delivery',
            active: payload.account_user.active,
          });
          createdAccountUserId = createdUser.id;
        }

        return await api.managerCreateDeliveryProvider(role ?? 'manager', {
          account_user_id: payload.account_user_id ?? createdAccountUserId,
          name: payload.name,
          provider_type: payload.provider_type,
          active: payload.active,
        });
      } catch (error) {
        if (createdAccountUserId !== null) {
          try {
            await api.managerDeleteUser(role ?? 'manager', createdAccountUserId);
          } catch {
            // Keep the provider creation failure as the source error.
          }
        }
        throw error;
      }
    },
    onSuccess: invalidateDeliverySettingsViews,
  });

  const updateProviderMutation = useMutation({
    mutationFn: (payload: {
      providerId: number;
      data: {
        account_user_id: number | null;
        name: string;
        provider_type: 'internal_team' | 'partner_company';
        active: boolean;
      };
    }) => api.managerUpdateDeliveryProvider(role ?? 'manager', payload.providerId, payload.data),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const deleteProviderMutation = useMutation({
    mutationFn: (providerId: number) => api.managerDeleteDeliveryProvider(role ?? 'manager', providerId),
    onSuccess: invalidateDeliverySettingsViews,
  });

  const level1Nodes = level1Query.data?.items ?? [];
  const level2Nodes = level2Query.data?.items ?? [];
  const localityNodes = localityQuery.data?.items ?? [];
  const sublocalityNodes = sublocalityQuery.data?.items ?? [];
  const providers = providersQuery.data ?? [];
  const drivers = driversQuery.data ?? [];
  const users = usersQuery.data ?? [];

  const selectedLevel1Node = level1Nodes.find((node) => node.id === selectedLevel1Id) ?? null;
  const selectedLevel2Node = level2Nodes.find((node) => node.id === selectedLevel2Id) ?? null;
  const selectedLocalityNode = localityNodes.find((node) => node.id === selectedLocalityId) ?? null;
  const selectedSublocalityNode = sublocalityNodes.find((node) => node.id === selectedSublocalityId) ?? null;

  const selectedNode =
    selectedSublocalityNode ?? selectedLocalityNode ?? selectedLevel2Node ?? selectedLevel1Node ?? null;

  const selectedPathLabel = [selectedLevel1Node, selectedLevel2Node, selectedLocalityNode, selectedSublocalityNode]
    .filter(Boolean)
    .map((node) => (node as DeliveryAddressNode).display_name)
    .join(' / ');

  const availableProviderUsers = useMemo<User[]>(() => {
    const linkedUserIds = new Set(
      providers.map((provider) => provider.account_user_id).filter((userId): userId is number => typeof userId === 'number')
    );
    return users
      .filter((user) => user.role === 'delivery' && !linkedUserIds.has(user.id))
      .sort((left, right) => left.name.localeCompare(right.name, 'ar'));
  }, [providers, users]);

  const structureMetrics = useMemo(
    () => ({
      providers: providers.length,
      internalDrivers: drivers.filter((driver) => !!driver.provider_is_internal_default).length,
      telegramLinked: drivers.filter((driver) => driver.telegram_enabled).length,
    }),
    [drivers, providers]
  );

  const settingsSummary = useMemo(
    () => ({
      pricingMode:
        deliverySettingsQuery.data?.pricing_mode === 'manual_tree' ? 'حسب العنوان' : 'رسم ثابت',
      fallbackFee: `${(deliverySettingsQuery.data?.delivery_fee ?? 0).toFixed(2)} ${systemContextQuery.data?.currency_symbol ?? ''}`.trim(),
      selectedNodeLabel: selectedNode ? mapLevelLabel(selectedNode.level) : 'لا يوجد تحديد',
    }),
    [deliverySettingsQuery.data, selectedNode, systemContextQuery.data?.currency_symbol]
  );

  const deliverySettingsError = updateDeliverySettingsMutation.isError
    ? getErrorMessage(updateDeliverySettingsMutation.error, 'تعذر حفظ الرسم الاحتياطي.')
    : '';

  const deliveryPoliciesError = updateDeliveryPoliciesMutation.isError
    ? getErrorMessage(updateDeliveryPoliciesMutation.error, 'تعذر حفظ السياسات.')
    : '';

  const settingsMutationError =
    (createDriverMutation.error as Error | null)?.message ||
    (updateDriverMutation.error as Error | null)?.message ||
    (deleteDriverMutation.error as Error | null)?.message ||
    (createProviderMutation.error as Error | null)?.message ||
    (updateProviderMutation.error as Error | null)?.message ||
    (deleteProviderMutation.error as Error | null)?.message ||
    '';

  if (
    systemContextQuery.isLoading ||
    deliverySettingsQuery.isLoading ||
    deliveryPoliciesQuery.isLoading ||
    providersQuery.isLoading ||
    driversQuery.isLoading ||
    usersQuery.isLoading ||
    level1Query.isLoading ||
    pricingQuery.isLoading
  ) {
    return (
      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تجهيز صفحة إعدادات التوصيل...
      </div>
    );
  }

  if (
    systemContextQuery.isError ||
    deliverySettingsQuery.isError ||
    deliveryPoliciesQuery.isError ||
    providersQuery.isError ||
    driversQuery.isError ||
    usersQuery.isError ||
    level1Query.isError ||
    pricingQuery.isError
  ) {
    return (
      <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-5 text-sm text-rose-200">
        تعذر تحميل بيانات التوصيل. أعد المحاولة.
      </div>
    );
  }

  return (
    <PageShell
      className="admin-page"
      header={
        <PageHeaderCard
          title="إعدادات التوصيل"
          description="اضبط جهات التوصيل والسائقين والسياسات من هنا."
          icon={<Settings2 className="h-5 w-5" />}
          actions={
            <Link to="/console/delivery/drivers" className="btn-secondary ui-size-sm">
              العودة إلى التشغيل
            </Link>
          }
          metrics={[
            { label: 'جهات التوصيل', value: structureMetrics.providers, tone: 'default' },
            { label: 'السائقون الداخليون', value: structureMetrics.internalDrivers, tone: 'info' },
            { label: 'Telegram مربوط', value: structureMetrics.telegramLinked, tone: 'success' },
          ]}
          metricsContainerClassName="grid gap-2 sm:grid-cols-3"
        />
      }
    >
      <div className="space-y-4">
        {settingsMutationError ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {settingsMutationError}
          </div>
        ) : null}

        <section className="admin-card space-y-4 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h3 className="text-sm font-black text-[var(--text-primary-strong)]">تهيئة القناة</h3>
              <p className="text-xs text-[var(--text-muted)]">
                أنشئ الجهة، أضف السائقين الداخليين، واربط Telegram. هذه الخطوات ينبغي أن تكون مباشرة وقصيرة دون خلطها بالتشغيل.
              </p>
            </div>
            <div className="grid min-w-[240px] gap-2 sm:grid-cols-3">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
                <p className="font-bold text-[var(--text-muted)]">الدولة / العملة</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                  {systemContextQuery.data?.country_name ?? 'غير محددة'} · {systemContextQuery.data?.currency_symbol}{' '}
                  {systemContextQuery.data?.currency_code}
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
                <p className="font-bold text-[var(--text-muted)]">طريقة التسعير</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">{settingsSummary.pricingMode}</p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
                <p className="font-bold text-[var(--text-muted)]">الرسم الاحتياطي</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">{settingsSummary.fallbackFee}</p>
              </div>
            </div>
          </div>

          <DeliveryProvidersPanel
            providers={providers}
            drivers={drivers}
            availableAccountUsers={availableProviderUsers}
            onCreateProvider={(payload) => createProviderMutation.mutate(payload)}
            onUpdateProvider={(providerId, payload) => updateProviderMutation.mutate({ providerId, data: payload })}
            onDeleteProvider={(providerId) => deleteProviderMutation.mutate(providerId)}
            creating={createProviderMutation.isPending}
            updating={updateProviderMutation.isPending}
            deleting={deleteProviderMutation.isPending}
            error={settingsMutationError}
          />

          <DeliveryDriversPanel
            drivers={drivers}
            providers={providers}
            onCreateDriver={(payload) => createDriverMutation.mutate(payload)}
            onUpdateDriver={(driverId, payload) => updateDriverMutation.mutate({ driverId, data: payload })}
            onDeleteDriver={(driverId) => deleteDriverMutation.mutate(driverId)}
            creating={createDriverMutation.isPending}
            updating={updateDriverMutation.isPending}
            deleting={deleteDriverMutation.isPending}
            createError={(createDriverMutation.error as Error | null)?.message ?? ''}
            updateError={(updateDriverMutation.error as Error | null)?.message ?? ''}
            title="السائقون الداخليون وربط Telegram"
            description="الإدارة تضيف السائقين الداخليين فقط. سائقو الجهات الخاصة يدارون لاحقًا من لوحة الجهة، أما Telegram الداخلي فيبقى هنا."
          />
        </section>

        <section className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
          <DeliveryPolicySettingsPanel
            settings={deliverySettingsQuery.data as DeliverySettings}
            policies={deliveryPoliciesQuery.data as DeliveryPolicies}
            systemContext={systemContextQuery.data as SystemContext | null}
            deliveryFeeInput={deliveryFeeInput}
            deliveryMinOrderInput={deliveryMinOrderInput}
            deliveryAutoNotifyTeam={deliveryAutoNotifyTeam}
            onDeliveryFeeInputChange={setDeliveryFeeInput}
            onDeliveryMinOrderInputChange={setDeliveryMinOrderInput}
            onDeliveryAutoNotifyTeamChange={setDeliveryAutoNotifyTeam}
            onSaveSettings={() => {
              const parsedFee = Number(deliveryFeeInput);
              if (!Number.isFinite(parsedFee) || parsedFee < 0) return;
              updateDeliverySettingsMutation.mutate(parsedFee);
            }}
            onSavePolicies={() => {
              const parsedMin = Number(deliveryMinOrderInput);
              if (!Number.isFinite(parsedMin) || parsedMin < 0) return;
              updateDeliveryPoliciesMutation.mutate({
                min_order_amount: parsedMin,
                auto_notify_team: deliveryAutoNotifyTeam,
              });
            }}
            savingSettings={updateDeliverySettingsMutation.isPending}
            savingPolicies={updateDeliveryPoliciesMutation.isPending}
            settingsError={deliverySettingsError}
            policiesError={deliveryPoliciesError}
            settingsSuccess={updateDeliverySettingsMutation.isSuccess}
            policiesSuccess={updateDeliveryPoliciesMutation.isSuccess}
          />

          <section className="admin-card space-y-3 p-4">
            <div className="space-y-1">
              <h3 className="text-sm font-black text-[var(--text-primary-strong)]">العنوان والسعر</h3>
              <p className="text-xs text-[var(--text-muted)]">
                اختر العقدة من الشجرة ليظهر سعرها الفعلي فورًا. لا حاجة للتمرير أولًا إلى قسم آخر حتى ترى النتيجة.
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
                <p className="font-bold text-[var(--text-muted)]">العقدة المحددة</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">{settingsSummary.selectedNodeLabel}</p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
                <p className="font-bold text-[var(--text-muted)]">المسار الحالي</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                  {selectedPathLabel || 'اختر عنوانًا من الشجرة'}
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs">
                <p className="font-bold text-[var(--text-muted)]">العناوين المسعّرة</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">{pricingQuery.data?.items.length ?? 0}</p>
              </div>
            </div>
          </section>
        </section>

        <section className="space-y-4">
          <div className="space-y-1">
            <h3 className="text-sm font-black text-[var(--text-primary-strong)]">العناوين والتسعير</h3>
            <p className="text-xs text-[var(--text-muted)]">
              ابنِ الشجرة وعدّل السعر من نفس نافذة العنوان. سجل الأسعار في الأسفل مرجع فقط، لا مسار العمل الأساسي.
            </p>
          </div>

          <DeliveryAddressTreeManager
            levels={[
              {
                key: 'admin_area_level_1',
                label: 'المنطقة الرئيسية',
                description: 'ابدأ من أعلى مستوى.',
                nodes: level1Nodes,
                selectedId: selectedLevel1Id,
                onSelect: (nodeId) => {
                  setSelectedLevel1Id(nodeId);
                  setSelectedLevel2Id(null);
                  setSelectedLocalityId(null);
                  setSelectedSublocalityId(null);
                },
                emptyState: 'لا توجد مناطق رئيسية بعد.',
              },
              {
                key: 'admin_area_level_2',
                label: 'الفرع الإداري',
                description: 'يظهر بعد اختيار المنطقة الرئيسية.',
                nodes: level2Nodes,
                selectedId: selectedLevel2Id,
                onSelect: (nodeId) => {
                  setSelectedLevel2Id(nodeId);
                  setSelectedLocalityId(null);
                  setSelectedSublocalityId(null);
                },
                emptyState: selectedLevel1Id ? 'لا توجد فروع بعد.' : 'اختر المنطقة الرئيسية أولًا.',
              },
              {
                key: 'locality',
                label: 'المدينة',
                description: 'اختر المدينة قبل الحي.',
                nodes: localityNodes,
                selectedId: selectedLocalityId,
                onSelect: (nodeId) => {
                  setSelectedLocalityId(nodeId);
                  setSelectedSublocalityId(null);
                },
                emptyState: selectedLevel2Id ? 'لا توجد مدن بعد.' : 'اختر الفرع الإداري أولًا.',
              },
              {
                key: 'sublocality',
                label: 'الحي',
                description: 'آخر مستوى يراه العميل.',
                nodes: sublocalityNodes,
                selectedId: selectedSublocalityId,
                onSelect: setSelectedSublocalityId,
                emptyState: selectedLocalityId ? 'لا توجد أحياء بعد.' : 'اختر المدينة أولًا.',
              },
            ]}
            selectedNode={selectedNode}
            selectedPathLabel={selectedPathLabel}
            pricingItems={pricingQuery.data?.items ?? []}
            quote={quoteQuery.data}
            onCreateNode={(payload) => createAddressNodeMutation.mutateAsync(payload)}
            onUpdateNode={(nodeId, payload) => updateAddressNodeMutation.mutateAsync({ nodeId, payload })}
            onDeleteNode={(nodeId) => deleteAddressNodeMutation.mutateAsync(nodeId)}
            onSavePricing={(payload) => upsertPricingMutation.mutateAsync(payload)}
            onDeletePricing={(pricingId) => deletePricingMutation.mutateAsync(pricingId)}
          />

          <DeliveryAddressPricingManager
            selectedNode={selectedNode}
            selectedPathLabel={selectedPathLabel}
            pricingItems={pricingQuery.data?.items ?? []}
            quote={quoteQuery.data}
            pricingSearch={pricingSearch}
            pricingActiveOnly={pricingActiveOnly}
            onPricingSearchChange={setPricingSearch}
            onPricingActiveOnlyChange={setPricingActiveOnly}
          />
        </section>
      </div>
    </PageShell>
  );
}
