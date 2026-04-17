import { createContext, type PropsWithChildren, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type {
  OperationalHeartDashboard,
  Order,
  TableSession,
} from '@/shared/api/types';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { sanitizeMojibakeText } from '@/shared/utils/textSanitizer';

export type AlertDomainKey = 'orders' | 'kitchen' | 'inventory' | 'financial' | 'delivery' | 'system' | 'audit';
export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface DomainAlertAction {
  id: string;
  title: string;
  detail: string;
  actionRoute: string;
  severity: AlertSeverity;
  isRead?: boolean;
}

export interface DomainAlertSummary {
  key: AlertDomainKey;
  label: string;
  badge: number;
  severity: AlertSeverity;
  actions: DomainAlertAction[];
  unreadCount: number;
}

interface ManagerAlertsContextValue {
  operationalHeart: OperationalHeartDashboard | null;
  notifications: DomainAlertSummary[];
  unresolvedCount: number;
  isLoading: boolean;
  isError: boolean;
  isAlertRead: (id: string) => boolean;
  toggleAlertRead: (id: string) => void;
  markAlertRead: (id: string) => void;
  markAlertUnread: (id: string) => void;
}

const ManagerAlertsContext = createContext<ManagerAlertsContextValue | null>(null);

function buildConsoleRoute(
  channel: string,
  section: string,
  params?: Record<string, string | null | undefined>
): string {
  const searchParams = new URLSearchParams({ channel, section });

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (!value) {
        continue;
      }
      searchParams.set(key, value);
    }
  }

  return `/console?${searchParams.toString()}`;
}

function normalizeSeverity(value?: string | null): AlertSeverity {
  if (value === 'critical') {
    return 'critical';
  }
  if (value === 'warning') {
    return 'warning';
  }
  return 'info';
}

function maxSeverity(current: AlertSeverity, next: AlertSeverity): AlertSeverity {
  const rank: Record<AlertSeverity, number> = { info: 1, warning: 2, critical: 3 };
  return rank[next] > rank[current] ? next : current;
}

function dedupeActions(actions: DomainAlertAction[]): DomainAlertAction[] {
  const actionMap = new Map<string, DomainAlertAction>();

  for (const action of actions) {
    const key = `${action.actionRoute}::${sanitizeMojibakeText(action.title).trim().toLowerCase()}`;
    const previous = actionMap.get(key);

    if (!previous) {
      actionMap.set(key, action);
      continue;
    }

    actionMap.set(key, {
      ...previous,
      detail: previous.detail.length >= action.detail.length ? previous.detail : action.detail,
      severity: maxSeverity(previous.severity, action.severity),
    });
  }

  return Array.from(actionMap.values());
}

function formatCountLabel(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural;
}

function getOldestOrderAgeMinutes(orders: Order[]): number {
  const now = Date.now();
  let oldestMinutes = 0;

  for (const order of orders) {
    const parsed = new Date(order.created_at).getTime();
    if (Number.isNaN(parsed)) {
      continue;
    }
    const ageMinutes = Math.max(0, Math.floor((now - parsed) / 60_000));
    if (ageMinutes > oldestMinutes) {
      oldestMinutes = ageMinutes;
    }
  }

  return oldestMinutes;
}

function formatOldestAgeLabel(minutes: number): string {
  if (minutes <= 0) {
    return 'الآن';
  }
  if (minutes < 60) {
    return `منذ ${minutes} د`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (remainingMinutes === 0) {
    return `منذ ${hours} س`;
  }
  return `منذ ${hours} س ${remainingMinutes} د`;
}

function playAlertChime(): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    const AudioContextCtor =
      (window as typeof window & { webkitAudioContext?: typeof AudioContext }).AudioContext ??
      (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

    if (!AudioContextCtor) {
      return;
    }

    const context = new AudioContextCtor();
    const now = context.currentTime;
    const masterGain = context.createGain();
    masterGain.gain.setValueAtTime(0.0001, now);
    masterGain.gain.exponentialRampToValueAtTime(0.085, now + 0.02);
    masterGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.42);
    masterGain.connect(context.destination);

    const firstOscillator = context.createOscillator();
    firstOscillator.type = 'sine';
    firstOscillator.frequency.setValueAtTime(784, now);
    firstOscillator.frequency.exponentialRampToValueAtTime(1046, now + 0.16);
    firstOscillator.connect(masterGain);
    firstOscillator.start(now);
    firstOscillator.stop(now + 0.18);

    const secondOscillator = context.createOscillator();
    secondOscillator.type = 'triangle';
    secondOscillator.frequency.setValueAtTime(1174, now + 0.14);
    secondOscillator.frequency.exponentialRampToValueAtTime(1567, now + 0.32);
    secondOscillator.connect(masterGain);
    secondOscillator.start(now + 0.14);
    secondOscillator.stop(now + 0.36);

    window.setTimeout(() => {
      void context.close().catch(() => undefined);
    }, 800);
  } catch {
    // Keep the alerts UI usable even if the environment blocks sound.
  }
}

function resolveDomainFromRoute(route: string | null | undefined): AlertDomainKey {
  const normalized = String(route ?? '').toLowerCase();

  if (
    normalized.includes('/console/system/audit-log') ||
    normalized.includes('/system/audit-log') ||
    normalized.includes('/manager/audit') ||
    normalized.includes('section=audit')
  ) {
    return 'audit';
  }

  if (
    normalized.includes('/console/kitchen') ||
    normalized.includes('/manager/kitchen') ||
    normalized.includes('/kitchen-monitor') ||
    normalized.includes('channel=kitchen')
  ) {
    return 'kitchen';
  }

  if (
    normalized.includes('/console/warehouse') ||
    normalized.includes('/warehouse') ||
    normalized.includes('/manager/warehouse') ||
    normalized.includes('channel=warehouse')
  ) {
    return 'inventory';
  }

  if (
    normalized.includes('/console/finance') ||
    normalized.includes('/finance') ||
    normalized.includes('/manager/financial') ||
    normalized.includes('/manager/expenses') ||
    normalized.includes('channel=finance')
  ) {
    return 'financial';
  }

  if (
    normalized.includes('/console/delivery') ||
    normalized.includes('/delivery') ||
    normalized.includes('/manager/delivery') ||
    normalized.includes('channel=delivery')
  ) {
    return 'delivery';
  }

  if (
    normalized.includes('/console/operations') ||
    normalized.includes('/console/restaurant') ||
    normalized.includes('/operations') ||
    normalized.includes('/manager/orders') ||
    normalized.includes('/manager/tables') ||
    normalized.includes('/manager/products') ||
    normalized.includes('channel=operations') ||
    normalized.includes('channel=menu')
  ) {
    return 'orders';
  }

  return 'system';
}

function buildDomainNotifications(
  snapshot: OperationalHeartDashboard | null,
  readIds: Set<string>,
  channelModes?: Record<string, 'core' | 'runtime_hidden' | 'disabled'>
): DomainAlertSummary[] {
  const domainMap: Record<AlertDomainKey, DomainAlertSummary> = {
    orders: { key: 'orders', label: 'الطلبات', badge: 0, severity: 'info', actions: [], unreadCount: 0 },
    kitchen: { key: 'kitchen', label: 'المطبخ', badge: 0, severity: 'info', actions: [], unreadCount: 0 },
    inventory: { key: 'inventory', label: 'المخزون', badge: 0, severity: 'info', actions: [], unreadCount: 0 },
    financial: { key: 'financial', label: 'العمليات المالية', badge: 0, severity: 'info', actions: [], unreadCount: 0 },
    delivery: { key: 'delivery', label: 'التوصيل', badge: 0, severity: 'info', actions: [], unreadCount: 0 },
    system: { key: 'system', label: 'النظام', badge: 0, severity: 'info', actions: [], unreadCount: 0 },
    audit: { key: 'audit', label: 'سجل التدقيق', badge: 0, severity: 'info', actions: [], unreadCount: 0 },
  };

  if (!snapshot) {
    return Object.values(domainMap);
  }

  for (const incident of snapshot.incidents) {
    const domain = resolveDomainFromRoute(incident.action_route);
    const severity = normalizeSeverity(incident.severity);
    domainMap[domain].actions.push({
      id: `incident-${incident.code}`,
      title: sanitizeMojibakeText(incident.title),
      detail: sanitizeMojibakeText(incident.message),
      actionRoute: incident.action_route,
      severity,
    });
    domainMap[domain].severity = maxSeverity(domainMap[domain].severity, severity);
  }

  for (const item of snapshot.reconciliations ?? []) {
    if (item.ok) {
      continue;
    }

    const severity = normalizeSeverity(item.severity);
    const domain = resolveDomainFromRoute(item.action_route);
    domainMap[domain].actions.push({
      id: `recon-${item.key}`,
      title: sanitizeMojibakeText(item.label),
      detail: sanitizeMojibakeText(item.detail),
      actionRoute: item.action_route,
      severity,
    });
    domainMap[domain].severity = maxSeverity(domainMap[domain].severity, severity);
  }

  if ((snapshot.warehouse_control?.low_stock_items ?? 0) > 0) {
    domainMap.inventory.actions.push({
      id: 'warehouse-low-stock',
      title: 'أصناف وصلت إلى حد التنبيه',
      detail: `يوجد ${snapshot.warehouse_control?.low_stock_items ?? 0} صنفًا يحتاج مراجعة الكمية أو التوريد.`,
      actionRoute: buildConsoleRoute('warehouse', 'warehouseOverview'),
      severity: normalizeSeverity(snapshot.warehouse_control?.severity),
    });
  }

  if ((snapshot.expenses_control?.pending_approvals ?? 0) > 0) {
    domainMap.financial.actions.push({
      id: 'expenses-pending-approvals',
      title: 'مصاريف بانتظار الاعتماد',
      detail: `يوجد ${snapshot.expenses_control?.pending_approvals ?? 0} طلب مصروف يحتاج إلى مراجعة واعتماد.`,
      actionRoute: buildConsoleRoute('finance', 'financeOverview'),
      severity: normalizeSeverity(snapshot.expenses_control?.severity),
    });
  }

  if ((snapshot.warehouse_control?.pending_stock_counts ?? 0) > 0) {
    domainMap.inventory.actions.push({
      id: 'warehouse-pending-counts',
      title: 'مطابقات جرد معلّقة',
      detail: `يوجد ${snapshot.warehouse_control?.pending_stock_counts ?? 0} جردًا أو مطابقة بانتظار التسوية.`,
      actionRoute: buildConsoleRoute('warehouse', 'warehouseCounts'),
      severity: normalizeSeverity(snapshot.warehouse_control?.severity),
    });
  }

  if ((snapshot.tables_control?.blocked_settlement_tables ?? 0) > 0) {
    domainMap.orders.actions.push({
      id: 'tables-blocked-settlement',
      title: 'طاولات تمنع التسوية',
      detail: `عدد الطاولات المعلّقة: ${snapshot.tables_control?.blocked_settlement_tables ?? 0}`,
      actionRoute: snapshot.tables_control?.action_route ?? buildConsoleRoute('operations', 'tables'),
      severity: 'warning',
    });
  }

  if (snapshot.financial_control && !snapshot.financial_control.shift_closed_today) {
    const activityCount =
      (snapshot.financial_control.sales_transactions_today ?? 0) +
      (snapshot.financial_control.expense_transactions_today ?? 0);

    if (activityCount > 0) {
      domainMap.financial.actions.push({
        id: 'financial-shift-open',
        title: 'الوردية ما تزال مفتوحة',
        detail: `تم تسجيل ${activityCount} حركة مالية اليوم والوردية لم تُغلق بعد.`,
        actionRoute: buildConsoleRoute('finance', 'financeOverview'),
        severity: 'warning',
      });
    }
  }

  if (snapshot.financial_control && Math.abs(snapshot.financial_control.latest_shift_variance ?? 0) > 0) {
    domainMap.financial.actions.push({
      id: 'financial-shift-variance',
      title: 'فرق في الصندوق أو التسوية',
      detail: `تم رصد فرق بقيمة ${Math.abs(snapshot.financial_control.latest_shift_variance ?? 0).toFixed(2)} د.ج ويحتاج إلى مراجعة التسوية.`,
      actionRoute: buildConsoleRoute('finance', 'financeOverview'),
      severity: normalizeSeverity(snapshot.financial_control.severity),
    });
  }

  const allowedDomains = new Set<AlertDomainKey>(['orders', 'system', 'audit']);
  if ((channelModes?.kitchen ?? 'disabled') === 'core') {
    allowedDomains.add('kitchen');
  }
  if ((channelModes?.delivery ?? 'core') === 'core') {
    allowedDomains.add('delivery');
  }
  if ((channelModes?.warehouse ?? 'disabled') === 'core') {
    allowedDomains.add('inventory');
  }
  if ((channelModes?.finance ?? 'disabled') === 'core') {
    allowedDomains.add('financial');
  }

  return Object.values(domainMap)
    .filter((domain) => allowedDomains.has(domain.key))
    .map((domain) => {
      const actions = dedupeActions(domain.actions)
        .map((action) => ({
          ...action,
          isRead: readIds.has(action.id),
        }))
        .slice(0, 24);

      const unreadCount = actions.filter((action) => !action.isRead).length;
      const unreadSeverity = actions.reduce<AlertSeverity>((current, action) => {
        if (action.isRead) {
          return current;
        }
        return maxSeverity(current, action.severity);
      }, 'info');

      return {
        ...domain,
        badge: unreadCount,
        unreadCount,
        severity: unreadCount > 0 ? unreadSeverity : 'info',
        actions,
      };
    });
}

function buildOperationalFallbackNotifications(
  activeOrders: Order[],
  tableSessions: TableSession[],
  readIds: Set<string>,
  workflowProfile: string | undefined,
  deliveryFeatureEnabled: boolean
): DomainAlertSummary[] {
  const awaitingConfirmation = activeOrders.filter((order) => order.status === 'CREATED');
  const awaitingKitchenDispatch = activeOrders.filter((order) => order.status === 'CONFIRMED');
  const sentToKitchen = activeOrders.filter((order) => order.status === 'SENT_TO_KITCHEN');
  const inPreparation = activeOrders.filter((order) => order.status === 'IN_PREPARATION');
  const readyForDelivery = activeOrders.filter(
    (order) => order.status === 'READY' && order.type === 'delivery' && deliveryFeatureEnabled
  );
  const readyForHandoff = activeOrders.filter(
    (order) => order.status === 'READY' && !(order.type === 'delivery' && deliveryFeatureEnabled)
  );
  const outForDelivery = activeOrders.filter((order) => order.status === 'OUT_FOR_DELIVERY');
  const unsettledTables = tableSessions.filter(
    (session) => session.has_active_session && (session.unsettled_orders_count ?? 0) > 0
  );

  const orderActions: DomainAlertAction[] = [];
  const kitchenActions: DomainAlertAction[] = [];
  const deliveryActions: DomainAlertAction[] = [];
  const kitchenManaged = workflowProfile === 'kitchen_managed' || workflowProfile === 'kitchen_delivery_managed';

  if (awaitingConfirmation.length > 0) {
    const oldestAge = formatOldestAgeLabel(getOldestOrderAgeMinutes(awaitingConfirmation));
    orderActions.push({
      id: 'orders-awaiting-confirmation',
      title: 'طلبات بانتظار التأكيد',
      detail: `يوجد ${awaitingConfirmation.length} ${formatCountLabel(
        awaitingConfirmation.length,
        'طلب يحتاج إلى التأكيد الآن.',
        'طلبات تحتاج إلى التأكيد الآن.'
      )} • ${oldestAge}`,
      actionRoute: buildConsoleRoute('operations', 'orders', { status: 'CREATED' }),
      severity: awaitingConfirmation.length >= 5 ? 'critical' : 'warning',
    });
  }

  if (kitchenManaged && awaitingKitchenDispatch.length > 0) {
    const oldestAge = formatOldestAgeLabel(getOldestOrderAgeMinutes(awaitingKitchenDispatch));
    kitchenActions.push({
      id: 'kitchen-awaiting-dispatch',
      title: 'طلبات بانتظار الإرسال إلى المطبخ',
      detail: `يوجد ${awaitingKitchenDispatch.length} ${formatCountLabel(
        awaitingKitchenDispatch.length,
        'طلب مؤكد لم يُرسل إلى المطبخ بعد.',
        'طلبات مؤكدة لم تُرسل إلى المطبخ بعد.'
      )} • ${oldestAge}`,
      actionRoute: buildConsoleRoute('operations', 'orders', { status: 'CONFIRMED' }),
      severity: awaitingKitchenDispatch.length >= 4 ? 'critical' : 'warning',
    });
  }

  if (kitchenManaged && sentToKitchen.length > 0) {
    const oldestAge = formatOldestAgeLabel(getOldestOrderAgeMinutes(sentToKitchen));
    kitchenActions.push({
      id: 'kitchen-awaiting-start',
      title: 'طلبات وصلت إلى المطبخ وتنتظر البدء',
      detail: `يوجد ${sentToKitchen.length} ${formatCountLabel(
        sentToKitchen.length,
        'طلب داخل طابور المطبخ بانتظار البدء.',
        'طلبات داخل طابور المطبخ بانتظار البدء.'
      )} • ${oldestAge}`,
      actionRoute: buildConsoleRoute('kitchen', 'kitchenMonitor'),
      severity: sentToKitchen.length >= 4 ? 'critical' : 'warning',
    });
  }

  if (kitchenManaged && inPreparation.length > 0) {
    const oldestAge = formatOldestAgeLabel(getOldestOrderAgeMinutes(inPreparation));
    kitchenActions.push({
      id: 'kitchen-in-preparation',
      title: 'طلبات قيد التحضير',
      detail: `يوجد ${inPreparation.length} ${formatCountLabel(
        inPreparation.length,
        'طلب قيد التحضير الآن.',
        'طلبات قيد التحضير الآن.'
      )} • ${oldestAge}`,
      actionRoute: buildConsoleRoute('kitchen', 'kitchenMonitor'),
      severity: 'info',
    });
  }

  if (readyForHandoff.length > 0) {
    const oldestAge = formatOldestAgeLabel(getOldestOrderAgeMinutes(readyForHandoff));
    orderActions.push({
      id: 'orders-ready-for-handoff',
      title: 'طلبات جاهزة للتسليم',
      detail: `يوجد ${readyForHandoff.length} ${formatCountLabel(
        readyForHandoff.length,
        'طلب جاهز للتسليم أو الإغلاق.',
        'طلبات جاهزة للتسليم أو الإغلاق.'
      )} • ${oldestAge}`,
      actionRoute: buildConsoleRoute('operations', 'orders', { status: 'READY' }),
      severity: 'info',
    });
  }

  if (readyForDelivery.length > 0) {
    const oldestAge = formatOldestAgeLabel(getOldestOrderAgeMinutes(readyForDelivery));
    deliveryActions.push({
      id: 'delivery-ready-orders',
      title: 'طلبات جاهزة للتوصيل',
      detail: `يوجد ${readyForDelivery.length} ${formatCountLabel(
        readyForDelivery.length,
        'طلب جاهز بانتظار التسليم إلى التوصيل.',
        'طلبات جاهزة بانتظار التسليم إلى التوصيل.'
      )} • ${oldestAge}`,
      actionRoute: buildConsoleRoute('delivery', 'delivery'),
      severity: readyForDelivery.length >= 4 ? 'warning' : 'info',
    });
  }

  if (outForDelivery.length > 0) {
    const oldestAge = formatOldestAgeLabel(getOldestOrderAgeMinutes(outForDelivery));
    deliveryActions.push({
      id: 'delivery-out-for-delivery',
      title: 'طلبات خرجت للتوصيل',
      detail: `يوجد ${outForDelivery.length} ${formatCountLabel(
        outForDelivery.length,
        'طلب قيد التوصيل الآن.',
        'طلبات قيد التوصيل الآن.'
      )} • ${oldestAge}`,
      actionRoute: buildConsoleRoute('delivery', 'delivery'),
      severity: 'info',
    });
  }

  if (unsettledTables.length > 0) {
    orderActions.push({
      id: 'tables-open-settlements',
      title: 'جلسات مفتوحة تحتاج تسوية',
      detail: `يوجد ${unsettledTables.length} ${formatCountLabel(
        unsettledTables.length,
        'طاولة عليها جلسة مفتوحة بانتظار التسوية.',
        'طاولات عليها جلسات مفتوحة بانتظار التسوية.'
      )}`,
      actionRoute: buildConsoleRoute('operations', 'tables'),
      severity: 'warning',
    });
  }

  const actions = dedupeActions(orderActions).map((action) => ({
    ...action,
    isRead: readIds.has(action.id),
  }));
  const kitchenActionsResolved = dedupeActions(kitchenActions).map((action) => ({
    ...action,
    isRead: readIds.has(action.id),
  }));
  const deliveryActionsResolved = dedupeActions(deliveryActions).map((action) => ({
    ...action,
    isRead: readIds.has(action.id),
  }));
  const unreadCount = actions.filter((action) => !action.isRead).length;
  const severity = actions.reduce<AlertSeverity>((current, action) => {
    if (action.isRead) {
      return current;
    }
    return maxSeverity(current, action.severity);
  }, 'info');
  const kitchenUnreadCount = kitchenActionsResolved.filter((action) => !action.isRead).length;
  const kitchenSeverity = kitchenActionsResolved.reduce<AlertSeverity>((current, action) => {
    if (action.isRead) {
      return current;
    }
    return maxSeverity(current, action.severity);
  }, 'info');
  const deliveryUnreadCount = deliveryActionsResolved.filter((action) => !action.isRead).length;
  const deliverySeverity = deliveryActionsResolved.reduce<AlertSeverity>((current, action) => {
    if (action.isRead) {
      return current;
    }
    return maxSeverity(current, action.severity);
  }, 'info');

  return [
    {
      key: 'orders',
      label: 'الطلبات والطاولات',
      badge: unreadCount,
      unreadCount,
      severity: unreadCount > 0 ? severity : 'info',
      actions,
    },
    {
      key: 'kitchen',
      label: 'المطبخ',
      badge: kitchenUnreadCount,
      unreadCount: kitchenUnreadCount,
      severity: kitchenUnreadCount > 0 ? kitchenSeverity : 'info',
      actions: kitchenActionsResolved,
    },
    {
      key: 'delivery',
      label: 'التوصيل',
      badge: deliveryUnreadCount,
      unreadCount: deliveryUnreadCount,
      severity: deliveryUnreadCount > 0 ? deliverySeverity : 'info',
      actions: deliveryActionsResolved,
    },
    {
      key: 'system',
      label: 'النظام',
      badge: 0,
      severity: 'info',
      actions: [],
      unreadCount: 0,
    },
    {
      key: 'audit',
      label: 'الحالة',
      badge: 0,
      severity: 'info',
      actions: [],
      unreadCount: 0,
    },
  ];
}

function mergeDomainNotifications(
  primary: DomainAlertSummary[],
  secondary: DomainAlertSummary[]
): DomainAlertSummary[] {
  const merged = new Map<AlertDomainKey, DomainAlertSummary>();

  for (const domain of [...primary, ...secondary]) {
    const existing = merged.get(domain.key);
    if (!existing) {
      merged.set(domain.key, {
        ...domain,
        actions: [...domain.actions],
      });
      continue;
    }

    const actions = dedupeActions([...existing.actions, ...domain.actions]).slice(0, 24);
    const unreadCount = actions.filter((action) => !action.isRead).length;
    const severity = actions.reduce<AlertSeverity>((current, action) => {
      if (action.isRead) {
        return current;
      }
      return maxSeverity(current, action.severity);
    }, 'info');

    merged.set(domain.key, {
      ...existing,
      label: existing.label || domain.label,
      actions,
      unreadCount,
      badge: unreadCount,
      severity: unreadCount > 0 ? severity : 'info',
    });
  }

  return Array.from(merged.values());
}

export function ManagerAlertsProvider({ children }: PropsWithChildren) {
  const role = useAuthStore((state) => state.role);
  const user = useAuthStore((state) => state.user);
  const previousUnreadIdsRef = useRef<Set<string>>(new Set());
  const hasPrimedAudioRef = useRef(false);
  const storageKey = useMemo(() => `manager-alerts-read:${user?.id ?? 'anonymous'}`, [user?.id]);
  const [readIds, setReadIds] = useState<Set<string>>(() => {
    if (typeof window === 'undefined') {
      return new Set();
    }

    try {
      const raw = window.localStorage.getItem(storageKey);
      const parsed = raw ? (JSON.parse(raw) as string[]) : [];
      return new Set(parsed);
    } catch {
      return new Set();
    }
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      const raw = window.localStorage.getItem(storageKey);
      const parsed = raw ? (JSON.parse(raw) as string[]) : [];
      setReadIds(new Set(parsed));
    } catch {
      setReadIds(new Set());
    }
  }, [storageKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      window.localStorage.setItem(storageKey, JSON.stringify(Array.from(readIds)));
    } catch {
      // Ignore storage failures.
    }
  }, [readIds, storageKey]);

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context'],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });
  const tenantScopeKey = tenantContextQuery.data?.tenant_id ?? 'tenant-unknown';
  const operationsChannelEnabled =
    tenantContextQuery.isSuccess && (tenantContextQuery.data?.channel_modes?.operations ?? 'disabled') === 'core';

  const operationalHeartQuery = useQuery({
    queryKey: ['manager-dashboard-operational-heart', tenantScopeKey],
    queryFn: () => api.managerDashboardOperationalHeart(role ?? 'manager'),
    enabled:
      role === 'manager' &&
      tenantContextQuery.isSuccess &&
      (tenantContextQuery.data?.channel_modes?.intelligence ?? 'disabled') === 'core',
    refetchInterval: adaptiveRefetchInterval(3000),
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
  const operationalCapabilitiesQuery = useQuery({
    queryKey: ['manager-operational-capabilities', tenantScopeKey],
    queryFn: () => api.managerOperationalCapabilities(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });
  const activeOrdersQuery = useQuery({
    queryKey: ['manager-active-orders', tenantScopeKey],
    queryFn: () => api.managerActiveOrders(role ?? 'manager', 200),
    enabled: role === 'manager' && operationsChannelEnabled,
    refetchInterval: adaptiveRefetchInterval(4000),
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });
  const tableSessionsQuery = useQuery({
    queryKey: ['manager-table-sessions', tenantScopeKey],
    queryFn: () => api.managerTableSessions(role ?? 'manager'),
    enabled: role === 'manager' && operationsChannelEnabled,
    refetchInterval: adaptiveRefetchInterval(5000),
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });

  const notifications = useMemo(
    () => {
      const fallbackNotifications = buildOperationalFallbackNotifications(
        activeOrdersQuery.data ?? [],
        tableSessionsQuery.data ?? [],
        readIds,
        operationalCapabilitiesQuery.data?.workflow_profile,
        operationalCapabilitiesQuery.data?.delivery_feature_enabled ?? false
      );

      if (!operationalHeartQuery.data) {
        return fallbackNotifications;
      }

      return mergeDomainNotifications(
        buildDomainNotifications(operationalHeartQuery.data, readIds, tenantContextQuery.data?.channel_modes),
        fallbackNotifications
      );
    },
    [
      activeOrdersQuery.data,
      operationalCapabilitiesQuery.data?.delivery_feature_enabled,
      operationalCapabilitiesQuery.data?.workflow_profile,
      operationalHeartQuery.data,
      readIds,
      tableSessionsQuery.data,
      tenantContextQuery.data?.channel_modes,
    ]
  );

  const unresolvedCount = useMemo(() => notifications.reduce((sum, row) => sum + row.badge, 0), [notifications]);
  const unreadAlertIds = useMemo(
    () =>
      notifications.flatMap((domain) =>
        domain.actions.filter((action) => !action.isRead).map((action) => action.id)
      ),
    [notifications]
  );

  useEffect(() => {
    const currentUnreadIds = new Set(unreadAlertIds);

    if (!hasPrimedAudioRef.current) {
      previousUnreadIdsRef.current = currentUnreadIds;
      hasPrimedAudioRef.current = true;
      return;
    }

    const hasNewUnreadAlert = unreadAlertIds.some((id) => !previousUnreadIdsRef.current.has(id));
    previousUnreadIdsRef.current = currentUnreadIds;

    if (!hasNewUnreadAlert || typeof document === 'undefined' || document.visibilityState !== 'visible') {
      return;
    }

    playAlertChime();
  }, [unreadAlertIds]);

  const isAlertRead = useMemo(() => (id: string) => readIds.has(id), [readIds]);

  const markAlertRead = (id: string) => {
    setReadIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  };

  const markAlertUnread = (id: string) => {
    setReadIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const toggleAlertRead = (id: string) => {
    setReadIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const value = useMemo<ManagerAlertsContextValue>(
    () => ({
      operationalHeart: operationalHeartQuery.data ?? null,
      notifications,
      unresolvedCount,
      isLoading:
        tenantContextQuery.isLoading ||
        operationalCapabilitiesQuery.isLoading ||
        operationalHeartQuery.isLoading ||
        activeOrdersQuery.isLoading ||
        tableSessionsQuery.isLoading,
      isError:
        tenantContextQuery.isError ||
        operationalCapabilitiesQuery.isError ||
        operationalHeartQuery.isError ||
        activeOrdersQuery.isError ||
        tableSessionsQuery.isError,
      isAlertRead,
      toggleAlertRead,
      markAlertRead,
      markAlertUnread,
    }),
    [
      activeOrdersQuery.isError,
      activeOrdersQuery.isLoading,
      isAlertRead,
      markAlertRead,
      markAlertUnread,
      notifications,
      operationalCapabilitiesQuery.isError,
      operationalCapabilitiesQuery.isLoading,
      operationalHeartQuery.data,
      operationalHeartQuery.isError,
      operationalHeartQuery.isLoading,
      tableSessionsQuery.isError,
      tableSessionsQuery.isLoading,
      tenantContextQuery.isError,
      tenantContextQuery.isLoading,
      toggleAlertRead,
      unresolvedCount,
    ]
  );

  return <ManagerAlertsContext.Provider value={value}>{children}</ManagerAlertsContext.Provider>;
}

export function useManagerAlerts(): ManagerAlertsContextValue {
  const context = useContext(ManagerAlertsContext);
  if (!context) {
    throw new Error('useManagerAlerts must be used within ManagerAlertsProvider');
  }
  return context;
}
