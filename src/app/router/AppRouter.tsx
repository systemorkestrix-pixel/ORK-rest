import { Suspense, lazy, useEffect, type ReactElement } from 'react';
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';

import { useAuthStore } from '@/modules/auth/store';
import { useMasterAuthStore } from '@/modules/master/auth/masterAuthStore';
import type { UserRole } from '@/shared/api/types';
import { ManagerAlertsProvider } from '../navigation/ManagerAlertsContext';
import { ManagerNavigationProvider } from '../navigation/ManagerNavigationContext';

const DeliveryLayout = lazy(() => import('../layout/DeliveryLayout').then((m) => ({ default: m.DeliveryLayout })));
const KitchenLayout = lazy(() => import('../layout/KitchenLayout').then((m) => ({ default: m.KitchenLayout })));
const PublicLayout = lazy(() => import('../layout/PublicLayout').then((m) => ({ default: m.PublicLayout })));

const KitchenBoardPage = lazy(() =>
  import('@/modules/kitchen/board/KitchenBoardPage').then((m) => ({ default: m.KitchenBoardPage }))
);
const DeliveryPanelPage = lazy(() =>
  import('@/modules/delivery/board/DeliveryBoardPage').then((m) => ({ default: m.DeliveryPanelPage }))
);

const ConsolePage = lazy(() => import('@/modules/console/ConsolePage').then((m) => ({ default: m.ConsolePage })));
const LoginPage = lazy(() => import('@/modules/auth/pages/LoginPage').then((m) => ({ default: m.LoginPage })));
const PublicOrderPage = lazy(() =>
  import('@/modules/orders/public/PublicOrderPage').then((m) => ({ default: m.PublicOrderPage }))
);
const PublicOrderTrackingPage = lazy(() =>
  import('@/modules/orders/public/PublicOrderTrackingPage').then((m) => ({ default: m.PublicOrderTrackingPage }))
);
const TenantScopeRequiredPage = lazy(() =>
  import('@/modules/public/TenantScopeRequiredPage').then((m) => ({ default: m.TenantScopeRequiredPage }))
);
const MasterLoginPage = lazy(() =>
  import('@/modules/master/auth/MasterLoginPage').then((m) => ({ default: m.MasterLoginPage }))
);
const MasterLayout = lazy(() =>
  import('@/modules/master/layout/MasterLayout').then((m) => ({ default: m.MasterLayout }))
);
const MasterDashboardPage = lazy(() =>
  import('@/modules/master/dashboard/MasterDashboardPage').then((m) => ({ default: m.MasterDashboardPage }))
);
const MasterClientsPage = lazy(() =>
  import('@/modules/master/clients/MasterClientsPage').then((m) => ({ default: m.MasterClientsPage }))
);
const MasterTenantsPage = lazy(() =>
  import('@/modules/master/tenants/MasterTenantsPage').then((m) => ({ default: m.MasterTenantsPage }))
);
const MasterPlansPage = lazy(() =>
  import('@/modules/master/plans/MasterPlansPage').then((m) => ({ default: m.MasterPlansPage }))
);

const ManagerOrdersPage = lazy(() =>
  import('@/pages/manager/orders/ManagerOrdersPage').then((m) => ({ default: m.ManagerOrdersPage }))
);
const ManagerTablesPage = lazy(() =>
  import('@/pages/manager/tables/ManagerTablesPage').then((m) => ({ default: m.ManagerTablesPage }))
);
const ManagerAlertsPage = lazy(() =>
  import('@/pages/manager/alerts/ManagerAlertsPage').then((m) => ({ default: m.ManagerAlertsPage }))
);
const ManagerKitchenMonitorPage = lazy(() =>
  import('@/modules/kitchen/monitor/ManagerKitchenMonitorPage').then((m) => ({ default: m.ManagerKitchenMonitorPage }))
);
const ManagerKitchenSettingsPage = lazy(() =>
  import('@/modules/kitchen/settings/ManagerKitchenSettingsPage').then((m) => ({ default: m.ManagerKitchenSettingsPage }))
);
const KitchenHistoryPage = lazy(() =>
  import('@/modules/kitchen/history/KitchenHistoryPage').then((m) => ({ default: m.KitchenHistoryPage }))
);

const DeliveryDriversPage = lazy(() =>
  import('@/pages/delivery/drivers/DeliveryDriversPage').then((m) => ({ default: m.DeliveryDriversPage }))
);
const DeliveryHistoryPage = lazy(() =>
  import('@/pages/delivery/history/DeliveryHistoryPage').then((m) => ({ default: m.DeliveryHistoryPage }))
);
const DeliverySettingsPage = lazy(() =>
  import('@/pages/delivery/settings/DeliverySettingsPage').then((m) => ({ default: m.DeliverySettingsPage }))
);

const StockLedgerPage = lazy(() =>
  import('@/pages/warehouse/stock-ledger/StockLedgerPage').then((m) => ({ default: m.StockLedgerPage }))
);
const WarehouseVouchersPage = lazy(() =>
  import('@/pages/warehouse/vouchers/WarehouseVouchersPage').then((m) => ({ default: m.WarehouseVouchersPage }))
);
const WarehouseSuppliersPage = lazy(() =>
  import('@/pages/warehouse/suppliers/WarehouseSuppliersPage').then((m) => ({ default: m.WarehouseSuppliersPage }))
);

const OperationalHeartPage = lazy(() =>
  import('@/pages/intelligence/operational-heart/OperationalHeartPage').then((m) => ({ default: m.OperationalHeartPage }))
);
const IntelligenceReportsPage = lazy(() =>
  import('@/pages/intelligence/reports/IntelligenceReportsPage').then((m) => ({ default: m.IntelligenceReportsPage }))
);

const SystemUsersPage = lazy(() =>
  import('@/pages/system/users/SystemUsersPage').then((m) => ({ default: m.SystemUsersPage }))
);
const ProductsPage = lazy(() =>
  import('@/modules/system/catalog/products/ProductsPage').then((m) => ({ default: m.ProductsPage }))
);
const SystemSettingsPage = lazy(() =>
  import('@/pages/system/settings/SystemSettingsPage').then((m) => ({ default: m.SystemSettingsPage }))
);

const PublicTablesPage = lazy(() =>
  import('@/pages/public/tables/PublicTablesPage').then((m) => ({ default: m.PublicTablesPage }))
);

function RouteLoading() {
  return <div className="p-4 text-center text-sm font-semibold text-gray-600">جارٍ تحميل الصفحة...</div>;
}

function withRouteSuspense(element: ReactElement) {
  return <Suspense fallback={<RouteLoading />}>{element}</Suspense>;
}

function ConsoleProviders({ children }: { children: ReactElement }) {
  return (
    <ManagerNavigationProvider>
      <ManagerAlertsProvider>{children}</ManagerAlertsProvider>
    </ManagerNavigationProvider>
  );
}

function RoleGuard({ allowedRole, loginPath }: { allowedRole: UserRole; loginPath: string }) {
  const user = useAuthStore((state) => state.user);
  const role = useAuthStore((state) => state.role);

  const scopedLoginPath = (() => {
    if (typeof window === 'undefined') {
      return loginPath;
    }
    const tenantCode = window.sessionStorage.getItem('active_tenant_code')?.trim();
    if (!tenantCode) {
      return loginPath;
    }
    if (allowedRole === 'kitchen') {
      return `/t/${encodeURIComponent(tenantCode)}/kitchen/login`;
    }
    if (allowedRole === 'delivery') {
      return `/t/${encodeURIComponent(tenantCode)}/delivery/login`;
    }
    return loginPath;
  })();

  if (!role || !user) {
    return <Navigate to={scopedLoginPath} replace />;
  }
  if (role !== allowedRole) {
    return (
      <Navigate
        to={role === 'manager' ? '/console' : role === 'kitchen' ? '/kitchen/console' : '/delivery/console'}
        replace
      />
    );
  }
  return <Outlet />;
}

function MasterGuard() {
  const identity = useMasterAuthStore((state) => state.identity);
  const status = useMasterAuthStore((state) => state.status);
  const hydrateSession = useMasterAuthStore((state) => state.hydrateSession);
  const location = useLocation();

  useEffect(() => {
    if (status === 'idle') {
      void hydrateSession();
    }
  }, [hydrateSession, status]);

  if (status === 'idle' || status === 'checking') {
    return <RouteLoading />;
  }

  if (!identity) {
    return <Navigate to="/master/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }

  return <Outlet />;
}

const LEGACY_ROUTE_REDIRECTS: Array<{ prefix: string; target: string }> = [
  { prefix: '/manager/dashboard', target: '/console' },
  { prefix: '/manager/orders', target: '/console?channel=operations&section=orders' },
  { prefix: '/manager/tables', target: '/console?channel=operations&section=tables' },
  { prefix: '/manager/alerts', target: '/console?channel=operations&section=alerts' },
  { prefix: '/manager/kitchen-monitor', target: '/console?channel=kitchen&section=kitchenMonitor' },
  { prefix: '/manager', target: '/console' },
  { prefix: '/operations/orders', target: '/console?channel=operations&section=orders' },
  { prefix: '/operations/tables', target: '/console?channel=operations&section=tables' },
  { prefix: '/operations', target: '/console?channel=operations' },
  { prefix: '/warehouse/dashboard', target: '/console?channel=warehouse&section=warehouseOverview' },
  { prefix: '/warehouse', target: '/console?channel=warehouse&section=warehouseOverview' },
  { prefix: '/finance/transactions', target: '/console?channel=finance&section=financeOverview' },
  { prefix: '/finance/expenses', target: '/console?channel=finance&section=financeExpenses' },
  { prefix: '/finance', target: '/console?channel=finance&section=financeOverview' },
  { prefix: '/intelligence/dashboard', target: '/console?channel=intelligence&section=operationalHeart' },
  { prefix: '/intelligence/audit', target: '/console?channel=intelligence&section=operationalHeart' },
  { prefix: '/intelligence', target: '/console?channel=intelligence&section=operationalHeart' },
  { prefix: '/system/roles', target: '/console/system/settings' },
  { prefix: '/system/audit-log', target: '/console/system/settings' },
  { prefix: '/system/audit', target: '/console/system/settings' },
  { prefix: '/system/settings', target: '/console/system/settings' },
  { prefix: '/system', target: '/console/system' },
];

function resolveLegacyRedirect(pathname: string): string {
  for (const redirect of LEGACY_ROUTE_REDIRECTS) {
    if (pathname.startsWith(redirect.prefix)) {
      return redirect.target;
    }
  }
  return '/console';
}

function LegacyRedirect() {
  const location = useLocation();
  const target = resolveLegacyRedirect(location.pathname);
  const mergedTarget = location.search
    ? `${target}${target.includes('?') ? '&' : '?'}${location.search.slice(1)}`
    : target;
  return <Navigate to={mergedTarget} replace />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={withRouteSuspense(<TenantScopeRequiredPage />)} />

      <Route path="/manager/login" element={withRouteSuspense(<LoginPage role="manager" />)} />
      <Route path="/t/:tenantCode/manager/login" element={withRouteSuspense(<LoginPage role="manager" />)} />
      <Route path="/t/:tenantCode/kitchen/login" element={withRouteSuspense(<LoginPage role="kitchen" />)} />
      <Route path="/kitchen/login" element={withRouteSuspense(<LoginPage role="kitchen" />)} />
      <Route path="/t/:tenantCode/delivery/login" element={withRouteSuspense(<LoginPage role="delivery" />)} />
      <Route path="/delivery/login" element={withRouteSuspense(<LoginPage role="delivery" />)} />
      <Route path="/master/login" element={withRouteSuspense(<MasterLoginPage />)} />

      <Route element={<MasterGuard />}>
        <Route element={withRouteSuspense(<MasterLayout />)}>
          <Route path="/master" element={<Navigate to="/master/dashboard" replace />} />
          <Route path="/master/dashboard" element={withRouteSuspense(<MasterDashboardPage />)} />
          <Route path="/master/clients" element={withRouteSuspense(<MasterClientsPage />)} />
          <Route path="/master/tenants" element={withRouteSuspense(<MasterTenantsPage />)} />
          <Route path="/master/addons" element={withRouteSuspense(<MasterPlansPage />)} />
          <Route path="/master/plans" element={<Navigate to="/master/addons" replace />} />
        </Route>
      </Route>

      <Route element={withRouteSuspense(<PublicLayout />)}>
        <Route path="/t/:tenantCode" element={<Navigate to="order" replace />} />
        <Route path="/t/:tenantCode/order" element={withRouteSuspense(<PublicOrderPage />)} />
        <Route path="/t/:tenantCode/menu" element={withRouteSuspense(<PublicOrderPage />)} />
        <Route path="/t/:tenantCode/track" element={withRouteSuspense(<PublicOrderTrackingPage />)} />
        <Route path="/t/:tenantCode/public/tables" element={withRouteSuspense(<PublicTablesPage />)} />
      </Route>

      <Route path="/order" element={withRouteSuspense(<TenantScopeRequiredPage />)} />
      <Route path="/menu" element={withRouteSuspense(<TenantScopeRequiredPage />)} />
      <Route path="/track" element={withRouteSuspense(<TenantScopeRequiredPage />)} />
      <Route path="/tracking" element={withRouteSuspense(<TenantScopeRequiredPage />)} />
      <Route path="/public/tables" element={withRouteSuspense(<TenantScopeRequiredPage />)} />

      <Route element={<RoleGuard allowedRole="manager" loginPath="/manager/login" />}>
        <Route
          element={
            <ConsoleProviders>
              <Suspense fallback={<RouteLoading />}>
                <ConsolePage />
              </Suspense>
            </ConsoleProviders>
          }
        >
          <Route path="/console" element={withRouteSuspense(<></>)} />

          <Route path="/console/operations" element={<Navigate to="/console?channel=operations" replace />} />
          <Route path="/console/operations/overview" element={<Navigate to="/console" replace />} />
          <Route path="/console/operations/orders" element={withRouteSuspense(<ManagerOrdersPage />)} />
          <Route path="/console/operations/tables" element={withRouteSuspense(<ManagerTablesPage />)} />
          <Route path="/console/alerts" element={withRouteSuspense(<ManagerAlertsPage />)} />
          <Route path="/console/operations/alerts" element={<Navigate to="/console/alerts" replace />} />

          <Route path="/console/operations/menu" element={withRouteSuspense(<ProductsPage />)} />
          <Route path="/console/kitchen" element={<Navigate to="/console?channel=kitchen&section=kitchenMonitor" replace />} />
          <Route path="/console/kitchen/monitor" element={withRouteSuspense(<ManagerKitchenMonitorPage />)} />
          <Route path="/console/kitchen/settings" element={withRouteSuspense(<ManagerKitchenSettingsPage />)} />
          <Route path="/console/restaurant" element={<Navigate to="/console?channel=operations&section=menu" replace />} />
          <Route path="/console/restaurant/menu" element={<Navigate to="/console/operations/menu" replace />} />
          <Route path="/console/restaurant/expenses" element={<Navigate to="/console/finance/expenses" replace />} />
          <Route path="/console/restaurant/settings" element={<Navigate to="/console/operations/menu" replace />} />

          <Route path="/console/delivery" element={<Navigate to="/console?channel=delivery" replace />} />
          <Route path="/console/delivery/drivers" element={withRouteSuspense(<DeliveryDriversPage />)} />
          <Route path="/console/delivery/history" element={withRouteSuspense(<DeliveryHistoryPage />)} />
          <Route path="/console/delivery/settings" element={withRouteSuspense(<DeliverySettingsPage />)} />

          <Route path="/console/warehouse" element={<Navigate to="/console?channel=warehouse&section=warehouseOverview" replace />} />
          <Route path="/console/warehouse/stock-ledger" element={withRouteSuspense(<StockLedgerPage />)} />
          <Route path="/console/warehouse/vouchers" element={withRouteSuspense(<WarehouseVouchersPage />)} />
          <Route path="/console/warehouse/suppliers" element={withRouteSuspense(<WarehouseSuppliersPage />)} />

          <Route path="/console/finance" element={<Navigate to="/console?channel=finance" replace />} />
          <Route path="/console/finance/dashboard" element={<Navigate to="/console?channel=finance&section=financeOverview" replace />} />
          <Route path="/console/finance/transactions" element={<Navigate to="/console?channel=finance&section=financeEntries" replace />} />
          <Route path="/console/finance/expenses" element={<Navigate to="/console?channel=finance&section=financeExpenses" replace />} />
          <Route path="/console/finance/cash-shift" element={<Navigate to="/console?channel=finance&section=financeOverview" replace />} />

          <Route path="/console/intelligence" element={<Navigate to="/console?channel=intelligence" replace />} />
          <Route path="/console/intelligence/operational-heart" element={withRouteSuspense(<OperationalHeartPage />)} />
          <Route path="/console/intelligence/reports" element={withRouteSuspense(<IntelligenceReportsPage />)} />

          <Route path="/console/control-plane" element={<Navigate to="/console/system/settings" replace />} />
          <Route path="/console/plans" element={<Navigate to="/console" replace />} />
          <Route path="/console/system" element={withRouteSuspense(<SystemUsersPage />)} />
          <Route path="/console/system/users" element={<Navigate to="/console/system" replace />} />
          <Route path="/console/system/catalog" element={<Navigate to="/console/operations/menu" replace />} />
          <Route path="/console/system/catalog/products" element={<Navigate to="/console/operations/menu" replace />} />
          <Route path="/console/system/roles" element={<Navigate to="/console/system/settings" replace />} />
          <Route path="/console/system/settings/*" element={withRouteSuspense(<SystemSettingsPage />)} />
          <Route path="/console/system/audit-log" element={<Navigate to="/console/system/settings" replace />} />
        </Route>
        <Route path="/manager/*" element={withRouteSuspense(<LegacyRedirect />)} />
        <Route path="/operations/*" element={withRouteSuspense(<LegacyRedirect />)} />
        <Route path="/warehouse/*" element={withRouteSuspense(<LegacyRedirect />)} />
        <Route path="/finance/*" element={withRouteSuspense(<LegacyRedirect />)} />
        <Route path="/intelligence/*" element={withRouteSuspense(<LegacyRedirect />)} />
        <Route path="/system/*" element={withRouteSuspense(<LegacyRedirect />)} />
      </Route>

      <Route element={<RoleGuard allowedRole="kitchen" loginPath="/kitchen/login" />}>
        <Route element={withRouteSuspense(<KitchenLayout />)}>
          <Route path="/kitchen/console" element={<Navigate to="/kitchen/console/monitor" replace />} />
          <Route path="/kitchen/console/monitor" element={withRouteSuspense(<KitchenBoardPage />)} />
          <Route path="/kitchen/console/history" element={withRouteSuspense(<KitchenHistoryPage />)} />
          <Route path="/kitchen/board" element={<Navigate to="/kitchen/console" replace />} />
          <Route path="/kitchen/monitor" element={<Navigate to="/kitchen/console/monitor" replace />} />
          <Route path="/kitchen/history" element={<Navigate to="/kitchen/console/history" replace />} />
          <Route path="/kitchen/prep-timeline" element={<Navigate to="/kitchen/console/history" replace />} />
        </Route>
      </Route>

      <Route element={<RoleGuard allowedRole="delivery" loginPath="/delivery/login" />}>
        <Route element={withRouteSuspense(<DeliveryLayout />)}>
          <Route path="/delivery/console" element={withRouteSuspense(<DeliveryPanelPage />)} />
          <Route path="/delivery/board" element={<Navigate to="/delivery/console" replace />} />
          <Route path="/delivery/history" element={<Navigate to="/delivery/console" replace />} />
          <Route path="/delivery/drivers" element={<Navigate to="/delivery/console" replace />} />
          <Route path="/delivery/panel" element={<Navigate to="/delivery/console" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
