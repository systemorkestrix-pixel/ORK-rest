import { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Archive,
  BadgeDollarSign,
  BarChart3,
  Bell,
  Boxes,
  ChefHat,
  ClipboardList,
  Cog,
  House,
  Layers3,
  LogOut,
  Menu,
  MoonStar,
  Plus,
  ReceiptText,
  Settings,
  SunMedium,
  Truck,
  Users,
  UtensilsCrossed,
  Wallet,
} from 'lucide-react';
import { useLocation, useNavigate, useOutlet, useSearchParams } from 'react-router-dom';

import { useManagerAlerts } from '@/app/navigation/ManagerAlertsContext';
import { useAuthStore } from '@/modules/auth/store';
import { ManagerAlertsPage } from '@/pages/manager/alerts/ManagerAlertsPage';
import { OperationalHeartPage } from '@/pages/intelligence/operational-heart/OperationalHeartPage';
import { api } from '@/shared/api/client';
import { useThemeMode } from '@/shared/hooks/useThemeMode';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { ActiveOrdersBoard } from './ActiveOrdersBoard';
import { ChannelBar, type ConsoleChannel } from './ChannelBar';
import { ChannelSectionBar, type ConsoleSection, type ConsoleSectionCard } from './ChannelCards';
import { ContentPanel } from './ContentPanel';

const OrdersPage = lazy(() => import('@/modules/operations/orders/OrdersPage').then((m) => ({ default: m.OrdersPage })));
const ManagerKitchenMonitorPage = lazy(() =>
  import('@/modules/kitchen/monitor/ManagerKitchenMonitorPage').then((m) => ({ default: m.ManagerKitchenMonitorPage }))
);
const ManagerKitchenSettingsPage = lazy(() =>
  import('@/modules/kitchen/settings/ManagerKitchenSettingsPage').then((m) => ({ default: m.ManagerKitchenSettingsPage }))
);
const DeliveryTeamPage = lazy(() =>
  import('@/modules/delivery/drivers/DeliveryTeamPage').then((m) => ({ default: m.DeliveryTeamPage }))
);
const DeliverySettingsPage = lazy(() =>
  import('@/modules/delivery/settings/DeliverySettingsPage').then((m) => ({ default: m.DeliverySettingsPage }))
);
const TablesPage = lazy(() => import('@/modules/operations/tables/TablesPage').then((m) => ({ default: m.TablesPage })));
const ProductsPage = lazy(() =>
  import('@/modules/system/catalog/products/ProductsPage').then((m) => ({ default: m.ProductsPage }))
);
const ExpensesPage = lazy(() =>
  import('@/modules/finance/expenses/ExpensesPage').then((m) => ({ default: m.ExpensesPage }))
);
const WarehousePage = lazy(() =>
  import('@/modules/warehouse/dashboard/WarehousePage').then((m) => ({ default: m.WarehousePage }))
);
const EmployeesPage = lazy(() =>
  import('@/modules/system/employees/EmployeesPage').then((m) => ({ default: m.EmployeesPage }))
);
const FinancialPage = lazy(() =>
  import('@/modules/finance/transactions/FinancialPage').then((m) => ({ default: m.FinancialPage }))
);
const ReportsPage = lazy(() =>
  import('@/modules/intelligence/reports/ReportsPage').then((m) => ({ default: m.ReportsPage }))
);

const SECTION_TO_CHANNEL: Record<ConsoleSection, ConsoleChannel> = {
  orders: 'operations',
  tables: 'operations',
  alerts: 'operations',
  menu: 'operations',
  kitchenMonitor: 'kitchen',
  kitchenSettings: 'kitchen',
  delivery: 'delivery',
  deliverySettings: 'delivery',
  warehouse: 'warehouse',
  warehouseOverview: 'warehouse',
  warehouseSuppliers: 'warehouse',
  warehouseItems: 'warehouse',
  warehouseBalances: 'warehouse',
  warehouseInbound: 'warehouse',
  warehouseOutbound: 'warehouse',
  warehouseCounts: 'warehouse',
  warehouseLedger: 'warehouse',
  financeOverview: 'finance',
  financeCashbox: 'finance',
  financeSettlements: 'finance',
  financeEntries: 'finance',
  financeClosures: 'finance',
  operationalHeart: 'intelligence',
  reports: 'intelligence',
  staff: 'system',
  settings: 'system',
};

const SECTION_CAPABILITIES: Partial<Record<ConsoleSection, string>> = {
  orders: 'manager.orders.view',
  tables: 'manager.tables.view',
  menu: 'manager.products.view',
  kitchenMonitor: 'manager.kitchen_monitor.view',
  kitchenSettings: 'manager.kitchen_monitor.view',
  delivery: 'manager.delivery.view',
  deliverySettings: 'manager.delivery.view',
  warehouse: 'manager.warehouse.view',
  warehouseOverview: 'manager.warehouse.view',
  warehouseSuppliers: 'manager.warehouse.view',
  warehouseItems: 'manager.warehouse.view',
  warehouseBalances: 'manager.warehouse.view',
  warehouseInbound: 'manager.warehouse.view',
  warehouseOutbound: 'manager.warehouse.view',
  warehouseCounts: 'manager.warehouse.view',
  warehouseLedger: 'manager.warehouse.view',
  staff: 'manager.users.view',
  financeOverview: 'manager.financial.view',
  financeExpenses: 'manager.expenses.view',
  financeCashbox: 'manager.financial.view',
  financeSettlements: 'manager.financial.view',
  financeEntries: 'manager.financial.view',
  financeClosures: 'manager.financial.view',
  reports: 'manager.reports.view',
  settings: 'manager.settings.view',
};

const LEGACY_WAREHOUSE_SECTIONS: ConsoleSection[] = ['warehouse', 'warehouseSuppliers', 'warehouseOutbound', 'warehouseLedger'];

const SECTION_PLAN_KEYS: Record<
  ConsoleSection,
  'operations' | 'menu' | 'kitchen' | 'delivery' | 'warehouse' | 'finance' | 'intelligence' | 'system'
> = {
  systemHub: 'system',
  orders: 'operations',
  tables: 'operations',
  alerts: 'operations',
  menu: 'menu',
  kitchenMonitor: 'kitchen',
  kitchenSettings: 'kitchen',
  delivery: 'delivery',
  deliverySettings: 'delivery',
  warehouse: 'warehouse',
  warehouseOverview: 'warehouse',
  warehouseSuppliers: 'warehouse',
  warehouseItems: 'warehouse',
  warehouseBalances: 'warehouse',
  warehouseInbound: 'warehouse',
  warehouseOutbound: 'warehouse',
  warehouseCounts: 'warehouse',
  warehouseLedger: 'warehouse',
  staff: 'system',
  financeOverview: 'finance',
  financeExpenses: 'finance',
  financeCashbox: 'finance',
  financeSettlements: 'finance',
  financeEntries: 'finance',
  financeClosures: 'finance',
  operationalHeart: 'intelligence',
  reports: 'intelligence',
  audit: 'system',
  settings: 'system',
  roles: 'system',
};

const SECTION_CARDS: ConsoleSectionCard[] = [
  { id: 'orders', channel: 'operations', label: '\u0627\u0644\u0637\u0644\u0628\u0627\u062a', subtitle: '\u0645\u062a\u0627\u0628\u0639\u0629 \u062f\u0648\u0631\u0629 \u0627\u0644\u0637\u0644\u0628\u0627\u062a \u0627\u0644\u064a\u0648\u0645\u064a\u0629.', icon: ClipboardList },
  { id: 'tables', channel: 'operations', label: '\u0627\u0644\u0637\u0627\u0648\u0644\u0627\u062a', subtitle: '\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u062c\u0644\u0633\u0627\u062a \u0648\u062d\u0627\u0644\u0629 \u0627\u0644\u0637\u0627\u0648\u0644\u0627\u062a.', icon: UtensilsCrossed },
  { id: 'menu', channel: 'operations', label: '\u0627\u0644\u0645\u0646\u064a\u0648', subtitle: '\u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0648\u0627\u0644\u0623\u0633\u0639\u0627\u0631.', icon: BadgeDollarSign },
  { id: 'kitchenMonitor', channel: 'kitchen', label: '\u0627\u0644\u0645\u0631\u0627\u0642\u0628\u0629', subtitle: '\u0645\u062a\u0627\u0628\u0639\u0629 \u0637\u0627\u0628\u0648\u0631 \u0627\u0644\u0645\u0637\u0628\u062e \u0648\u062d\u0627\u0644\u0627\u062a \u0627\u0644\u062a\u062d\u0636\u064a\u0631 \u0645\u0646 \u062f\u0627\u062e\u0644 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0637\u0639\u0645.', icon: ChefHat },
  { id: 'kitchenSettings', channel: 'kitchen', label: '\u0627\u0644\u0636\u0628\u0637', subtitle: '\u062a\u062c\u0647\u064a\u0632 \u0648\u0635\u0648\u0644 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0637\u0628\u062e \u0648\u0625\u0639\u0627\u062f\u0629 \u062a\u0648\u0644\u064a\u062f \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631.', icon: Settings },
  { id: 'delivery', channel: 'delivery', label: '\u0641\u0631\u064a\u0642 \u0627\u0644\u062a\u0648\u0635\u064a\u0644', subtitle: '\u0645\u062a\u0627\u0628\u0639\u0629 \u0627\u0644\u0633\u0627\u0626\u0642\u064a\u0646 \u0648\u062d\u0627\u0644\u0627\u062a \u0627\u0644\u062a\u0648\u0635\u064a\u0644.', icon: Truck },
  { id: 'deliverySettings', channel: 'delivery', label: '\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u062a\u0648\u0635\u064a\u0644', subtitle: '\u0636\u0628\u0637 \u0627\u0644\u0631\u0633\u0648\u0645 \u0648\u0627\u0644\u0633\u064a\u0627\u0633\u0627\u062a \u0627\u0644\u064a\u0648\u0645\u064a\u0629.', icon: Settings },
  { id: 'warehouseOverview', channel: 'warehouse', label: '\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639', subtitle: '\u0645\u0634\u0647\u062f \u0633\u0631\u064a\u0639 \u0644\u062d\u0627\u0644\u0629 \u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639 \u0648\u0623\u0648\u0644\u0648\u064a\u0627\u062a \u0627\u0644\u0645\u062a\u0627\u0628\u0639\u0629.', icon: Boxes },
  { id: 'warehouseInbound', channel: 'warehouse', label: '\u0627\u0644\u062a\u0648\u0631\u064a\u062f', subtitle: '\u0627\u0644\u0645\u0648\u0631\u062f\u0648\u0646 \u0648\u0627\u0633\u062a\u0644\u0627\u0645 \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0641\u064a \u0633\u064a\u0627\u0642 \u0648\u0627\u062d\u062f.', icon: Truck },
  { id: 'warehouseItems', channel: 'warehouse', label: '\u0627\u0644\u0623\u0635\u0646\u0627\u0641', subtitle: '\u062a\u0639\u0631\u064a\u0641 \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0645\u0639 \u0633\u062c\u0644 \u062d\u0631\u0643\u0629 \u0643\u0644 \u0635\u0646\u0641.', icon: Boxes },
  { id: 'warehouseBalances', channel: 'warehouse', label: '\u0627\u0644\u0645\u062e\u0632\u0648\u0646', subtitle: '\u0627\u0644\u0631\u0635\u064a\u062f \u0627\u0644\u062d\u0627\u0644\u064a \u0648\u0639\u0645\u0644\u064a\u0627\u062a \u0627\u0644\u0635\u0631\u0641 \u0641\u064a \u0645\u0643\u0627\u0646 \u0648\u0627\u062d\u062f.', icon: Archive },
  { id: 'warehouseCounts', channel: 'warehouse', label: '\u0627\u0644\u062c\u0631\u062f', subtitle: '\u0645\u0642\u0627\u0631\u0646\u0629 \u0627\u0644\u0643\u0645\u064a\u0627\u062a \u0627\u0644\u0641\u0639\u0644\u064a\u0629 \u0628\u0643\u0645\u064a\u0627\u062a \u0627\u0644\u0646\u0638\u0627\u0645.', icon: ClipboardList },
  { id: 'financeOverview', channel: 'finance', label: '\u0627\u0644\u0645\u0644\u062e\u0635', subtitle: '\u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u064a\u0648\u0645 \u0648\u0625\u063a\u0644\u0627\u0642 \u0627\u0644\u0648\u0631\u062f\u064a\u0629.', icon: Wallet },
  { id: 'financeExpenses', channel: 'finance', label: '\u0627\u0644\u0645\u0635\u0631\u0648\u0641\u0627\u062a', subtitle: '\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u0645\u0635\u0631\u0648\u0641\u0627\u062a \u0648\u0645\u0631\u0627\u062c\u0639\u0629 \u0633\u062c\u0644\u0647\u0627 \u0645\u0646 \u0645\u0643\u0627\u0646 \u0647\u0627 \u0627\u0644\u0645\u0627\u0644\u064a \u0627\u0644\u0623\u0635\u0644\u064a.', icon: ReceiptText },
  { id: 'financeCashbox', channel: 'finance', label: '\u0627\u0644\u0635\u0646\u062f\u0648\u0642', subtitle: '\u0627\u0644\u0646\u0642\u062f \u0627\u0644\u062f\u0627\u062e\u0644 \u0648\u0627\u0644\u062e\u0627\u0631\u062c.', icon: BadgeDollarSign },
  { id: 'financeSettlements', channel: 'finance', label: '\u062a\u0633\u0648\u064a\u0627\u062a \u0627\u0644\u062a\u0648\u0635\u064a\u0644', subtitle: '\u0645\u062a\u0627\u0628\u0639\u0629 \u0627\u0644\u0645\u0646\u062f\u0648\u0628\u064a\u0646 \u0648\u0627\u0644\u062a\u0648\u0631\u064a\u062f.', icon: Truck },
  { id: 'financeEntries', channel: 'finance', label: '\u0627\u0644\u0642\u064a\u0648\u062f \u0627\u0644\u0645\u062d\u0627\u0633\u0628\u064a\u0629', subtitle: '\u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u0642\u064a\u0648\u062f \u0648\u0627\u0644\u0645\u0631\u0627\u062c\u0639.', icon: ReceiptText },
  { id: 'financeClosures', channel: 'finance', label: '\u0633\u062c\u0644 \u0627\u0644\u0625\u063a\u0644\u0627\u0642\u0627\u062a', subtitle: '\u0623\u0631\u0634\u064a\u0641 \u0627\u0644\u0648\u0631\u062f\u064a\u0627\u062a \u0627\u0644\u0633\u0627\u0628\u0642\u0629.', icon: Archive },
  { id: 'operationalHeart', channel: 'intelligence', label: '\u062d\u0627\u0644\u0629 \u0627\u0644\u0646\u0638\u0627\u0645', subtitle: '\u0645\u0624\u0634\u0631\u0627\u062a \u0627\u0644\u0645\u062a\u0627\u0628\u0639\u0629 \u0627\u0644\u0645\u0628\u0627\u0634\u0631\u0629 \u0644\u0644\u0646\u0638\u0627\u0645.', icon: Activity },
  { id: 'reports', channel: 'intelligence', label: '\u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631', subtitle: '\u0645\u0631\u0627\u062c\u0639\u0629 \u0627\u0644\u0623\u062f\u0627\u0621 \u0648\u0627\u0644\u0645\u0644\u062e\u0635\u0627\u062a.', icon: BarChart3 },
  { id: 'staff', channel: 'system', label: '\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u0648\u0638\u0641\u064a\u0646', subtitle: '\u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a \u0627\u0644\u062a\u0634\u063a\u064a\u0644\u064a\u0629 \u0627\u0644\u062d\u0627\u0644\u064a\u0629 \u0648\u0645\u0633\u0627\u0631 \u0627\u0644\u062a\u0648\u0633\u0639 \u0627\u0644\u0645\u0647\u0646\u064a \u0644\u0644\u0645\u0648\u0638\u0641\u064a\u0646.', icon: Users },
];

const OPERATIONAL_HEART_QUERY_KEY = ['console-operational-heart'] as const;

const HEADER_ICON_BUTTON_CLASS =
  'inline-flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.16)] transition hover:border-[#b98757] hover:bg-[var(--surface-card-hover)] hover:text-[var(--text-primary)]';
const HEADER_LOGOUT_BUTTON_CLASS =
  'inline-flex h-14 w-14 items-center justify-center rounded-xl border border-rose-300 bg-rose-100/85 text-rose-900 shadow-[inset_0_1px_0_rgba(255,255,255,0.16)] transition hover:border-rose-400 hover:bg-rose-100 hover:text-rose-950';
const MOBILE_BOTTOM_NAV_BUTTON_CLASS =
  'inline-flex min-h-[56px] flex-1 flex-col items-center justify-center gap-1 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] px-2 py-2 text-[11px] font-black text-[var(--text-secondary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] transition hover:border-[#b98757] hover:bg-[var(--surface-card-hover)] hover:text-[var(--text-primary)]';
const MOBILE_BOTTOM_NAV_ACTIVE_CLASS =
  'border-[#b98757] bg-[var(--surface-card-hover)] text-[var(--text-primary)] shadow-[0_10px_18px_rgba(0,0,0,0.18)]';

function resolveHeaderAlertTone(notifications: ReturnType<typeof useManagerAlerts>['notifications']) {
  const hasAnyActions = notifications.some((domain) => domain.actions.length > 0);
  const hasCritical = notifications.some((domain) => domain.unreadCount > 0 && domain.severity === 'critical');
  const hasWarning = notifications.some((domain) => domain.unreadCount > 0 && domain.severity === 'warning');
  const hasInfo = notifications.some((domain) => domain.unreadCount > 0 && domain.severity === 'info');

  if (hasCritical) {
    return {
      iconButton:
        'border-rose-300 bg-rose-100/90 text-rose-800 hover:border-rose-400 hover:bg-rose-100 hover:text-rose-900',
      tile: 'border-rose-200 bg-rose-50 text-rose-800',
      badge: 'border-rose-700 bg-rose-700 text-rose-50',
    };
  }
  if (hasWarning) {
    return {
      iconButton:
        'border-amber-300 bg-amber-100/90 text-amber-800 hover:border-amber-400 hover:bg-amber-100 hover:text-amber-900',
      tile: 'border-amber-200 bg-amber-50 text-amber-800',
      badge: 'border-amber-700 bg-amber-700 text-amber-50',
    };
  }
  if (hasInfo) {
    return {
      iconButton:
        'border-sky-300 bg-sky-100/90 text-sky-800 hover:border-sky-400 hover:bg-sky-100 hover:text-sky-900',
      tile: 'border-sky-200 bg-sky-50 text-sky-800',
      badge: 'border-sky-700 bg-sky-700 text-sky-50',
    };
  }
  if (hasAnyActions) {
    return {
      iconButton:
        'border-emerald-300 bg-emerald-100/90 text-emerald-800 hover:border-emerald-400 hover:bg-emerald-100 hover:text-emerald-900',
      tile: 'border-emerald-200 bg-emerald-50 text-emerald-800',
      badge: 'border-emerald-700 bg-emerald-700 text-emerald-50',
    };
  }
  return {
    iconButton:
      'border-emerald-200 bg-emerald-50/80 text-emerald-700 hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800',
    tile: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    badge: 'border-emerald-700 bg-emerald-700 text-emerald-50',
  };
}

function parseChannel(value: string | null): ConsoleChannel | null {
  if (
    value === 'operations' ||
    value === 'kitchen' ||
    value === 'delivery' ||
    value === 'warehouse' ||
    value === 'finance' ||
    value === 'intelligence' ||
    value === 'system'
  ) {
    return value;
  }
  return null;
}

function parseSection(value: string | null): ConsoleSection | null {
  if (!value) {
    return null;
  }
  return value === 'alerts' ||
    LEGACY_WAREHOUSE_SECTIONS.includes(value as ConsoleSection) ||
    SECTION_CARDS.some((card) => card.id === value)
    ? (value as ConsoleSection)
    : null;
}

function resolveStateFromSearch(
  params: URLSearchParams,
  allowedSections: Set<ConsoleSection>
): { channel: ConsoleChannel | null; section: ConsoleSection | null } {
  const requestedSection = parseSection(params.get('section'));
  if (requestedSection && allowedSections.has(requestedSection)) {
    const requestedChannel = parseChannel(params.get('channel'));
    return {
      channel: requestedChannel ?? SECTION_TO_CHANNEL[requestedSection],
      section: requestedSection,
    };
  }

  return {
    channel: parseChannel(params.get('channel')),
    section: null,
  };
}

function resolveStateFromPath(pathname: string): { channel: ConsoleChannel | null; section: ConsoleSection | null } | null {
  if (pathname.startsWith('/console/plans')) {
    return { channel: null, section: null };
  }
  if (pathname === '/console/system') {
    return { channel: 'system', section: 'staff' };
  }
  if (pathname.startsWith('/console/system/settings')) {
    return { channel: null, section: null };
  }
  if (pathname.startsWith('/console/system/users')) {
    return { channel: 'system', section: 'staff' };
  }
  if (pathname.startsWith('/console/operations/orders')) {
    return { channel: 'operations', section: 'orders' };
  }
  if (pathname.startsWith('/console/operations/tables')) {
    return { channel: 'operations', section: 'tables' };
  }
  if (pathname.startsWith('/console/alerts')) {
    return { channel: null, section: null };
  }
  if (pathname.startsWith('/console/operations/menu')) {
    return { channel: 'operations', section: 'menu' };
  }
  if (pathname.startsWith('/console/kitchen/monitor')) {
    return { channel: 'kitchen', section: 'kitchenMonitor' };
  }
  if (pathname.startsWith('/console/kitchen/settings')) {
    return { channel: 'kitchen', section: 'kitchenSettings' };
  }
  if (pathname.startsWith('/console/restaurant/menu')) {
    return { channel: 'operations', section: 'menu' };
  }
  if (pathname.startsWith('/console/finance/expenses')) {
    return { channel: 'finance', section: 'financeExpenses' };
  }
  if (pathname.startsWith('/console/delivery/drivers')) {
    return { channel: 'delivery', section: 'delivery' };
  }
  if (pathname.startsWith('/console/delivery/settings')) {
    return { channel: 'delivery', section: 'deliverySettings' };
  }
  if (pathname.startsWith('/console/intelligence/operational-heart')) {
    return { channel: 'intelligence', section: 'operationalHeart' };
  }
  if (pathname.startsWith('/console/intelligence/reports')) {
    return { channel: 'intelligence', section: 'reports' };
  }
  return null;
}

function buildConsoleStatePath(
  channel: ConsoleChannel | null,
  section: ConsoleSection | null,
  extras?: Partial<Record<string, string>>
): string {
  const params = new URLSearchParams();
  if (channel) {
    params.set('channel', channel);
  }
  if (section) {
    params.set('section', section);
  }
  if (section !== 'orders') {
    params.delete('status');
    params.delete('order_type');
    params.delete('new');
  }
  if (extras) {
    for (const [key, value] of Object.entries(extras)) {
      if (!value) {
        continue;
      }
      params.set(key, value);
    }
  }
  return params.size > 0 ? `/console?${params.toString()}` : '/console';
}

function resolveDirectPathForSection(section: ConsoleSection): string | null {
  switch (section) {
    case 'orders':
      return '/console/operations/orders';
    case 'tables':
      return '/console/operations/tables';
    case 'alerts':
      return '/console/alerts';
    case 'menu':
      return '/console/operations/menu';
    case 'kitchenMonitor':
      return '/console/kitchen/monitor';
    case 'kitchenSettings':
      return '/console/kitchen/settings';
    case 'delivery':
      return '/console/delivery/drivers';
    case 'deliverySettings':
      return '/console/delivery/settings';
    case 'staff':
      return '/console/system/users';
    case 'financeExpenses':
      return '/console/finance/expenses';
    case 'operationalHeart':
      return '/console/intelligence/operational-heart';
    case 'reports':
      return '/console/intelligence/reports';
    default:
      return null;
  }
}

function SectionLoading() {
  return (
    <div className="rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4 text-sm font-semibold text-[var(--text-secondary)]">
      جارٍ تحميل القسم...
    </div>
  );
}

function formatHeaderCounter(value: number): string {
  return value > 99 ? '99+' : String(value);
}

export function ConsolePage() {
  const user = useAuthStore((state) => state.user);
  const role = useAuthStore((state) => state.role);
  const logout = useAuthStore((state) => state.logout);
  const location = useLocation();
  const navigate = useNavigate();
  const routeOutlet = useOutlet();
  const [searchParams, setSearchParams] = useSearchParams();
  const { notifications, unresolvedCount } = useManagerAlerts();
  const { isDark, toggleTheme } = useThemeMode();
  const themeButtonLabel = isDark ? 'تفعيل الوضع النهاري' : 'تفعيل الوضع الليلي';

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context'],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });
  const sectionModes = tenantContextQuery.data?.section_modes ?? {};
  const channelModes = tenantContextQuery.data?.channel_modes ?? {};

  const availableCards = useMemo(() => {
    const isSectionVisible = (section: ConsoleSection) => (sectionModes[section] ?? 'core') === 'core';
    if (!Array.isArray(user?.permissions_effective)) {
      return SECTION_CARDS.filter((card) => isSectionVisible(card.id));
    }
    const granted = new Set(user.permissions_effective);
    return SECTION_CARDS.filter((card) => {
      const capability = SECTION_CAPABILITIES[card.id];
      return isSectionVisible(card.id) && (!capability || granted.has(capability));
    });
  }, [role, sectionModes, user?.permissions_effective]);

  const hasWarehouseSections = useMemo(() => availableCards.some((card) => card.channel === 'warehouse'), [availableCards]);
  const allowedSections = useMemo(
    () =>
      new Set<ConsoleSection>([
        'alerts',
        ...(hasWarehouseSections ? LEGACY_WAREHOUSE_SECTIONS : []),
        ...availableCards.map((card) => card.id),
      ]),
    [availableCards, hasWarehouseSections]
  );
  const searchStateKey = searchParams.toString();

  const [activeChannel, setActiveChannel] = useState<ConsoleChannel | null>(() => {
    const state = resolveStateFromSearch(searchParams, allowedSections);
    return state.channel;
  });
  const [activeSection, setActiveSection] = useState<ConsoleSection | null>(() => {
    const state = resolveStateFromSearch(searchParams, allowedSections);
    return state.section;
  });
  const [lastSectionByChannel, setLastSectionByChannel] = useState<Partial<Record<ConsoleChannel, ConsoleSection>>>({});
  const [homeOrdersCreateToken, setHomeOrdersCreateToken] = useState(0);
  const [showNavigationBars, setShowNavigationBars] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    return window.localStorage.getItem('console-navigation-bars') !== 'hidden';
  });

  useEffect(() => {
    if (location.pathname !== '/console') {
      const directState = resolveStateFromPath(location.pathname);
      if (directState) {
        setActiveChannel((current) => (current !== directState.channel ? directState.channel : current));
        setActiveSection((current) => (current !== directState.section ? directState.section : current));
      }
      return;
    }

    const state = resolveStateFromSearch(searchParams, allowedSections);

    setActiveChannel((current) => (current !== state.channel ? state.channel : current));
    setActiveSection((current) => (current !== state.section ? state.section : current));
  }, [allowedSections, location.pathname, searchStateKey]);

  useEffect(() => {
    if (!activeChannel || !activeSection || SECTION_TO_CHANNEL[activeSection] !== activeChannel) {
      return;
    }
    setLastSectionByChannel((current) =>
      current[activeChannel] === activeSection ? current : { ...current, [activeChannel]: activeSection }
    );
  }, [activeChannel, activeSection]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem('console-navigation-bars', showNavigationBars ? 'shown' : 'hidden');
  }, [showNavigationBars]);

  const syncSearchState = (
    channel: ConsoleChannel | null,
    section: ConsoleSection | null,
    extras?: Partial<Record<string, string>>
  ) => {
    const next = new URLSearchParams(searchParams);
    if (channel) {
      next.set('channel', channel);
    } else {
      next.delete('channel');
    }
    if (section) {
      next.set('section', section);
    } else {
      next.delete('section');
    }
    if (section !== 'orders') {
      next.delete('status');
      next.delete('order_type');
      next.delete('new');
    }
    if (extras) {
      for (const [key, value] of Object.entries(extras)) {
        if (!value) {
          next.delete(key);
        } else {
          next.set(key, value);
        }
      }
    }
    setSearchParams(next, { replace: true });
  };

  const goToConsoleHome = () => {
    setActiveChannel(null);
    setActiveSection(null);
    navigate('/console');
  };

  const operationalHeartQuery = useQuery({
    queryKey: OPERATIONAL_HEART_QUERY_KEY,
    queryFn: () => api.managerDashboardOperationalHeart(role ?? 'manager'),
    enabled: role === 'manager' && tenantContextQuery.isSuccess && (channelModes.intelligence ?? 'disabled') === 'core',
    refetchInterval: adaptiveRefetchInterval(5000, { minimumMs: 5000 }),
  });

  const alertTone = useMemo(() => resolveHeaderAlertTone(notifications), [notifications]);

  const cardMetrics = useMemo(() => {
    const kpis = operationalHeartQuery.data?.kpis;
    return {
      orders: kpis?.active_orders ?? 0,
      kitchen: kpis?.kitchen_active_orders ?? 0,
      delivery: kpis?.delivery_active_orders ?? 0,
    };
  }, [operationalHeartQuery.data?.kpis]);

  const cardsWithMetrics = useMemo(
    () =>
      availableCards.map((card) => {
        if (card.id === 'orders') {
          return { ...card, metric: cardMetrics.orders };
        }
        if (card.id === 'kitchenMonitor') {
          return { ...card, metric: cardMetrics.kitchen };
        }
        if (card.id === 'delivery') {
          return { ...card, metric: cardMetrics.delivery };
        }
        return card;
      }),
    [availableCards, cardMetrics.delivery, cardMetrics.kitchen, cardMetrics.orders]
  );

  const visibleChannels = useMemo(
    () =>
      (['operations', 'kitchen', 'delivery', 'warehouse', 'finance', 'intelligence'] as const).filter(
        (channel) => (channelModes[channel] ?? 'core') === 'core'
      ),
    [channelModes]
  );
  const singleCoreChannel = visibleChannels.length === 1 ? visibleChannels[0] : null;
  const effectiveChannel = activeChannel ?? singleCoreChannel;
  const channelSections = useMemo(
    () => (effectiveChannel ? cardsWithMetrics.filter((card) => card.channel === effectiveChannel) : []),
    [cardsWithMetrics, effectiveChannel]
  );
  const systemSections = useMemo(() => cardsWithMetrics.filter((card) => card.channel === 'system'), [cardsWithMetrics]);
  const hasSystemAccess = systemSections.length > 0;
  const grantedPermissions = Array.isArray(user?.permissions_effective) ? new Set(user.permissions_effective) : null;
  const hasSettingsAccess = !grantedPermissions || grantedPermissions.has('manager.settings.view');
  const isDirectConsoleRoute = location.pathname !== '/console';
  const showSectionBar =
    Boolean(effectiveChannel) && !location.pathname.startsWith('/console/system') && !location.pathname.startsWith('/console/plans');
  const showChannelBar = showNavigationBars && visibleChannels.length > 1;
  const activeSectionCard = activeSection ? cardsWithMetrics.find((card) => card.id === activeSection) ?? null : null;
  const currentChannelLabel = effectiveChannel
    ? {
        operations: 'العمليات',
        kitchen: 'المطبخ',
        delivery: 'التوصيل',
        warehouse: 'المستودع',
        finance: 'المالية',
        intelligence: 'التحليلات',
        system: 'النظام',
      }[effectiveChannel]
    : null;
  const mobileHeaderTitle = activeSectionCard?.label ?? (isDirectConsoleRoute ? 'لوحة التحكم' : 'الواجهة الرئيسية');
  const mobileHeaderSubtitle = activeSectionCard?.subtitle ?? (currentChannelLabel ? `قناة ${currentChannelLabel}` : 'تنقل واضح وسريع بين أقسام النظام');
  const mobileMainPaddingClass = showNavigationBars
    ? showSectionBar
      ? showChannelBar
        ? 'pb-[15.5rem]'
        : 'pb-[11.5rem]'
      : showChannelBar
        ? 'pb-[11.5rem]'
        : 'pb-[7.5rem]'
    : 'pb-[7.5rem]';
  const isHomeActive = !isDirectConsoleRoute && !activeSection;
  const isAlertsActive = location.pathname.startsWith('/console/alerts');
  const isSystemActive = location.pathname.startsWith('/console/system');
  const isPlansActive = location.pathname.startsWith('/console/plans');

  useEffect(() => {
    if (tenantContextQuery.isLoading) {
      return;
    }

    if (activeSection && !allowedSections.has(activeSection)) {
      const fallbackSection = allowedSections.has('orders')
        ? 'orders'
        : availableCards.find((card) => card.channel === 'operations')?.id ?? availableCards[0]?.id ?? null;
      if (fallbackSection) {
        const fallbackChannel = SECTION_TO_CHANNEL[fallbackSection];
        setActiveChannel(fallbackChannel);
        setActiveSection(fallbackSection);
        const directPath = resolveDirectPathForSection(fallbackSection);
        navigate(directPath ?? buildConsoleStatePath(fallbackChannel, fallbackSection), { replace: true });
      } else {
        setActiveChannel(null);
        setActiveSection(null);
        navigate('/console', { replace: true });
      }
      return;
    }

    if (activeChannel && activeChannel !== 'system' && !visibleChannels.includes(activeChannel)) {
      setActiveChannel(null);
      if (location.pathname === '/console') {
        syncSearchState(null, null);
      } else {
        navigate('/console', { replace: true });
      }
    }
  }, [
    activeChannel,
    activeSection,
    allowedSections,
    availableCards,
    location.pathname,
    navigate,
    tenantContextQuery.isLoading,
    visibleChannels,
  ]);

  const selectChannel = (channel: ConsoleChannel) => {
    if (!visibleChannels.includes(channel)) {
      return;
    }
    setActiveChannel(channel);
    setActiveSection(null);
    if (location.pathname === '/console') {
      syncSearchState(channel, null);
    }
  };

  const openSection = (section: ConsoleSection) => {
    const channel = SECTION_TO_CHANNEL[section];
    setActiveChannel(channel);
    setActiveSection(section);
    const directPath = resolveDirectPathForSection(section);
    if (directPath) {
      navigate(directPath);
      return;
    }
    navigate(buildConsoleStatePath(channel, section));
  };

  const openOrdersCreation = () => {
    setHomeOrdersCreateToken((current) => current + 1);
  };

  const openAlertsSection = () => {
    setActiveChannel(null);
    setActiveSection(null);
    navigate('/console/alerts');
  };

  const openSystemHubSection = () => {
    navigate('/console/system/settings');
  };

  const openSystemCenterSection = () => {
    setActiveChannel('system');
    setActiveSection('staff');
    navigate('/console/system');
  };

  const openPlansSection = () => {
    setActiveChannel(null);
    setActiveSection(null);
    navigate('/console/plans');
  };

  const openMobileSystemTarget = () => {
    if (hasSettingsAccess) {
      openSystemHubSection();
      return;
    }
    if (hasSystemAccess) {
      openSystemCenterSection();
    }
  };

  useEffect(() => {
    if (searchParams.get('section') === 'settings') {
      navigate('/console/system/settings', { replace: true });
    }
  }, [navigate, searchParams]);

  useEffect(() => {
    if (activeSection === 'settings') {
      navigate('/console/system/settings', { replace: true });
    }
  }, [activeSection, navigate]);

  const renderFinanceSection = () => {
    switch (activeSection) {
      case 'financeOverview':
        return <FinancialPage initialTab="overview" />;
      case 'financeExpenses':
        return <ExpensesPage embedded />;
      case 'financeCashbox':
        return <FinancialPage initialTab="cashbox" />;
      case 'financeSettlements':
        return <FinancialPage initialTab="settlements" />;
      case 'financeEntries':
        return <FinancialPage initialTab="entries" />;
      case 'financeClosures':
        return <FinancialPage initialTab="closures" />;
      default:
        return null;
    }
  };

  const renderWarehouseSection = () => {
    switch (activeSection) {
      case 'warehouse':
      case 'warehouseOverview':
        return <WarehousePage initialView="overview" />;
      case 'warehouseSuppliers':
      case 'warehouseInbound':
        return <WarehousePage initialView="supply" />;
      case 'warehouseItems':
      case 'warehouseLedger':
        return <WarehousePage initialView="items" />;
      case 'warehouseBalances':
      case 'warehouseOutbound':
        return <WarehousePage initialView="stock" />;
      case 'warehouseCounts':
        return <WarehousePage initialView="counts" />;
      default:
        return null;
    }
  };

  const renderSection = () => {
    switch (activeSection) {
      case 'orders':
        return <OrdersPage showCreateButton={false} />;
      case 'alerts':
        return <ManagerAlertsPage />;
      case 'delivery':
        return <DeliveryTeamPage />;
      case 'deliverySettings':
        return <DeliverySettingsPage />;
      case 'tables':
        return <TablesPage />;
      case 'menu':
        return <ProductsPage />;
      case 'kitchenMonitor':
        return <ManagerKitchenMonitorPage />;
      case 'kitchenSettings':
        return <ManagerKitchenSettingsPage />;
      case 'warehouse':
      case 'warehouseOverview':
      case 'warehouseSuppliers':
      case 'warehouseItems':
      case 'warehouseBalances':
      case 'warehouseInbound':
      case 'warehouseOutbound':
      case 'warehouseCounts':
      case 'warehouseLedger':
        return renderWarehouseSection();
      case 'staff':
        return <EmployeesPage />;
      case 'financeOverview':
      case 'financeExpenses':
      case 'financeCashbox':
      case 'financeSettlements':
      case 'financeEntries':
      case 'financeClosures':
        return renderFinanceSection();
      case 'operationalHeart':
        return <OperationalHeartPage />;
      case 'reports':
        return <ReportsPage />;
      default:
        return null;
    }
  };

  return (
    <div className="console-theme h-screen overflow-hidden bg-[var(--console-page-bg)] text-[var(--text-primary)]">
      <div className="flex h-full flex-col">
        <header className="console-header-layer border-b border-[var(--console-border)] px-3 py-2 tablet:px-6 tablet:py-3">
          <div className="tablet:hidden">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] font-black text-[var(--text-muted)]">
                  {currentChannelLabel ? `قناة ${currentChannelLabel}` : 'لوحة النظام'}
                </p>
                <h1 className="truncate text-lg font-black text-[var(--text-primary)]">{mobileHeaderTitle}</h1>
                <p className="truncate text-xs font-semibold text-[var(--text-muted)]">{mobileHeaderSubtitle}</p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={openPlansSection}
                  className={`${HEADER_ICON_BUTTON_CLASS} ${
                    isPlansActive ? 'border-[#b98757] bg-[var(--surface-card-hover)] text-[var(--text-primary)]' : ''
                  }`}
                  aria-label="الإضافات"
                  title="الإضافات"
                >
                  <Layers3 className="h-5 w-5" />
                  <span className="text-[10px] font-bold leading-none">الإضافات</span>
                </button>
                <button
                  type="button"
                  onClick={toggleTheme}
                  className={HEADER_ICON_BUTTON_CLASS}
                  aria-label={themeButtonLabel}
                  title={themeButtonLabel}
                >
                  {isDark ? <SunMedium className="h-5 w-5" /> : <MoonStar className="h-5 w-5" />}
                  <span className="text-[10px] font-bold leading-none">{isDark ? 'نهاري' : 'ليلي'}</span>
                </button>
              </div>
            </div>
          </div>

          <div className="hidden tablet:grid tablet:grid-cols-[auto_minmax(0,1fr)_auto] tablet:items-center tablet:gap-3">
            <button
              type="button"
              onClick={logout}
              className={`${HEADER_LOGOUT_BUTTON_CLASS} !h-12 !w-12`}
              aria-label="تسجيل الخروج"
              title="تسجيل الخروج"
            >
              <LogOut className="h-4 w-4" />
            </button>

            <div />

            <div className="flex items-center justify-end gap-2">
              {hasSettingsAccess ? (
                <button
                  type="button"
                  onClick={openSystemHubSection}
                  className="btn-secondary ui-size-sm !h-12 !w-12 !px-0"
                  aria-label="إعدادات النظام"
                  title="إعدادات النظام"
                >
                  <Cog className="h-5 w-5" />
                </button>
              ) : null}

              <button
                type="button"
                onClick={openPlansSection}
                className={`btn-secondary ui-size-sm !h-12 !w-12 !px-0 ${
                  isPlansActive ? 'border-[#b98757] bg-[var(--surface-card-hover)] text-[var(--text-primary)]' : ''
                }`}
                aria-label="الإضافات"
                title="الإضافات"
              >
                <Layers3 className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={toggleTheme}
                className="btn-secondary ui-size-sm !h-12 !w-12 !px-0"
                aria-label={themeButtonLabel}
                title={themeButtonLabel}
              >
                {isDark ? <SunMedium className="h-5 w-5" /> : <MoonStar className="h-5 w-5" />}
              </button>

              {hasSystemAccess ? (
                <button
                  type="button"
                  onClick={openSystemCenterSection}
                  className="btn-secondary ui-size-sm !h-12 !w-12 !px-0"
                  aria-label="مركز النظام"
                  title="مركز النظام"
                >
                  <Users className="h-5 w-5" />
                </button>
              ) : null}

              <button
                type="button"
                onClick={() => setShowNavigationBars((current) => !current)}
                className="btn-secondary ui-size-sm !h-12 !w-12 !px-0"
                aria-label={showNavigationBars ? 'إخفاء شريط التنقل' : 'إظهار شريط التنقل'}
                title={showNavigationBars ? 'إخفاء شريط التنقل' : 'إظهار شريط التنقل'}
              >
                <Menu className="h-5 w-5" />
              </button>

              <button
                type="button"
                onClick={openAlertsSection}
                className={`btn-secondary ui-size-sm !h-12 !w-12 !px-0 relative ${alertTone.iconButton}`}
                aria-label={`التنبيهات: ${unresolvedCount}`}
                title={`التنبيهات: ${unresolvedCount}`}
              >
                <Bell className="h-5 w-5" />
                <span className={`absolute -right-1 -top-1 inline-flex min-w-5 items-center justify-center rounded-full border px-1 text-[10px] font-black leading-4 ${alertTone.badge}`}>
                  {formatHeaderCounter(unresolvedCount)}
                </span>
              </button>

              <button
                type="button"
                onClick={goToConsoleHome}
                className="btn-secondary ui-size-sm !h-12 !w-12 !px-0"
                aria-label="الواجهة الرئيسية"
                title="الواجهة الرئيسية"
              >
                <House className="h-5 w-5" />
              </button>
            </div>
          </div>
        </header>

        <div className="hidden tablet:block">
          {showChannelBar ? (
            <ChannelBar activeChannel={activeChannel} channels={visibleChannels} onSelectChannel={selectChannel} />
          ) : null}
          {showNavigationBars && showSectionBar ? (
            <ChannelSectionBar
              channel={effectiveChannel}
              sections={channelSections}
              activeSection={activeSection}
              onOpenSection={openSection}
            />
          ) : null}
        </div>

        <main className={`console-main-layer min-h-0 flex-1 overflow-hidden p-3 md:p-4 tablet:pb-4 ${mobileMainPaddingClass}`}>
          {isDirectConsoleRoute && routeOutlet ? (
            <ContentPanel>{routeOutlet}</ContentPanel>
          ) : activeSection ? (
            <ContentPanel>
              <Suspense fallback={<SectionLoading />}>{renderSection()}</Suspense>
            </ContentPanel>
          ) : (
            <section className="console-board-layer console-panel-surface console-scrollbar manager-section-shell h-full min-h-0 overflow-auto rounded-2xl border p-4 md:p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-black text-[var(--text-primary)]">لوحة الطلبات النشطة</p>
                  <p className="text-xs font-semibold text-[var(--text-muted)]">متابعة دورة الطلبات لحظيًا داخل قناة العمليات.</p>
                </div>
                {allowedSections.has('orders') ? (
                  <button
                    type="button"
                    onClick={openOrdersCreation}
                    className="btn-primary ui-size-sm inline-flex items-center gap-2"
                  >
                    <Plus className="h-4 w-4" />
                    <span>إنشاء طلب جديد</span>
                  </button>
                ) : null}
              </div>

              <ActiveOrdersBoard createRequestToken={homeOrdersCreateToken} />
            </section>
          )}
        </main>

        <div className="pointer-events-none fixed inset-x-0 bottom-0 z-40 tablet:hidden">
          <div className="pointer-events-auto px-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)]">
            {showNavigationBars && showSectionBar ? (
              <div className="mb-2 overflow-hidden rounded-[1.75rem] border border-[var(--console-border)] bg-[var(--surface-card-soft)]/95 shadow-[0_-12px_30px_rgba(0,0,0,0.22)] backdrop-blur">
                <ChannelSectionBar
                  channel={effectiveChannel}
                  sections={channelSections}
                  activeSection={activeSection}
                  onOpenSection={openSection}
                />
              </div>
            ) : null}

            {showChannelBar ? (
              <div className="mb-2 overflow-hidden rounded-[1.75rem] border border-[var(--console-border)] bg-[var(--surface-card-soft)]/95 shadow-[0_-12px_30px_rgba(0,0,0,0.22)] backdrop-blur">
                <ChannelBar activeChannel={activeChannel} channels={visibleChannels} onSelectChannel={selectChannel} />
              </div>
            ) : null}

            <div className="rounded-[1.75rem] border border-[var(--console-border)] bg-[var(--surface-card-soft)]/95 p-2 shadow-[0_-12px_30px_rgba(0,0,0,0.22)] backdrop-blur">
              <div className="flex items-stretch gap-2">
                <button
                  type="button"
                  onClick={openAlertsSection}
                  className={`${MOBILE_BOTTOM_NAV_BUTTON_CLASS} ${isAlertsActive ? MOBILE_BOTTOM_NAV_ACTIVE_CLASS : ''} relative`}
                  aria-label={`التنبيهات: ${unresolvedCount}`}
                  title={`التنبيهات: ${unresolvedCount}`}
                >
                  <span className="relative flex h-5 w-5 items-center justify-center">
                    <Bell className="h-5 w-5" />
                    <span className={`absolute -right-2 -top-2 inline-flex min-w-5 items-center justify-center rounded-full border px-1 text-[10px] font-black leading-4 ${alertTone.badge}`}>
                      {formatHeaderCounter(unresolvedCount)}
                    </span>
                  </span>
                  <span>التنبيهات</span>
                </button>

                <button
                  type="button"
                  onClick={() => setShowNavigationBars((current) => !current)}
                  className={`${MOBILE_BOTTOM_NAV_BUTTON_CLASS} ${showNavigationBars ? MOBILE_BOTTOM_NAV_ACTIVE_CLASS : ''}`}
                  aria-label={showNavigationBars ? 'إخفاء القنوات' : 'إظهار القنوات'}
                  title={showNavigationBars ? 'إخفاء القنوات' : 'إظهار القنوات'}
                >
                  <Menu className="h-5 w-5" />
                  <span>{showNavigationBars ? 'إخفاء' : 'القنوات'}</span>
                </button>

                <button
                  type="button"
                  onClick={goToConsoleHome}
                  className={`${MOBILE_BOTTOM_NAV_BUTTON_CLASS} ${isHomeActive ? MOBILE_BOTTOM_NAV_ACTIVE_CLASS : ''}`}
                  aria-label="الواجهة الرئيسية"
                  title="الواجهة الرئيسية"
                >
                  <House className="h-5 w-5" />
                  <span>الرئيسية</span>
                </button>

                {(hasSettingsAccess || hasSystemAccess) ? (
                  <button
                    type="button"
                    onClick={openMobileSystemTarget}
                    className={`${MOBILE_BOTTOM_NAV_BUTTON_CLASS} ${isSystemActive ? MOBILE_BOTTOM_NAV_ACTIVE_CLASS : ''}`}
                    aria-label={hasSettingsAccess ? 'إعدادات النظام' : 'مركز النظام'}
                    title={hasSettingsAccess ? 'إعدادات النظام' : 'مركز النظام'}
                  >
                    {hasSettingsAccess ? <Cog className="h-5 w-5" /> : <Users className="h-5 w-5" />}
                    <span>{hasSettingsAccess ? 'الإعدادات' : 'النظام'}</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={toggleTheme}
                    className={MOBILE_BOTTOM_NAV_BUTTON_CLASS}
                    aria-label={themeButtonLabel}
                    title={themeButtonLabel}
                  >
                    {isDark ? <SunMedium className="h-5 w-5" /> : <MoonStar className="h-5 w-5" />}
                    <span>{isDark ? 'نهاري' : 'ليلي'}</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={logout}
                  className={`${MOBILE_BOTTOM_NAV_BUTTON_CLASS} border-rose-300 bg-rose-100/85 text-rose-900 hover:border-rose-400 hover:bg-rose-100 hover:text-rose-950`}
                  aria-label="تسجيل الخروج"
                  title="تسجيل الخروج"
                >
                  <LogOut className="h-5 w-5" />
                  <span>الخروج</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
