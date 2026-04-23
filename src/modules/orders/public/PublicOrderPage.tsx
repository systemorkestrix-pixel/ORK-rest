import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useOutletContext } from 'react-router-dom';

import { api } from '@/shared/api/client';
import type {
  CreateOrderPayload,
  DeliveryAddressNode,
  Order,
  OrderType,
  PublicJourneyProduct,
  PublicSecondaryOption,
} from '@/shared/api/types';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import type { PublicLayoutOutletContext } from '@/app/layout/PublicLayout';
import { PublicCartSummaryBar } from './components/PublicCartSummaryBar';
import { PublicCheckoutModal } from './components/PublicCheckoutModal';
import { PublicProductsCatalog } from './components/PublicProductsCatalog';
import {
  type CartRow,
  type CartSecondarySelection,
  fallbackDeliveryBlockedReason,
  getCartRowTotal,
  getErrorMessage,
  orderTypeOptions,
} from './publicOrder.helpers';

function getDeepestSelectedNode(nodes: Array<DeliveryAddressNode | undefined>): DeliveryAddressNode | undefined {
  return [...nodes].reverse().find(Boolean);
}

export function PublicOrderPage() {
  useOutletContext<PublicLayoutOutletContext>();
  const location = useLocation();
  const queryClient = useQueryClient();
  const tenantCode = location.pathname.match(/^\/t\/([^/]+)(?:\/|$)/i)?.[1] ?? 'public';
  const tableFromPath = Number(new URLSearchParams(window.location.search).get('table') ?? '');
  const tableId = Number.isFinite(tableFromPath) && tableFromPath > 0 ? tableFromPath : undefined;

  const [orderType, setOrderType] = useState<OrderType>(tableId ? 'dine-in' : 'takeaway');
  const [selectedTable, setSelectedTable] = useState<number | undefined>(tableId);
  const [cart, setCart] = useState<Record<number, CartRow>>({});
  const [secondarySelections, setSecondarySelections] = useState<Record<number, CartSecondarySelection>>({});
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [lastCreatedOrder, setLastCreatedOrder] = useState<Order | null>(null);
  const [showCreatedOrderCard, setShowCreatedOrderCard] = useState(false);
  const [selectedDeliveryRootId, setSelectedDeliveryRootId] = useState<number | undefined>();
  const [selectedDeliveryAdminAreaLevel2Id, setSelectedDeliveryAdminAreaLevel2Id] = useState<number | undefined>();
  const [selectedDeliveryLocalityId, setSelectedDeliveryLocalityId] = useState<number | undefined>();
  const [selectedDeliverySublocalityId, setSelectedDeliverySublocalityId] = useState<number | undefined>();

  const bootstrapQuery = useQuery({
    queryKey: ['public-order-journey-bootstrap', tenantCode, tableId],
    queryFn: () => api.publicOrderJourneyBootstrap(tableId),
    staleTime: 30_000,
  });

  const tablesQuery = useQuery({
    queryKey: ['public-tables', tenantCode, orderType, isCheckoutOpen],
    queryFn: api.publicTables,
    enabled: !tableId && isCheckoutOpen && orderType === 'dine-in',
  });

  const tableSessionQuery = useQuery({
    queryKey: ['public-table-session', tenantCode, tableId],
    queryFn: () => api.publicTableSession(tableId ?? 0),
    enabled: Boolean(tableId),
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const structuredDeliveryReady = Boolean(bootstrapQuery.data?.delivery.structured_locations_enabled);
  const deliveryMode = !tableId && orderType === 'delivery';

  const deliveryRootNodesQuery = useQuery({
    queryKey: ['public-delivery-address-nodes', tenantCode, null],
    queryFn: () => api.publicDeliveryAddressNodes(),
    enabled: isCheckoutOpen && deliveryMode && structuredDeliveryReady,
    staleTime: 5 * 60_000,
  });

  const deliveryAdminAreaLevel2Query = useQuery({
    queryKey: ['public-delivery-address-nodes', tenantCode, selectedDeliveryRootId],
    queryFn: () => api.publicDeliveryAddressNodes(selectedDeliveryRootId),
    enabled: isCheckoutOpen && deliveryMode && structuredDeliveryReady && typeof selectedDeliveryRootId === 'number',
    staleTime: 5 * 60_000,
  });

  const deliveryLocalityQuery = useQuery({
    queryKey: ['public-delivery-address-nodes', tenantCode, selectedDeliveryAdminAreaLevel2Id],
    queryFn: () => api.publicDeliveryAddressNodes(selectedDeliveryAdminAreaLevel2Id),
    enabled:
      isCheckoutOpen &&
      deliveryMode &&
      structuredDeliveryReady &&
      typeof selectedDeliveryAdminAreaLevel2Id === 'number',
    staleTime: 5 * 60_000,
  });

  const deliverySublocalityQuery = useQuery({
    queryKey: ['public-delivery-address-nodes', tenantCode, selectedDeliveryLocalityId],
    queryFn: () => api.publicDeliveryAddressNodes(selectedDeliveryLocalityId),
    enabled: isCheckoutOpen && deliveryMode && structuredDeliveryReady && typeof selectedDeliveryLocalityId === 'number',
    staleTime: 5 * 60_000,
  });

  const deliveryRootNodes = deliveryRootNodesQuery.data?.items ?? [];
  const deliveryAdminAreaLevel2Nodes = deliveryAdminAreaLevel2Query.data?.items ?? [];
  const deliveryLocalityNodes = deliveryLocalityQuery.data?.items ?? [];
  const deliverySublocalityNodes = deliverySublocalityQuery.data?.items ?? [];

  const selectedDeliveryRoot = deliveryRootNodes.find((node) => node.id === selectedDeliveryRootId);
  const selectedDeliveryAdminAreaLevel2 = deliveryAdminAreaLevel2Nodes.find(
    (node) => node.id === selectedDeliveryAdminAreaLevel2Id,
  );
  const selectedDeliveryLocality = deliveryLocalityNodes.find((node) => node.id === selectedDeliveryLocalityId);
  const selectedDeliverySublocality = deliverySublocalityNodes.find((node) => node.id === selectedDeliverySublocalityId);

  const selectedDeliveryNodes = [
    selectedDeliveryRoot,
    selectedDeliveryAdminAreaLevel2,
    selectedDeliveryLocality,
    selectedDeliverySublocality,
  ].filter(Boolean) as DeliveryAddressNode[];

  const deepestSelectedDeliveryNode = getDeepestSelectedNode([
    selectedDeliveryRoot,
    selectedDeliveryAdminAreaLevel2,
    selectedDeliveryLocality,
    selectedDeliverySublocality,
  ]);

  const deliverySelectionIncomplete = useMemo(() => {
    if (!deliveryMode || !structuredDeliveryReady || !deepestSelectedDeliveryNode) {
      return false;
    }
    if (deepestSelectedDeliveryNode.id === selectedDeliveryRoot?.id) {
      return deliveryAdminAreaLevel2Nodes.length > 0 && !selectedDeliveryAdminAreaLevel2Id;
    }
    if (deepestSelectedDeliveryNode.id === selectedDeliveryAdminAreaLevel2?.id) {
      return deliveryLocalityNodes.length > 0 && !selectedDeliveryLocalityId;
    }
    if (deepestSelectedDeliveryNode.id === selectedDeliveryLocality?.id) {
      return deliverySublocalityNodes.length > 0 && !selectedDeliverySublocalityId;
    }
    return false;
  }, [
    deliveryAdminAreaLevel2Nodes.length,
    deliveryLocalityNodes.length,
    deliveryMode,
    deliverySublocalityNodes.length,
    deepestSelectedDeliveryNode,
    selectedDeliveryAdminAreaLevel2,
    selectedDeliveryAdminAreaLevel2Id,
    selectedDeliveryLocality,
    selectedDeliveryLocalityId,
    selectedDeliveryRoot,
    selectedDeliverySublocalityId,
    structuredDeliveryReady,
  ]);

  const selectedDeliveryNode =
    deliveryMode && structuredDeliveryReady && !deliverySelectionIncomplete ? deepestSelectedDeliveryNode : undefined;

  const deliveryQuoteQuery = useQuery({
    queryKey: ['public-delivery-pricing-quote', tenantCode, selectedDeliveryNode?.id],
    queryFn: () => api.publicDeliveryPricingQuote(selectedDeliveryNode?.id),
    enabled: deliveryMode && structuredDeliveryReady && typeof selectedDeliveryNode?.id === 'number',
    staleTime: 15_000,
  });

  const submitMutation = useMutation({
    mutationFn: (payload: CreateOrderPayload) => api.createPublicOrder(payload),
    onSuccess: (createdOrder) => {
      setLastCreatedOrder(createdOrder);
      setShowCreatedOrderCard(true);
      setCart({});
      setSecondarySelections({});
      setPhone('');
      setNotes('');
      setSelectedDeliveryRootId(undefined);
      setSelectedDeliveryAdminAreaLevel2Id(undefined);
      setSelectedDeliveryLocalityId(undefined);
      setSelectedDeliverySublocalityId(undefined);
      setError('');
      setIsCheckoutOpen(true);
      if (tableId) {
        queryClient.invalidateQueries({ queryKey: ['public-table-session', tenantCode, tableId] });
      }
      queryClient.invalidateQueries({ queryKey: ['public-order-journey-bootstrap', tenantCode, tableId] });
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'تعذر إرسال الطلب');
    },
  });

  const operationalCapabilities = bootstrapQuery.data?.capabilities;
  const journeyRules = bootstrapQuery.data?.journey_rules;
  const deliveryFeatureEnabled = operationalCapabilities?.delivery_feature_enabled ?? false;
  const deliveryEnabled = operationalCapabilities?.delivery_enabled ?? false;
  const deliveryBlockedReason = fallbackDeliveryBlockedReason;
  const requirePhoneForTakeaway = journeyRules?.require_phone_for_takeaway ?? false;
  const requirePhoneForDelivery = journeyRules?.require_phone_for_delivery ?? true;
  const tableContext = bootstrapQuery.data?.table_context;
  const fallbackDeliveryFee = bootstrapQuery.data?.delivery.delivery_fee ?? 0;
  const minDeliveryOrderAmount = bootstrapQuery.data?.delivery.min_order_amount ?? 0;
  const tableSession = tableSessionQuery.data;
  const hasActiveTableSession = tableSession?.has_active_session ?? tableContext?.has_active_session ?? false;

  const publicOrderTypeOptions = useMemo(
    () => orderTypeOptions.filter((option) => option.value !== 'delivery' || deliveryFeatureEnabled),
    [deliveryFeatureEnabled],
  );

  useEffect(() => {
    if (showCreatedOrderCard) {
      setIsCheckoutOpen(true);
    }
  }, [showCreatedOrderCard]);

  useEffect(() => {
    if (!tableId && !deliveryFeatureEnabled && orderType === 'delivery') {
      setOrderType('takeaway');
    }
  }, [deliveryFeatureEnabled, orderType, tableId]);

  useEffect(() => {
    if (orderType !== 'delivery') {
      setSelectedDeliveryRootId(undefined);
      setSelectedDeliveryAdminAreaLevel2Id(undefined);
      setSelectedDeliveryLocalityId(undefined);
      setSelectedDeliverySublocalityId(undefined);
    }
  }, [orderType]);

  useEffect(() => {
    if (tableId) {
      setOrderType('dine-in');
      return;
    }
    const defaultOrderType = bootstrapQuery.data?.journey_rules.default_order_type;
    if (defaultOrderType && orderType === 'takeaway' && defaultOrderType !== 'takeaway') {
      setOrderType(defaultOrderType);
    }
  }, [bootstrapQuery.data?.journey_rules.default_order_type, orderType, tableId]);

  const categories = useMemo(() => {
    const map = new Map<string, PublicJourneyProduct[]>();
    for (const category of bootstrapQuery.data?.catalog.categories ?? []) {
      map.set(category.name, [...category.products]);
    }
    return map;
  }, [bootstrapQuery.data?.catalog.categories]);

  const categoryEntries = useMemo(
    () => Array.from(categories.entries()).sort(([first], [second]) => first.localeCompare(second, 'ar')),
    [categories],
  );

  const totalProducts =
    bootstrapQuery.data?.catalog.categories.reduce((sum, category) => sum + category.products.length, 0) ?? 0;
  const secondaryCatalog = bootstrapQuery.data?.catalog.secondary_products ?? [];

  const availablePublicTables = useMemo(
    () => (tablesQuery.data ?? []).filter((table) => table.status !== 'occupied'),
    [tablesQuery.data],
  );

  const cartItems = useMemo(() => Object.values(cart), [cart]);
  const selectedSecondaryRows = useMemo(() => Object.values(secondarySelections), [secondarySelections]);
  const subtotal =
    cartItems.reduce((sum, row) => sum + getCartRowTotal(row), 0) +
    selectedSecondaryRows.reduce((sum, row) => sum + row.option.price * row.quantity, 0);
  const addressSummary = selectedDeliveryNodes.map((node) => node.display_name).join('، ');
  const effectiveDeliveryFee =
    deliveryMode
      ? structuredDeliveryReady
        ? deliveryQuoteQuery.data?.available
          ? deliveryQuoteQuery.data.delivery_fee ?? 0
          : 0
        : fallbackDeliveryFee
      : 0;
  const total = subtotal + effectiveDeliveryFee;

  const needsTableSelection = !tableId && orderType === 'dine-in';
  const hasTableSelection = Boolean(tableId ?? selectedTable);
  const deliveryBelowMinimum = deliveryMode && minDeliveryOrderAmount > 0 && subtotal < minDeliveryOrderAmount;
  const deliverySelectionReady =
    !deliveryMode ||
    !structuredDeliveryReady ||
    (Boolean(selectedDeliveryNode) &&
      !deliverySelectionIncomplete &&
      !deliveryQuoteQuery.isFetching &&
      Boolean(deliveryQuoteQuery.data?.available));

  const submitDisabled =
    submitMutation.isPending ||
    cartItems.length === 0 ||
    (needsTableSelection && !hasTableSelection) ||
    (!tableId && orderType === 'delivery' && (!deliveryFeatureEnabled || !deliveryEnabled)) ||
    deliveryBelowMinimum ||
    !deliverySelectionReady;

  const productsErrorText = bootstrapQuery.isError
    ? getErrorMessage(bootstrapQuery.error, 'تعذر تحميل قائمة المنتجات')
    : '';
  const tablesErrorText = tablesQuery.isError ? getErrorMessage(tablesQuery.error, 'تعذر تحميل قائمة الطاولات') : '';
  const bootstrapErrorText = bootstrapQuery.isError
    ? getErrorMessage(bootstrapQuery.error, 'تعذر تحميل حالة التشغيل')
    : '';
  const tableSessionErrorText = tableId && tableSessionQuery.isError
    ? getErrorMessage(tableSessionQuery.error, 'تعذر تحميل حالة الطاولة')
    : '';

  const updateCartQuantity = (product: PublicJourneyProduct, delta: number) => {
    setCart((prev) => {
      const currentQuantity = prev[product.id]?.quantity ?? 0;
      const nextQuantity = Math.max(0, currentQuantity + delta);
      const next = { ...prev };

      if (nextQuantity <= 0) {
        delete next[product.id];
        return next;
      }

      next[product.id] = {
        product,
        quantity: nextQuantity,
      };
      return next;
    });
  };

  const updateSecondarySelectionQuantity = (option: PublicSecondaryOption, delta: number) => {
    setSecondarySelections((current) => {
      const next = { ...current };
      const currentQuantity = next[option.product_id]?.quantity ?? 0;
      const rawQuantity = currentQuantity + delta;
      const nextQuantity = Math.max(0, Math.min(rawQuantity, option.max_quantity > 0 ? option.max_quantity : 99));

      if (nextQuantity <= 0) {
        delete next[option.product_id];
        return next;
      }

      next[option.product_id] = {
        option,
        quantity: nextQuantity,
      };
      return next;
    });
  };

  const submitOrder = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    const trimmedPhone = phone.trim();

    if (cartItems.length === 0) {
      setError('يرجى إضافة صنف واحد على الأقل قبل الإرسال');
      return;
    }

    if (!tableId && orderType === 'delivery' && (!deliveryFeatureEnabled || !deliveryEnabled)) {
      setError(deliveryBlockedReason);
      return;
    }

    if (!tableId && orderType === 'delivery' && requirePhoneForDelivery && !trimmedPhone) {
      setError('يرجى إدخال رقم الهاتف لطلبات التوصيل.');
      return;
    }

    if (!tableId && orderType === 'takeaway' && requirePhoneForTakeaway && !trimmedPhone) {
      setError('يرجى إدخال رقم الهاتف لإتمام الطلب.');
      return;
    }

    if (!tableId && orderType === 'delivery' && !structuredDeliveryReady) {
      setError('خدمة التوصيل تحتاج إلى ضبط عناوين التغطية أولًا قبل استقبال الطلبات العامة.');
      return;
    }

    if (!tableId && orderType === 'delivery' && deliveryBelowMinimum) {
      setError(`يلزم أن يبلغ الحد الأدنى للتوصيل ${minDeliveryOrderAmount.toFixed(2)} د.ج.`);
      return;
    }

    if (!tableId && orderType === 'delivery' && !selectedDeliveryNode) {
      setError('يرجى إكمال اختيار عنوان التوصيل من القوائم المتاحة.');
      return;
    }

    if (!tableId && orderType === 'delivery' && !deliveryQuoteQuery.data?.available) {
      setError(deliveryQuoteQuery.data?.message ?? 'العنوان المختار غير مغطى ضمن التوصيل الحالي.');
      return;
    }

    if (!tableId && orderType === 'dine-in' && !selectedTable) {
      setError('يرجى اختيار رقم الطاولة قبل الإرسال');
      return;
    }

    const payload: CreateOrderPayload = {
      type: tableId ? 'dine-in' : orderType,
      items: cartItems
        .map((item) => ({
          product_id: item.product.id,
          quantity: item.quantity,
        }))
        .concat(
          selectedSecondaryRows.map((selection) => ({
            product_id: selection.option.product_id,
            quantity: selection.quantity,
          })),
        ),
      notes: notes || undefined,
    };

    if (tableId || orderType === 'dine-in') {
      payload.table_id = tableId ?? selectedTable;
    }

    if (!tableId && (orderType === 'takeaway' || orderType === 'delivery') && trimmedPhone) {
      payload.phone = trimmedPhone;
    }

    if (!tableId && orderType === 'delivery') {
      payload.address = addressSummary;
      payload.delivery_location_key = deliveryQuoteQuery.data?.location_key ?? String(selectedDeliveryNode?.id ?? '');
    }

    submitMutation.mutate(payload);
  };

  return (
    <div dir="rtl" className="mx-auto max-w-7xl space-y-5 px-3 py-4 text-right md:px-5 md:py-6">
      {bootstrapErrorText ? (
        <div className="rounded-2xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-200">
          {bootstrapErrorText}
        </div>
      ) : null}

      {tableSessionErrorText ? (
        <div className="rounded-2xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-200">
          {tableSessionErrorText}
        </div>
      ) : null}

      {!tableId && tablesErrorText ? (
        <div className="rounded-2xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-200">
          {tablesErrorText}
        </div>
      ) : null}

      {tableContext?.has_active_session ? (
        <section className="rounded-[26px] border border-white/10 bg-[#17110d] p-4 shadow-[0_18px_50px_rgba(0,0,0,0.24)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-black text-white">هذه الطاولة لديها جلسة نشطة</p>
              <p className="text-xs text-stone-400">
                طلبات نشطة: {tableContext.active_orders_count} • غير مسددة: {tableContext.unsettled_orders_count} • الإجمالي: {tableContext.unpaid_total.toFixed(2)} د.ج
              </p>
            </div>

            <button
              type="button"
              onClick={() => setIsCheckoutOpen(true)}
              className="inline-flex min-h-[42px] items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] px-4 text-sm font-black text-stone-100 transition hover:bg-white/[0.08]"
            >
              إضافة طلب جديد للطاولة
            </button>
          </div>
        </section>
      ) : null}

      <PublicProductsCatalog
        productsLoading={bootstrapQuery.isLoading}
        productsErrorText={productsErrorText}
        totalProducts={totalProducts}
        categoryEntries={categoryEntries}
        cart={cart}
        onIncreaseQuantity={(product) => updateCartQuantity(product, 1)}
        onDecreaseQuantity={(product) => updateCartQuantity(product, -1)}
      />

      <PublicCartSummaryBar
        itemCount={cartItems.reduce(
          (sum, item) => sum + item.quantity,
          selectedSecondaryRows.reduce((sum, selection) => sum + selection.quantity, 0),
        )}
        total={total}
        onOpenCheckout={() => {
          setShowCreatedOrderCard(false);
          setIsCheckoutOpen(true);
        }}
      />

      <PublicCheckoutModal
        open={isCheckoutOpen}
        tableId={tableId}
        orderType={orderType}
        orderTypeOptions={publicOrderTypeOptions}
        availablePublicTables={availablePublicTables}
        cartItems={cartItems}
        subtotal={subtotal}
        secondaryCatalog={secondaryCatalog}
        secondarySelections={secondarySelections}
        deliveryFee={effectiveDeliveryFee}
        minDeliveryOrderAmount={minDeliveryOrderAmount}
        total={total}
        requirePhoneForTakeaway={requirePhoneForTakeaway}
        requirePhoneForDelivery={requirePhoneForDelivery}
        phone={phone}
        addressSummary={addressSummary}
        notes={notes}
        selectedTable={selectedTable}
        structuredDeliveryReady={structuredDeliveryReady}
        deliveryRootNodes={deliveryRootNodes}
        deliveryAdminAreaLevel2Nodes={deliveryAdminAreaLevel2Nodes}
        deliveryLocalityNodes={deliveryLocalityNodes}
        deliverySublocalityNodes={deliverySublocalityNodes}
        selectedDeliveryRootId={selectedDeliveryRootId}
        selectedDeliveryAdminAreaLevel2Id={selectedDeliveryAdminAreaLevel2Id}
        selectedDeliveryLocalityId={selectedDeliveryLocalityId}
        selectedDeliverySublocalityId={selectedDeliverySublocalityId}
        deliveryQuote={deliveryQuoteQuery.data}
        deliveryQuoteLoading={deliveryQuoteQuery.isFetching}
        deliverySelectionIncomplete={deliverySelectionIncomplete}
        submitPending={submitMutation.isPending}
        submitDisabled={submitDisabled}
        deliveryEnabled={deliveryEnabled}
        deliveryBlockedReason={deliveryBlockedReason}
        error={error}
        lastCreatedOrder={lastCreatedOrder}
        showSuccess={showCreatedOrderCard}
        onClose={() => setIsCheckoutOpen(false)}
        onOrderTypeChange={setOrderType}
        onPhoneChange={setPhone}
        onNotesChange={setNotes}
        onSecondaryQuantityChange={updateSecondarySelectionQuantity}
        onSelectedTableChange={setSelectedTable}
        onDeliveryRootChange={(value) => {
          setSelectedDeliveryRootId(value);
          setSelectedDeliveryAdminAreaLevel2Id(undefined);
          setSelectedDeliveryLocalityId(undefined);
          setSelectedDeliverySublocalityId(undefined);
        }}
        onDeliveryAdminAreaLevel2Change={(value) => {
          setSelectedDeliveryAdminAreaLevel2Id(value);
          setSelectedDeliveryLocalityId(undefined);
          setSelectedDeliverySublocalityId(undefined);
        }}
        onDeliveryLocalityChange={(value) => {
          setSelectedDeliveryLocalityId(value);
          setSelectedDeliverySublocalityId(undefined);
        }}
        onDeliverySublocalityChange={setSelectedDeliverySublocalityId}
        onSubmit={submitOrder}
        onCloseSuccess={() => {
          setShowCreatedOrderCard(false);
          setIsCheckoutOpen(false);
        }}
      />
    </div>
  );
}
