import type {
  AccountSession,
  AccountSessionsRevokeResult,
  AuthSession,
  CreateOrderPayload,
  DashboardStats,
  OperationalHeartDashboard,
  CashboxMovement,
  DeliveryAddressNodeList,
  DeliveryAccountingBackfillResult,
  DeliveryAccountingMigrationStatus,
  DeliveryAddressNode,
  DeliveryAddressNodeCreatePayload,
  DeliveryAddressNodeUpdatePayload,
  DeliveryAddressPricing,
  DeliveryAddressPricingList,
  DeliveryAddressPricingUpsertPayload,
  DeliveryAssignment,
  DeliveryDispatch,
  DeliveryDriver,
  DeliveryDriverTelegramLink,
  DeliveryProvider,
  DeliveryHistoryRow,
  DeliveryLocationPricingQuote,
  DeliverySettlement,
  DeliveryPolicies,
  DeliverySettings,
  ExpenseAttachment,
  ExpenseCostCenter,
  Expense,
  FinancialTransaction,
  KitchenOrdersPage,
  KitchenRuntimeSettings,
  LoginPayload,
  MasterClient,
  MasterOverview,
  MasterAddon,
  MasterSession,
  MasterTenantAccess,
  MasterTenantCreatePayload,
  MasterTenantCreateResult,
  MasterTenantUpdatePayload,
  MasterTenant,
  ManagerTable,
  ManagerTenantContext,
  ManagerKitchenAccess,
  OperationalCapabilities,
  OperationalSetting,
  Order,
  OrdersPage,
  OrderStatus,
  OrderTransitionLog,
  PermissionCatalogItem,
  PublicOrderJourneyBootstrap,
  PublicOrderTracking,
  PublicProduct,
  StorefrontSettings,
  TelegramBotHealth,
  TelegramBotSettings,
  SystemAuditLog,
  Product,
  ProductApiResponse,
  ProductCategory,
  ProductKind,
  ProductsPage,
  ProductPayload,
  ReportByTypeRow,
  ReportDailyRow,
  ReportMonthlyRow,
  ReportPeakHoursPerformance,
  ReportPeriodComparison,
  ReportPerformance,
  ReportProfitability,
  RestaurantEmployee,
  RestaurantEmployeePayload,
  SecurityAuditEvent,
  ShiftClosure,
  SystemBackup,
  SystemContext,
  TableInfo,
  TableSession,
  TableSessionSettlement,
  User,
  UserPermissionsProfile,
  UserRole,
  WarehouseDashboard,
  WarehouseInboundVoucher,
  WarehouseItem,
  WarehouseLedgerRow,
  WarehouseOutboundReason,
  WarehouseOutboundVoucher,
  WarehouseStockCount,
  WarehouseStockBalance,
  WarehouseSupplier,
  TenantEntry,
} from './types';
import { sanitizeMojibakeText } from '../utils/textSanitizer';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
const AUTH_STORAGE_KEY = 'restaurant-auth';
const ACTIVE_TENANT_CODE_STORAGE_KEY = 'active_tenant_code';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  skipAuthRefresh?: boolean;
}

interface MasterRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  redirectOnUnauthorized?: boolean;
}

function resolveTenantEntryCodeFromLocation(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const pathMatch = window.location.pathname.match(/^\/t\/([^/]+)(?:\/|$)/i);
  if (pathMatch?.[1]) {
    return decodeURIComponent(pathMatch[1]).trim() || null;
  }

  const queryTenant = new URLSearchParams(window.location.search).get('tenant');
  if (queryTenant?.trim()) {
    return queryTenant.trim();
  }

  const storedTenantCode = window.sessionStorage.getItem(ACTIVE_TENANT_CODE_STORAGE_KEY)?.trim();
  return storedTenantCode || null;
}

interface CreateDriverPayload {
  user_id?: number | null;
  name: string;
  provider_id?: number | null;
  phone: string;
  vehicle?: string | null;
  active: boolean;
}

interface UpdateDriverPayload {
  provider_id?: number | null;
  name: string;
  phone: string;
  vehicle?: string | null;
  active: boolean;
  status: 'available' | 'busy' | 'inactive';
}

interface DeliveryProviderPayload {
  account_user_id?: number | null;
  name: string;
  provider_type: 'internal_team' | 'partner_company';
  active: boolean;
}

interface DeliveryDispatchPayload {
  order_id: number;
  provider_id?: number | null;
  driver_id?: number | null;
}

interface ExpensePayload {
  title: string;
  category: string;
  cost_center_id: number;
  amount: number;
  note?: string | null;
}

interface ExpenseReviewPayload {
  note?: string | null;
}

interface ExpenseCostCenterPayload {
  code: string;
  name: string;
  active: boolean;
}

interface ExpenseAttachmentPayload {
  file_name?: string | null;
  mime_type: string;
  data_base64: string;
}

interface ShiftClosurePayload {
  opening_cash: number;
  actual_cash: number;
  note?: string | null;
}

interface UserPayload {
  name: string;
  role: UserRole;
  active: boolean;
  username?: string;
  password?: string;
}

interface UserPermissionsUpdatePayload {
  allow: string[];
  deny: string[];
}

interface AccountProfilePayload {
  name: string;
  password?: string;
}

interface SystemBackupRestorePayload {
  filename: string;
  confirm_phrase: string;
}

interface ProductImagePayload {
  mime_type: string;
  data_base64: string;
}

interface ProductCategoryPayload {
  name: string;
  active: boolean;
  sort_order: number;
}

interface WarehouseSupplierPayload {
  name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  payment_term_days: number;
  credit_limit?: number | null;
  quality_rating: number;
  lead_time_days: number;
  notes?: string | null;
  active: boolean;
  supplied_item_ids: number[];
}

interface WarehouseItemPayload {
  name: string;
  unit: string;
  alert_threshold: number;
  active: boolean;
}

interface WarehouseInboundVoucherPayload {
  supplier_id: number;
  reference_no?: string | null;
  note?: string | null;
  idempotency_key?: string | null;
  items: Array<{
    item_id: number;
    quantity: number;
    unit_cost: number;
  }>;
}

interface WarehouseOutboundVoucherPayload {
  reason_code: string;
  reason_note?: string | null;
  note?: string | null;
  idempotency_key?: string | null;
  items: Array<{
    item_id: number;
    quantity: number;
  }>;
}

interface WarehouseStockCountPayload {
  note?: string | null;
  idempotency_key?: string | null;
  items: Array<{
    item_id: number;
    counted_quantity: number;
  }>;
}

function normalizeProductKind(kind: ProductApiResponse['kind'], normalizedKind?: ProductKind | null): ProductKind {
  if (normalizedKind === 'primary' || normalizedKind === 'secondary') {
    return normalizedKind;
  }
  return kind === 'internal' || kind === 'secondary' ? 'secondary' : 'primary';
}

function normalizeProduct(product: ProductApiResponse): Product {
  const {
    kind,
    normalized_kind,
    secondary_links,
    consumption_components,
    ...rest
  } = product;
  const resolvedKind = normalizeProductKind(kind, normalized_kind);
  return {
    ...rest,
    kind: resolvedKind,
    legacy_kind: kind === 'sellable' || kind === 'internal' ? kind : resolvedKind === 'primary' ? 'sellable' : 'internal',
    secondary_links: secondary_links ?? [],
    consumption_components: consumption_components ?? [],
  };
}

function readCookie(name: string): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function readCsrfToken(): string | null {
  return readCookie('csrf_token');
}

function readMasterCsrfToken(): string | null {
  return readCookie('master_csrf_token');
}

function clearAuthStorage(): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

function redirectToRoleLogin(): void {
  if (typeof window === 'undefined') {
    return;
  }

  const path = window.location.pathname;
  const scopedTenantCode = resolveTenantEntryCodeFromLocation();
  if (path.startsWith('/manager') || path.startsWith('/console')) {
    window.location.href = '/manager/login';
    return;
  }
  if (path.startsWith('/kitchen')) {
    window.location.href = scopedTenantCode ? `/t/${encodeURIComponent(scopedTenantCode)}/kitchen/login` : '/kitchen/login';
    return;
  }
  if (path.startsWith('/delivery')) {
    window.location.href = scopedTenantCode ? `/t/${encodeURIComponent(scopedTenantCode)}/delivery/login` : '/delivery/login';
    return;
  }
  window.location.href = '/';
}

function redirectToMasterLogin(): void {
  if (typeof window === 'undefined') {
    return;
  }

  const from = `${window.location.pathname}${window.location.search}`;
  const query = new URLSearchParams({ from });
  window.location.href = `/master/login?${query.toString()}`;
}

function parseError(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') {
    return fallback;
  }

  const data = payload as { detail?: unknown };

  if (typeof data.detail === 'string') {
    return normalizeErrorText(data.detail, fallback);
  }

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    const first = data.detail[0] as { msg?: string };
    if (typeof first?.msg === 'string') {
      return normalizeErrorText(first.msg, fallback);
    }
  }

  return fallback;
}

function normalizeErrorText(value: string, fallback = 'حدث خطأ غير مقروء في النص.'): string {
  return sanitizeMojibakeText(value, fallback);
}

function normalizePayloadText<T>(value: T): T {
  if (typeof value === 'string') {
    return sanitizeMojibakeText(value, 'غير متاح') as T;
  }
  if (Array.isArray(value)) {
    return value.map((item) => normalizePayloadText(item)) as T;
  }
  if (value && typeof value === 'object') {
    const normalized: Record<string, unknown> = {};
    Object.entries(value as Record<string, unknown>).forEach(([key, entry]) => {
      normalized[key] = normalizePayloadText(entry);
    });
    return normalized as T;
  }
  return value;
}

async function tryRefreshAccessToken(): Promise<boolean> {
  try {
    const csrfToken = readCsrfToken();
    const headers: Record<string, string> = {};
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers,
    });

    if (!response.ok) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const tenantCode = resolveTenantEntryCodeFromLocation();
  if (tenantCode) {
    headers['X-Tenant-Code'] = tenantCode;
  }

  if (options.auth && options.method && options.method !== 'GET') {
    const csrfToken = readCsrfToken();
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    credentials: 'include',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401 && options.auth && !options.skipAuthRefresh) {
    const refreshed = await tryRefreshAccessToken();
    if (refreshed) {
      return request<T>(path, { ...options, skipAuthRefresh: true });
    }

    clearAuthStorage();
    redirectToRoleLogin();
    throw new Error('انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى');
  }

  if (!response.ok) {
    const fallback = `فشل الطلب (${response.status})`;
    let message = fallback;

    try {
      const payload = await response.json();
      message = parseError(payload, fallback);
    } catch {
      // Ignore JSON parse failure and keep fallback message.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json()) as T;
  return normalizePayloadText(payload);
}

async function masterRequest<T>(path: string, options: MasterRequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (options.method && options.method !== 'GET') {
    const csrfToken = readMasterCsrfToken();
    if (csrfToken) {
      headers['X-Master-CSRF-Token'] = csrfToken;
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    credentials: 'include',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401 && options.redirectOnUnauthorized) {
    redirectToMasterLogin();
    throw new Error('انتهت جلسة اللوحة الأم، يرجى تسجيل الدخول مرة أخرى.');
  }

  if (!response.ok) {
    const fallback = `فشل الطلب (${response.status})`;
    let message = fallback;

    try {
      const payload = await response.json();
      message = parseError(payload, fallback);
    } catch {
      // Ignore JSON parse failure and keep fallback message.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json()) as T;
  return normalizePayloadText(payload);
}

export const api = {
  masterLogin: (payload: { username: string; password: string }) =>
    masterRequest<MasterSession>('/master-auth/login', { method: 'POST', body: payload }),
  masterLogout: () => masterRequest<void>('/master-auth/logout', { method: 'POST' }),
  masterSession: () => masterRequest<MasterSession>('/master-auth/session'),
  masterOverview: () => masterRequest<MasterOverview>('/master/overview', { redirectOnUnauthorized: true }),
  masterClients: () => masterRequest<MasterClient[]>('/master/clients', { redirectOnUnauthorized: true }),
  masterTenants: () => masterRequest<MasterTenant[]>('/master/tenants', { redirectOnUnauthorized: true }),
  masterAddons: () => masterRequest<MasterAddon[]>('/master/addons', { redirectOnUnauthorized: true }),
  masterCreateTenant: (payload: MasterTenantCreatePayload) =>
    masterRequest<MasterTenantCreateResult>('/master/tenants', {
      method: 'POST',
      body: payload,
      redirectOnUnauthorized: true,
    }),
  masterUpdateTenant: (tenantId: string, payload: MasterTenantUpdatePayload) =>
    masterRequest<MasterTenant>(`/master/tenants/${tenantId}`, {
      method: 'PUT',
      body: payload,
      redirectOnUnauthorized: true,
    }),
  masterRegenerateTenantPassword: (tenantId: string) =>
    masterRequest<MasterTenantAccess>(`/master/tenants/${tenantId}/regenerate-manager-password`, {
      method: 'POST',
      redirectOnUnauthorized: true,
    }),
  masterPauseTenantAddon: (tenantId: string, addonId: string) =>
    masterRequest<MasterTenant>(`/master/tenants/${tenantId}/addons/${encodeURIComponent(addonId)}/pause`, {
      method: 'POST',
      redirectOnUnauthorized: true,
    }),
  masterResumeTenantAddon: (tenantId: string, addonId: string) =>
    masterRequest<MasterTenant>(`/master/tenants/${tenantId}/addons/${encodeURIComponent(addonId)}/resume`, {
      method: 'POST',
      redirectOnUnauthorized: true,
    }),
  masterToggleTenantSuspension: (tenantId: string) =>
    masterRequest<MasterTenant>(`/master/tenants/${tenantId}/toggle-suspension`, {
      method: 'POST',
      redirectOnUnauthorized: true,
    }),
  masterDeleteTenant: (tenantId: string) =>
    masterRequest<void>(`/master/tenants/${tenantId}`, {
      method: 'DELETE',
      redirectOnUnauthorized: true,
    }),

  login: (payload: LoginPayload) => request<AuthSession>('/auth/login', { method: 'POST', body: payload }),
  refresh: () => request<AuthSession>('/auth/refresh', { method: 'POST' }),
  logout: () => request<{ status: string }>('/auth/logout', { method: 'POST', auth: true }),
  me: () => request<User>('/auth/me', { auth: true }),

  publicStorefrontSettings: () => request<StorefrontSettings>('/public/storefront-settings'),
  publicTenantEntry: (tenantCode: string) =>
    request<TenantEntry>(`/public/tenant-entry?tenant=${encodeURIComponent(tenantCode)}`),
  publicOrderJourneyBootstrap: (tableId?: number) => {
    const query = tableId ? `?table_id=${tableId}` : '';
    return request<PublicOrderJourneyBootstrap>(`/public/order-journey/bootstrap${query}`);
  },
  publicTrackOrder: (code: string, refreshToken?: number) => {
    const query = new URLSearchParams({ code: code.trim().toUpperCase() });
    if (refreshToken) {
      query.set('_', String(refreshToken));
    }
    return request<PublicOrderTracking>(`/public/orders/track?${query.toString()}`);
  },
  publicProducts: () => request<PublicProduct[]>('/public/products'),
  publicTables: () => request<TableInfo[]>('/public/tables'),
  publicTableSession: (tableId: number) => request<TableSession>(`/public/tables/${tableId}/session`),
  publicDeliveryAddressNodes: (parentId?: number) => {
    const query = typeof parentId === 'number' ? `?parent_id=${parentId}` : '';
    return request<DeliveryAddressNodeList>(`/public/delivery/address-nodes${query}`);
  },
  publicDeliveryPricingQuote: (nodeId?: number) => {
    const query = typeof nodeId === 'number' ? `?node_id=${nodeId}` : '';
    return request<DeliveryLocationPricingQuote>(`/public/delivery/pricing/quote${query}`);
  },
  publicDeliverySettings: () => request<DeliverySettings>('/public/delivery/settings'),
  publicOperationalCapabilities: () => request<OperationalCapabilities>('/public/operational-capabilities'),
  createPublicOrder: (payload: CreateOrderPayload) => request<Order>('/public/orders', { method: 'POST', body: payload }),

  managerDashboard: (_role?: UserRole) => request<DashboardStats>('/manager/dashboard', { auth: true }),
  managerDashboardOperationalHeart: (_role?: UserRole) =>
    request<OperationalHeartDashboard>('/manager/dashboard/operational-heart', { auth: true }),
  managerTenantContext: (_role?: UserRole) => request<ManagerTenantContext>('/manager/tenant-context', { auth: true }),
  managerAddons: (_role?: UserRole) => request<MasterAddon[]>('/manager/addons', { auth: true }),
  managerKitchenAccess: (_role?: UserRole) =>
    request<ManagerKitchenAccess>('/manager/kitchen/access', { auth: true }),
  managerRegenerateKitchenAccessPassword: (_role: UserRole) =>
    request<ManagerKitchenAccess>('/manager/kitchen/access/regenerate-password', { method: 'POST', auth: true }),
  managerOperationalCapabilities: (_role?: UserRole) =>
    request<OperationalCapabilities>('/manager/operational-capabilities', { auth: true }),
  managerRestaurantEmployees: (
    _role?: UserRole,
    params?: { search?: string; employeeType?: string; activeOnly?: boolean }
  ) => {
    const query = new URLSearchParams();
    if (params?.search?.trim()) {
      query.set('search', params.search.trim());
    }
    if (params?.employeeType?.trim()) {
      query.set('employee_type', params.employeeType.trim());
    }
    if (params?.activeOnly) {
      query.set('active_only', 'true');
    }
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<RestaurantEmployee[]>(`/manager/staff${suffix}`, { auth: true });
  },
  managerCreateRestaurantEmployee: (_role: UserRole, payload: RestaurantEmployeePayload) =>
    request<RestaurantEmployee>('/manager/staff', { method: 'POST', auth: true, body: payload }),
  managerUpdateRestaurantEmployee: (_role: UserRole, employeeId: number, payload: RestaurantEmployeePayload) =>
    request<RestaurantEmployee>(`/manager/staff/${employeeId}`, { method: 'PUT', auth: true, body: payload }),
  managerDeleteRestaurantEmployee: (_role: UserRole, employeeId: number) =>
    request<void>(`/manager/staff/${employeeId}`, { method: 'DELETE', auth: true }),
  managerOperationalSettings: (_role?: UserRole) =>
    request<OperationalSetting[]>('/manager/settings/operational', { auth: true }),
  managerUpdateOperationalSetting: (_role: UserRole, payload: { key: string; value: string }) =>
    request<OperationalSetting>('/manager/settings/operational', { method: 'PUT', auth: true, body: payload }),
  managerTelegramBotSettings: (_role?: UserRole) =>
    request<TelegramBotSettings>('/manager/settings/telegram-bot', { auth: true }),
  managerTelegramBotHealth: (_role?: UserRole) =>
    request<TelegramBotHealth>('/manager/settings/telegram-bot/health', { auth: true }),
  managerUpdateTelegramBotSettings: (
    _role: UserRole,
    payload: { enabled: boolean; bot_token?: string | null; bot_username?: string | null }
  ) => request<TelegramBotSettings>('/manager/settings/telegram-bot', { method: 'PUT', auth: true, body: payload }),
  managerOrders: (_role?: UserRole) => request<Order[]>('/manager/orders', { auth: true }),
  managerActiveOrders: (_role?: UserRole, limit = 200) =>
    request<Order[]>(`/manager/orders/active?limit=${limit}`, { auth: true }),
  managerTables: (_role?: UserRole) => request<ManagerTable[]>('/manager/tables', { auth: true }),
  managerCreateTable: (_role: UserRole, payload: { status: 'available' | 'occupied' | 'reserved' }) =>
    request<ManagerTable>('/manager/tables', { method: 'POST', auth: true, body: payload }),
  managerUpdateTable: (_role: UserRole, tableId: number, payload: { status: 'available' | 'occupied' | 'reserved' }) =>
    request<ManagerTable>(`/manager/tables/${tableId}`, { method: 'PUT', auth: true, body: payload }),
  managerDeleteTable: (_role: UserRole, tableId: number) =>
    request<void>(`/manager/tables/${tableId}`, { method: 'DELETE', auth: true }),
  managerTableSessions: (_role?: UserRole) => request<TableSession[]>('/manager/table-sessions', { auth: true }),
  managerSettleTableSession: (_role: UserRole, tableId: number, amountReceived?: number) =>
    request<TableSessionSettlement>(`/manager/tables/${tableId}/settle-session`, {
      method: 'POST',
      auth: true,
      body: { amount_received: amountReceived },
    }),
  managerCreateManualOrder: (_role: UserRole, payload: CreateOrderPayload) =>
    request<Order>('/manager/orders/manual', { method: 'POST', auth: true, body: payload }),
  managerOrdersPaged: (
    _role: UserRole,
    params: {
      page: number;
      pageSize: number;
      search?: string;
      sortBy?: 'created_at' | 'total' | 'status' | 'id';
      sortDirection?: 'asc' | 'desc';
      status?: OrderStatus;
      orderType?: 'dine-in' | 'takeaway' | 'delivery';
    }
  ) => {
    const query = new URLSearchParams({
      page: String(params.page),
      page_size: String(params.pageSize),
      sort_by: params.sortBy ?? 'created_at',
      sort_direction: params.sortDirection ?? 'desc',
    });
    if (params.search && params.search.trim().length > 0) {
      query.set('search', params.search.trim());
    }
    if (params.status) {
      query.set('status', params.status);
    }
    if (params.orderType) {
      query.set('order_type', params.orderType);
    }
    return request<OrdersPage>(`/manager/orders/paged?${query.toString()}`, { auth: true });
  },
  managerKitchenOrders: (_role?: UserRole) => request<Order[]>('/manager/kitchen/orders', { auth: true }),
  managerKitchenOrdersPaged: (
    _role: UserRole,
    params: {
      page: number;
      pageSize: number;
      scope?: 'active' | 'history';
      search?: string;
      sortBy?: 'created_at' | 'total' | 'status' | 'id';
      sortDirection?: 'asc' | 'desc';
    }
  ) => {
    const query = new URLSearchParams({
      page: String(params.page),
      page_size: String(params.pageSize),
      scope: params.scope ?? 'active',
      sort_by: params.sortBy ?? 'created_at',
      sort_direction: params.sortDirection ?? 'desc',
    });
    if (params.search && params.search.trim().length > 0) {
      query.set('search', params.search.trim());
    }
    return request<KitchenOrdersPage>(`/manager/kitchen/orders/paged?${query.toString()}`, { auth: true });
  },
  managerTransitionOrder: (
    _role: UserRole,
    orderId: number,
    targetStatus: OrderStatus,
    amountReceived?: number,
    collectPayment = true,
    reasonCode?: string,
    reasonNote?: string
  ) =>
    request<Order>(`/manager/orders/${orderId}/transition`, {
      method: 'POST',
      auth: true,
      body: {
        target_status: targetStatus,
        amount_received: amountReceived,
        collect_payment: collectPayment,
        reason_code: reasonCode,
        reason_note: reasonNote,
      },
    }),
  managerCollectOrderPayment: (_role: UserRole, orderId: number, amountReceived?: number) =>
    request<Order>(`/manager/orders/${orderId}/collect-payment`, {
      method: 'POST',
      auth: true,
      body: { amount_received: amountReceived },
    }),
  managerSettleDeliveryOrder: (_role: UserRole, orderId: number) =>
    request<DeliverySettlement>(`/manager/orders/${orderId}/settle-delivery`, {
      method: 'POST',
      auth: true,
    }),
  managerEmergencyDeliveryFail: (_role: UserRole, orderId: number, reasonCode: string, reasonNote?: string) =>
    request<Order>(`/manager/orders/${orderId}/emergency-delivery-fail`, {
      method: 'POST',
      auth: true,
      body: { reason_code: reasonCode, reason_note: reasonNote },
    }),
  managerResolveDeliveryFailure: (
    _role: UserRole,
    orderId: number,
    resolutionAction: 'retry_delivery' | 'convert_to_takeaway' | 'close_failure',
    resolutionNote?: string
  ) =>
    request<Order>(`/manager/orders/${orderId}/resolve-delivery-failure`, {
      method: 'POST',
      auth: true,
      body: { resolution_action: resolutionAction, resolution_note: resolutionNote },
    }),

  managerProducts: (_role?: UserRole, kind: 'all' | 'primary' | 'secondary' = 'all') =>
    request<ProductApiResponse[]>(`/manager/products?kind=${kind}`, { auth: true }).then((rows) => rows.map(normalizeProduct)),
  managerCategories: (_role?: UserRole) => request<ProductCategory[]>('/manager/categories', { auth: true }),
  managerCreateCategory: (_role: UserRole, payload: ProductCategoryPayload) =>
    request<ProductCategory>('/manager/categories', { method: 'POST', auth: true, body: payload }),
  managerUpdateCategory: (_role: UserRole, categoryId: number, payload: ProductCategoryPayload) =>
    request<ProductCategory>(`/manager/categories/${categoryId}`, { method: 'PUT', auth: true, body: payload }),
  managerDeleteCategory: (_role: UserRole, categoryId: number) =>
    request<void>(`/manager/categories/${categoryId}`, { method: 'DELETE', auth: true }),
  managerProductsPaged: (
    _role: UserRole,
    params: {
      page: number;
      pageSize: number;
      search?: string;
      sortBy?: 'id' | 'name' | 'category' | 'price' | 'available';
      sortDirection?: 'asc' | 'desc';
      archiveState?: 'all' | 'active' | 'archived';
      kind?: 'all' | 'primary' | 'secondary';
    }
  ) => {
    const query = new URLSearchParams({
      page: String(params.page),
      page_size: String(params.pageSize),
      sort_by: params.sortBy ?? 'id',
      sort_direction: params.sortDirection ?? 'desc',
      archive_state: params.archiveState ?? 'all',
      kind: params.kind ?? 'all',
    });
    if (params.search && params.search.trim().length > 0) {
      query.set('search', params.search.trim());
    }
    return request<Omit<ProductsPage, 'items'> & { items: ProductApiResponse[] }>(`/manager/products/paged?${query.toString()}`, { auth: true }).then(
      (page) => ({
        ...page,
        items: page.items.map(normalizeProduct),
      })
    );
  },
  managerCreateProduct: (_role: UserRole, payload: ProductPayload) =>
    request<ProductApiResponse>('/manager/products', { method: 'POST', auth: true, body: payload }).then(normalizeProduct),
  managerUpdateProduct: (_role: UserRole, productId: number, payload: ProductPayload) =>
    request<ProductApiResponse>(`/manager/products/${productId}`, { method: 'PUT', auth: true, body: payload }).then(normalizeProduct),
  managerDeleteProduct: (_role: UserRole, productId: number) =>
    request<void>(`/manager/products/${productId}`, { method: 'DELETE', auth: true }),
  managerDeleteProductPermanently: (_role: UserRole, productId: number) =>
    request<void>(`/manager/products/${productId}/permanent`, { method: 'DELETE', auth: true }),
  managerUploadProductImage: (_role: UserRole, productId: number, payload: ProductImagePayload) =>
    request<ProductApiResponse>(`/manager/products/${productId}/image`, { method: 'POST', auth: true, body: payload }).then(
      normalizeProduct
    ),

  managerDrivers: (_role?: UserRole) => request<DeliveryDriver[]>('/manager/drivers', { auth: true }),
  managerDeliveryProviders: (_role?: UserRole) =>
    request<DeliveryProvider[]>('/manager/delivery/providers', { auth: true }),
  managerDeliveryDispatches: (_role?: UserRole, pageSize?: number) =>
    request<DeliveryDispatch[]>(`/manager/delivery/dispatches${pageSize ? `?page_size=${pageSize}` : ''}`, {
      auth: true,
    }),
  managerCreateDeliveryDispatch: (_role: UserRole, payload: DeliveryDispatchPayload) =>
    request<DeliveryDispatch>('/manager/delivery/dispatches', { method: 'POST', auth: true, body: payload }),
  managerCancelDeliveryDispatch: (_role: UserRole, dispatchId: number) =>
    request<DeliveryDispatch>(`/manager/delivery/dispatches/${dispatchId}/cancel`, {
      method: 'POST',
      auth: true,
    }),
  managerCreateDeliveryProvider: (_role: UserRole, payload: DeliveryProviderPayload) =>
      request<DeliveryProvider>('/manager/delivery/providers', { method: 'POST', auth: true, body: payload }),
  managerUpdateDeliveryProvider: (_role: UserRole, providerId: number, payload: DeliveryProviderPayload) =>
      request<DeliveryProvider>(`/manager/delivery/providers/${providerId}`, { method: 'PUT', auth: true, body: payload }),
  managerDeleteDeliveryProvider: (_role: UserRole, providerId: number) =>
      request<void>(`/manager/delivery/providers/${providerId}`, { method: 'DELETE', auth: true }),
  managerCreateDriver: (_role: UserRole, payload: CreateDriverPayload) =>
      request<DeliveryDriver>('/manager/drivers', { method: 'POST', auth: true, body: payload }),
  managerUpdateDriver: (_role: UserRole, driverId: number, payload: UpdateDriverPayload) =>
      request<DeliveryDriver>(`/manager/drivers/${driverId}`, { method: 'PUT', auth: true, body: payload }),
  managerDeleteDriver: (_role: UserRole, driverId: number) =>
      request<void>(`/manager/drivers/${driverId}`, { method: 'DELETE', auth: true }),
  managerDriverTelegramLinkStatus: (_role: UserRole, driverId: number) =>
      request<DeliveryDriverTelegramLink>(`/manager/drivers/${driverId}/telegram-link`, { auth: true }),
  managerCreateDriverTelegramLink: (_role: UserRole, driverId: number) =>
    request<DeliveryDriverTelegramLink>(`/manager/drivers/${driverId}/telegram-link`, { method: 'POST', auth: true }),
  managerClearDriverTelegramLink: (_role: UserRole, driverId: number) =>
    request<DeliveryDriverTelegramLink>(`/manager/drivers/${driverId}/telegram-link`, { method: 'DELETE', auth: true }),
  managerSendDriverTelegramTestMessage: (_role: UserRole, driverId: number) =>
    request<DeliveryDriverTelegramLink>(`/manager/drivers/${driverId}/telegram-link/test-message`, {
      method: 'POST',
      auth: true,
    }),
  managerResendDriverTelegramFlow: (_role: UserRole, driverId: number) =>
    request<DeliveryDriverTelegramLink>(`/manager/drivers/${driverId}/telegram-link/resend-latest`, {
      method: 'POST',
      auth: true,
    }),
  managerDeliverySettings: (_role?: UserRole) => request<DeliverySettings>('/manager/delivery/settings', { auth: true }),
  managerUpdateDeliverySettings: (_role: UserRole, payload: DeliverySettings) =>
    request<DeliverySettings>('/manager/delivery/settings', { method: 'PUT', auth: true, body: payload }),
  managerSystemContext: (_role?: UserRole) => request<SystemContext>('/manager/settings/system-context', { auth: true }),
  managerUpdateSystemContext: (_role: UserRole, payload: SystemContext) =>
    request<SystemContext>('/manager/settings/system-context', { method: 'PUT', auth: true, body: payload }),
  managerStorefrontSettings: (_role?: UserRole) => request<StorefrontSettings>('/manager/settings/storefront', { auth: true }),
  managerUpdateStorefrontSettings: (_role: UserRole, payload: StorefrontSettings) =>
    request<StorefrontSettings>('/manager/settings/storefront', { method: 'PUT', auth: true, body: payload }),
  managerDeliveryPolicies: (_role?: UserRole) =>
    request<DeliveryPolicies>('/manager/delivery/policies', { auth: true }),
  managerUpdateDeliveryPolicies: (_role: UserRole, payload: DeliveryPolicies) =>
    request<DeliveryPolicies>('/manager/delivery/policies', { method: 'PUT', auth: true, body: payload }),
  managerDeliveryAddressNodes: (_role?: UserRole, parentId?: number) =>
    request<DeliveryAddressNodeList>(
      parentId ? `/manager/delivery/address-nodes?parent_id=${parentId}` : '/manager/delivery/address-nodes',
      { auth: true }
    ),
  managerCreateDeliveryAddressNode: (_role: UserRole, payload: DeliveryAddressNodeCreatePayload) =>
    request<DeliveryAddressNode>('/manager/delivery/address-nodes', { method: 'POST', auth: true, body: payload }),
  managerUpdateDeliveryAddressNode: (_role: UserRole, nodeId: number, payload: DeliveryAddressNodeUpdatePayload) =>
    request<DeliveryAddressNode>(`/manager/delivery/address-nodes/${nodeId}`, {
      method: 'PUT',
      auth: true,
      body: payload,
    }),
  managerDeleteDeliveryAddressNode: (_role: UserRole, nodeId: number) =>
    request<void>(`/manager/delivery/address-nodes/${nodeId}`, { method: 'DELETE', auth: true }),
  managerDeliveryAddressPricing: (_role?: UserRole, params?: { search?: string; activeOnly?: boolean | null }) => {
    const query = new URLSearchParams();
    if (params?.search) {
      query.set('search', params.search);
    }
    if (params?.activeOnly !== undefined && params.activeOnly !== null) {
      query.set('active_only', params.activeOnly ? 'true' : 'false');
    }
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<DeliveryAddressPricingList>(`/manager/delivery/address-pricing${suffix}`, { auth: true });
  },
  managerUpsertDeliveryAddressPricing: (_role: UserRole, payload: DeliveryAddressPricingUpsertPayload) =>
    request<DeliveryAddressPricing>('/manager/delivery/address-pricing', { method: 'PUT', auth: true, body: payload }),
  managerQuoteDeliveryAddressPricing: (_role?: UserRole, nodeId?: number) =>
    request<DeliveryLocationPricingQuote>(
      nodeId ? `/manager/delivery/address-pricing/quote?node_id=${nodeId}` : '/manager/delivery/address-pricing/quote',
      { auth: true }
    ),
  managerDeleteDeliveryAddressPricing: (_role: UserRole, pricingId: number) =>
    request<void>(`/manager/delivery/address-pricing/${pricingId}`, { method: 'DELETE', auth: true }),
  managerUpdateAccountProfile: (_role: UserRole, payload: AccountProfilePayload) =>
    request<User>('/manager/account/profile', { method: 'PUT', auth: true, body: payload }),
  managerAccountSessions: (_role?: UserRole) =>
    request<AccountSession[]>('/manager/account/sessions', { auth: true }),
  managerRevokeAllAccountSessions: (_role: UserRole) =>
    request<AccountSessionsRevokeResult>('/manager/account/sessions/revoke-all', { method: 'POST', auth: true }),
  managerSystemBackups: (_role?: UserRole) =>
    request<SystemBackup[]>('/manager/system/backups', { auth: true }),
  managerCreateSystemBackup: (_role: UserRole) =>
    request<SystemBackup>('/manager/system/backups/create', { method: 'POST', auth: true }),
  managerRestoreSystemBackup: (_role: UserRole, payload: SystemBackupRestorePayload) =>
    request<SystemBackup>('/manager/system/backups/restore', { method: 'POST', auth: true, body: payload }),
  managerNotifyDeliveryTeam: (_role: UserRole, orderId: number) =>
    request<Order>('/manager/delivery/team-notify', {
      method: 'POST',
      auth: true,
      body: { order_id: orderId },
    }),

  managerFinancialTransactions: (_role?: UserRole) =>
    request<FinancialTransaction[]>('/manager/financial/transactions', { auth: true }),
  managerDeliverySettlements: (_role?: UserRole) =>
    request<DeliverySettlement[]>('/manager/financial/delivery-settlements', { auth: true }),
  managerCashboxMovements: (_role?: UserRole) =>
    request<CashboxMovement[]>('/manager/financial/cashbox-movements', { auth: true }),
  managerDeliveryAccountingMigrationStatus: (_role?: UserRole) =>
    request<DeliveryAccountingMigrationStatus>('/manager/financial/migration-status', { auth: true }),
  managerRunDeliveryAccountingBackfill: (
    _role: UserRole,
    payload?: {
      limit?: number;
      dry_run?: boolean;
    }
  ) =>
    request<DeliveryAccountingBackfillResult>('/manager/financial/delivery-accounting-backfill', {
      method: 'POST',
      auth: true,
      body: {
        limit: payload?.limit ?? 100,
        dry_run: payload?.dry_run ?? false,
      },
    }),
  managerShiftClosures: (_role?: UserRole) =>
    request<ShiftClosure[]>('/manager/financial/shift-closures', { auth: true }),
  managerCreateShiftClosure: (_role: UserRole, payload: ShiftClosurePayload) =>
    request<ShiftClosure>('/manager/financial/shift-closures', { method: 'POST', auth: true, body: payload }),

  managerExpenseCostCenters: (_role?: UserRole, includeInactive = false) =>
    request<ExpenseCostCenter[]>(`/manager/expenses/cost-centers?include_inactive=${includeInactive ? 'true' : 'false'}`, {
      auth: true,
    }),
  managerCreateExpenseCostCenter: (_role: UserRole, payload: ExpenseCostCenterPayload) =>
    request<ExpenseCostCenter>('/manager/expenses/cost-centers', { method: 'POST', auth: true, body: payload }),
  managerUpdateExpenseCostCenter: (_role: UserRole, centerId: number, payload: ExpenseCostCenterPayload) =>
    request<ExpenseCostCenter>(`/manager/expenses/cost-centers/${centerId}`, {
      method: 'PUT',
      auth: true,
      body: payload,
    }),
  managerExpenses: (_role?: UserRole) => request<Expense[]>('/manager/expenses', { auth: true }),
  managerCreateExpense: (_role: UserRole, payload: ExpensePayload) =>
    request<Expense>('/manager/expenses', { method: 'POST', auth: true, body: payload }),
  managerUpdateExpense: (_role: UserRole, expenseId: number, payload: ExpensePayload) =>
    request<Expense>(`/manager/expenses/${expenseId}`, { method: 'PUT', auth: true, body: payload }),
  managerApproveExpense: (_role: UserRole, expenseId: number, payload?: ExpenseReviewPayload) =>
    request<Expense>(`/manager/expenses/${expenseId}/approve`, {
      method: 'POST',
      auth: true,
      body: payload ?? {},
    }),
  managerRejectExpense: (_role: UserRole, expenseId: number, payload?: ExpenseReviewPayload) =>
    request<Expense>(`/manager/expenses/${expenseId}/reject`, {
      method: 'POST',
      auth: true,
      body: payload ?? {},
    }),
  managerCreateExpenseAttachment: (_role: UserRole, expenseId: number, payload: ExpenseAttachmentPayload) =>
    request<ExpenseAttachment>(`/manager/expenses/${expenseId}/attachments`, {
      method: 'POST',
      auth: true,
      body: payload,
    }),
  managerDeleteExpenseAttachment: (_role: UserRole, expenseId: number, attachmentId: number) =>
    request<void>(`/manager/expenses/${expenseId}/attachments/${attachmentId}`, {
      method: 'DELETE',
      auth: true,
    }),
  managerDeleteExpense: (_role: UserRole, expenseId: number) =>
    request<void>(`/manager/expenses/${expenseId}`, { method: 'DELETE', auth: true }),

  managerReportsDaily: (_role?: UserRole) => request<ReportDailyRow[]>('/manager/reports/daily', { auth: true }),
  managerReportsMonthly: (_role?: UserRole) => request<ReportMonthlyRow[]>('/manager/reports/monthly', { auth: true }),
  managerReportsByType: (_role?: UserRole) => request<ReportByTypeRow[]>('/manager/reports/by-order-type', { auth: true }),
  managerReportsPerformance: (_role?: UserRole) => request<ReportPerformance>('/manager/reports/performance', { auth: true }),
  managerReportsProfitability: (
    _role?: UserRole,
    params?: {
      startDate?: string;
      endDate?: string;
    }
  ) => {
    const query = new URLSearchParams();
    if (params?.startDate) {
      query.set('start_date', params.startDate);
    }
    if (params?.endDate) {
      query.set('end_date', params.endDate);
    }
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<ReportProfitability>(`/manager/reports/profitability${suffix}`, { auth: true });
  },
  managerReportsPeriodComparison: (
    _role?: UserRole,
    params?: {
      startDate?: string;
      endDate?: string;
    }
  ) => {
    const query = new URLSearchParams();
    if (params?.startDate) {
      query.set('start_date', params.startDate);
    }
    if (params?.endDate) {
      query.set('end_date', params.endDate);
    }
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<ReportPeriodComparison>(`/manager/reports/period-comparison${suffix}`, { auth: true });
  },
  managerReportsPeakHoursPerformance: (
    _role?: UserRole,
    params?: {
      startDate?: string;
      endDate?: string;
    }
  ) => {
    const query = new URLSearchParams();
    if (params?.startDate) {
      query.set('start_date', params.startDate);
    }
    if (params?.endDate) {
      query.set('end_date', params.endDate);
    }
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<ReportPeakHoursPerformance>(`/manager/reports/peak-hours-performance${suffix}`, { auth: true });
  },

  managerWarehouseDashboard: (_role?: UserRole) =>
    request<WarehouseDashboard>('/manager/warehouse/dashboard', { auth: true }),
  managerWarehouseSuppliers: (_role?: UserRole) =>
    request<WarehouseSupplier[]>('/manager/warehouse/suppliers', { auth: true }),
  managerCreateWarehouseSupplier: (_role: UserRole, payload: WarehouseSupplierPayload) =>
    request<WarehouseSupplier>('/manager/warehouse/suppliers', { method: 'POST', auth: true, body: payload }),
  managerUpdateWarehouseSupplier: (_role: UserRole, supplierId: number, payload: WarehouseSupplierPayload) =>
    request<WarehouseSupplier>(`/manager/warehouse/suppliers/${supplierId}`, {
      method: 'PUT',
      auth: true,
      body: payload,
    }),
  managerWarehouseItems: (_role?: UserRole) =>
    request<WarehouseItem[]>('/manager/warehouse/items', { auth: true }),
  managerCreateWarehouseItem: (_role: UserRole, payload: WarehouseItemPayload) =>
    request<WarehouseItem>('/manager/warehouse/items', { method: 'POST', auth: true, body: payload }),
  managerUpdateWarehouseItem: (_role: UserRole, itemId: number, payload: WarehouseItemPayload) =>
    request<WarehouseItem>(`/manager/warehouse/items/${itemId}`, {
      method: 'PUT',
      auth: true,
      body: payload,
    }),
  managerWarehouseBalances: (_role?: UserRole, onlyLow = false) =>
    request<WarehouseStockBalance[]>(`/manager/warehouse/balances?only_low=${onlyLow ? 'true' : 'false'}`, {
      auth: true,
    }),
  managerWarehouseLedger: (
    _role?: UserRole,
    params?: {
      limit?: number;
      itemId?: number;
      movementKind?: 'inbound' | 'outbound';
    }
  ) => {
    const query = new URLSearchParams();
    query.set('limit', String(params?.limit ?? 200));
    if (params?.itemId) {
      query.set('item_id', String(params.itemId));
    }
    if (params?.movementKind) {
      query.set('movement_kind', params.movementKind);
    }
    return request<WarehouseLedgerRow[]>(`/manager/warehouse/ledger?${query.toString()}`, { auth: true });
  },
  managerWarehouseInboundVouchers: (_role?: UserRole, limit = 100) =>
    request<WarehouseInboundVoucher[]>(`/manager/warehouse/inbound-vouchers?limit=${limit}`, { auth: true }),
  managerCreateWarehouseInboundVoucher: (_role: UserRole, payload: WarehouseInboundVoucherPayload) =>
    request<WarehouseInboundVoucher>('/manager/warehouse/inbound-vouchers', {
      method: 'POST',
      auth: true,
      body: payload,
    }),
  managerWarehouseOutboundVouchers: (_role?: UserRole, limit = 100) =>
    request<WarehouseOutboundVoucher[]>(`/manager/warehouse/outbound-vouchers?limit=${limit}`, { auth: true }),
  managerWarehouseOutboundReasons: (_role?: UserRole) =>
    request<WarehouseOutboundReason[]>('/manager/warehouse/outbound-reasons', { auth: true }),
  managerCreateWarehouseOutboundVoucher: (_role: UserRole, payload: WarehouseOutboundVoucherPayload) =>
    request<WarehouseOutboundVoucher>('/manager/warehouse/outbound-vouchers', {
      method: 'POST',
      auth: true,
      body: payload,
    }),
  managerWarehouseStockCounts: (_role?: UserRole, limit = 100) =>
    request<WarehouseStockCount[]>(`/manager/warehouse/stock-counts?limit=${limit}`, { auth: true }),
  managerCreateWarehouseStockCount: (_role: UserRole, payload: WarehouseStockCountPayload) =>
    request<WarehouseStockCount>('/manager/warehouse/stock-counts', {
      method: 'POST',
      auth: true,
      body: payload,
    }),
  managerSettleWarehouseStockCount: (_role: UserRole, countId: number) =>
    request<WarehouseStockCount>(`/manager/warehouse/stock-counts/${countId}/settle`, {
      method: 'POST',
      auth: true,
    }),

  managerUsers: (_role?: UserRole) => request<User[]>('/manager/users', { auth: true }),
  managerPermissionsCatalog: (_role: UserRole, targetRole?: UserRole) => {
    const query = targetRole ? `?role=${targetRole}` : '';
    return request<PermissionCatalogItem[]>(`/manager/users/permissions/catalog${query}`, { auth: true });
  },
  managerUserPermissions: (_role: UserRole, userId: number) =>
    request<UserPermissionsProfile>(`/manager/users/${userId}/permissions`, { auth: true }),
  managerUpdateUserPermissions: (_role: UserRole, userId: number, payload: UserPermissionsUpdatePayload) =>
    request<UserPermissionsProfile>(`/manager/users/${userId}/permissions`, {
      method: 'PUT',
      auth: true,
      body: payload,
    }),
  managerCreateUser: (_role: UserRole, payload: UserPayload) =>
    request<User>('/manager/users', { method: 'POST', auth: true, body: payload }),
  managerUpdateUser: (_role: UserRole, userId: number, payload: UserPayload) =>
    request<User>(`/manager/users/${userId}`, { method: 'PUT', auth: true, body: payload }),
  managerDeleteUser: (_role: UserRole, userId: number) =>
    request<void>(`/manager/users/${userId}`, { method: 'DELETE', auth: true }),

  managerAuditLogs: (_role?: UserRole) => request<OrderTransitionLog[]>('/manager/audit/orders', { auth: true }),
  managerAuditSystemLogs: (_role?: UserRole) => request<SystemAuditLog[]>('/manager/audit/system', { auth: true }),
  managerAuditSecurityEvents: (_role?: UserRole) => request<SecurityAuditEvent[]>('/manager/audit/security', { auth: true }),

  kitchenOrdersPaged: (
    _role: UserRole,
    params: {
      page: number;
      pageSize: number;
      scope?: 'active' | 'history';
      search?: string;
      sortBy?: 'created_at' | 'total' | 'status' | 'id';
      sortDirection?: 'asc' | 'desc';
    }
  ) => {
    const query = new URLSearchParams({
      page: String(params.page),
      page_size: String(params.pageSize),
      scope: params.scope ?? 'active',
      sort_by: params.sortBy ?? 'created_at',
      sort_direction: params.sortDirection ?? 'asc',
    });
    if (params.search && params.search.trim().length > 0) {
      query.set('search', params.search.trim());
    }
    return request<KitchenOrdersPage>(`/kitchen/orders/paged?${query.toString()}`, { auth: true });
  },
  kitchenRuntimeSettings: (_role?: UserRole) =>
    request<KitchenRuntimeSettings>('/kitchen/runtime-settings', { auth: true }),
  kitchenStartOrder: (_role: UserRole, orderId: number) =>
    request<Order>(`/kitchen/orders/${orderId}/start`, { method: 'POST', auth: true }),
  kitchenReadyOrder: (_role: UserRole, orderId: number) =>
    request<Order>(`/kitchen/orders/${orderId}/ready`, { method: 'POST', auth: true }),

  deliveryAssignments: (_role?: UserRole, pageSize?: number) =>
    request<DeliveryAssignment[]>(`/delivery/assignments${pageSize ? `?page_size=${pageSize}` : ''}`, { auth: true }),
  deliveryDispatches: (_role?: UserRole, pageSize?: number) =>
    request<DeliveryDispatch[]>(`/delivery/dispatches${pageSize ? `?page_size=${pageSize}` : ''}`, { auth: true }),
  deliveryTeamDrivers: (_role?: UserRole) => request<DeliveryDriver[]>('/delivery/team/drivers', { auth: true }),
  deliveryOrders: (_role?: UserRole, pageSize?: number) =>
    request<Order[]>(`/delivery/orders${pageSize ? `?page_size=${pageSize}` : ''}`, { auth: true }),
  deliveryHistory: (_role?: UserRole) => request<DeliveryHistoryRow[]>('/delivery/history', { auth: true }),
  deliveryAssignDispatchToDriver: (_role: UserRole, dispatchId: number, driverId: number) =>
    request<DeliveryDispatch>(`/delivery/dispatches/${dispatchId}/assign-driver`, {
      method: 'POST',
      auth: true,
      body: { driver_id: driverId },
    }),
  deliveryClaim: (_role: UserRole, orderId: number) =>
    request<DeliveryAssignment>(`/delivery/orders/${orderId}/claim`, { method: 'POST', auth: true }),
  deliveryRejectDispatch: (_role: UserRole, dispatchId: number) =>
    request<DeliveryDispatch>(`/delivery/dispatches/${dispatchId}/reject`, { method: 'POST', auth: true }),
  deliveryDepart: (_role: UserRole, orderId: number) =>
    request<Order>(`/delivery/orders/${orderId}/depart`, { method: 'POST', auth: true }),
  deliveryDelivered: (_role: UserRole, orderId: number, amountReceived?: number) =>
    request<Order>(`/delivery/orders/${orderId}/delivered`, {
      method: 'POST',
      auth: true,
      body: { target_status: 'DELIVERED', amount_received: amountReceived },
    }),
  deliveryFailed: (_role: UserRole, orderId: number) =>
    request<Order>(`/delivery/orders/${orderId}/failed`, { method: 'POST', auth: true }),
};
