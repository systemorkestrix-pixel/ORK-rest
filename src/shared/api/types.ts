export type UserRole = 'manager' | 'kitchen' | 'delivery';

export type ProductKind = 'primary' | 'secondary';
export type LegacyProductKind = 'sellable' | 'internal';
export type OrderType = 'dine-in' | 'takeaway' | 'delivery';

export type OrderStatus =
  | 'CREATED'
  | 'CONFIRMED'
  | 'SENT_TO_KITCHEN'
  | 'IN_PREPARATION'
  | 'READY'
  | 'OUT_FOR_DELIVERY'
  | 'DELIVERED'
  | 'DELIVERY_FAILED'
  | 'CANCELED';

export type OrderPaymentStatus = 'unpaid' | 'paid' | 'refunded';
export type DeliveryFailureResolutionAction = 'retry_delivery' | 'convert_to_takeaway' | 'close_failure';

export interface User {
  id: number;
  name: string;
  username: string;
  role: UserRole;
  active?: boolean;
  permissions_effective?: string[];
}

export interface PermissionCatalogItem {
  code: string;
  label: string;
  description: string;
  roles: UserRole[];
  default_enabled: boolean;
}

export interface UserPermissionsProfile {
  user_id: number;
  username: string;
  role: UserRole;
  default_permissions: string[];
  allow_overrides: string[];
  deny_overrides: string[];
  effective_permissions: string[];
}

export interface AccountSession {
  id: number;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  is_active: boolean;
}

export interface AccountSessionsRevokeResult {
  revoked_count: number;
}

export interface SystemBackup {
  filename: string;
  size_bytes: number;
  created_at: string;
}

export interface AuthSession {
  user: User;
  token_type: string;
}

export interface MasterIdentity {
  username: string;
  display_name: string;
  role_label: string;
}

export interface MasterSession {
  identity: MasterIdentity;
  token_type: string;
}

export interface MasterOverviewStat {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: 'emerald' | 'cyan' | 'amber' | 'violet';
  icon_key: 'clients' | 'tenants' | 'addons' | 'disabled';
}

export interface MasterSignal {
  label: string;
  value: string;
}

export interface MasterOperatingMode {
  key: string;
  label: string;
  detail: string;
  tone: 'visible' | 'hidden' | 'disabled';
}

export interface MasterLatestTenant {
  tenant_id: string;
  brand_name: string;
  code: string;
  activation_stage_name: string;
}

export interface MasterOverview {
  stats: MasterOverviewStat[];
  signals: MasterSignal[];
  operating_modes: MasterOperatingMode[];
  base_clients_count: number;
  latest_tenants: MasterLatestTenant[];
}

export interface MasterAddonCapability {
  key: string;
  label: string;
  status: 'locked' | 'passive' | 'active' | 'paused';
  mode: 'core' | 'runtime_hidden' | 'disabled';
  detail: string;
}

export interface MasterAddon {
  id: string;
  sequence: number;
  name: string;
  description: string;
  unlock_note: string;
  target: string;
  prerequisite_id: string | null;
  prerequisite_label: string | null;
  status: 'locked' | 'passive' | 'active' | 'paused';
  can_activate_now: boolean;
  purchase_state: 'owned' | 'next' | 'later';
  paypal_checkout_url: string | null;
  telegram_checkout_url: string | null;
  capabilities: MasterAddonCapability[];
}

export interface MasterClient {
  id: string;
  owner_name: string;
  brand_name: string;
  phone: string;
  city: string;
  current_stage_id: string;
  current_stage_name: string;
  subscription_state: 'active' | 'trial' | 'paused';
  next_billing_date: string;
}

export interface MasterTenant {
  id: string;
  code: string;
  brand_name: string;
  client_id: string;
  client_owner_name: string;
  client_brand_name: string;
  database_name: string;
  manager_username: string;
  environment_state: 'ready' | 'pending_activation' | 'suspended';
  enabled_tools: string[];
  hidden_tools: string[];
  locked_tools: string[];
  paused_tools: string[];
  current_stage_id: string;
  current_stage_name: string;
  next_addon_id: string | null;
  next_addon_name: string | null;
  manager_login_path: string;
  public_order_path: string;
}

export interface MasterTenantCreatePayload {
  client_mode: 'existing' | 'new';
  existing_client_id?: string | null;
  client_owner_name?: string | null;
  client_brand_name?: string | null;
  client_phone?: string | null;
  client_city?: string | null;
  tenant_brand_name: string;
  tenant_code?: string | null;
  database_name?: string | null;
}

export interface MasterTenantUpdatePayload {
  client_owner_name: string;
  client_brand_name: string;
  client_phone: string;
  client_city: string;
  brand_name: string;
  activation_stage_id: string;
}

export interface MasterTenantAccess {
  login_path: string;
  manager_username: string;
  manager_password: string;
}

export interface MasterTenantCreateResult {
  client: MasterClient;
  tenant: MasterTenant;
  activation_stage: MasterAddon;
  access: MasterTenantAccess;
}

export interface TenantEntry {
  tenant_id: string;
  tenant_code: string;
  tenant_brand_name: string;
  client_brand_name: string;
  client_owner_name: string;
  manager_login_path: string;
  public_order_path: string;
  public_menu_path: string;
}

export interface ManagerTenantContext {
  tenant_id: string | null;
  tenant_code: string | null;
  tenant_brand_name: string | null;
  database_name: string | null;
  activation_stage_id: string;
  activation_stage_name: string;
  channel_modes: Record<string, 'core' | 'runtime_hidden' | 'disabled'>;
  section_modes: Record<string, 'core' | 'runtime_hidden' | 'disabled'>;
}

export interface ManagerKitchenAccess {
  login_path: string;
  username: string;
  password: string;
  account_ready: boolean;
}

export type RestaurantEmployeeType =
  | 'cook'
  | 'kitchen_assistant'
  | 'delivery_staff'
  | 'courier'
  | 'warehouse_keeper'
  | 'cashier'
  | 'service_staff'
  | 'admin_staff';

export type RestaurantEmployeeCompensationCycle = 'monthly' | 'weekly' | 'daily' | 'hourly';

export interface RestaurantEmployee {
  id: number;
  name: string;
  employee_type: RestaurantEmployeeType;
  phone: string | null;
  compensation_cycle: RestaurantEmployeeCompensationCycle;
  compensation_amount: number;
  work_schedule: string | null;
  notes: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RestaurantEmployeePayload {
  name: string;
  employee_type: RestaurantEmployeeType;
  phone?: string | null;
  compensation_cycle: RestaurantEmployeeCompensationCycle;
  compensation_amount: number;
  work_schedule?: string | null;
  notes?: string | null;
  active: boolean;
}

export interface ProductSecondaryLink {
  id?: number;
  primary_product_id?: number;
  secondary_product_id: number;
  secondary_product_name?: string;
  sort_order: number;
  is_default: boolean;
  max_quantity: number;
}

export interface ProductConsumptionComponent {
  id?: number;
  product_id?: number;
  warehouse_item_id: number;
  warehouse_item_name?: string;
  warehouse_item_unit?: string;
  quantity_per_unit: number;
}

export interface Product {
  id: number;
  name: string;
  description?: string | null;
  price: number;
  kind: ProductKind;
  legacy_kind?: LegacyProductKind | null;
  available: boolean;
  category: string;
  category_id?: number | null;
  image_path?: string | null;
  is_archived?: boolean;
  secondary_links: ProductSecondaryLink[];
  consumption_components: ProductConsumptionComponent[];
}

export interface ProductApiResponse extends Omit<Product, 'kind' | 'secondary_links' | 'consumption_components' | 'legacy_kind'> {
  kind: ProductKind | LegacyProductKind;
  normalized_kind?: ProductKind | null;
  secondary_links?: ProductSecondaryLink[];
  consumption_components?: ProductConsumptionComponent[];
}

export interface PublicProduct {
  id: number;
  name: string;
  description?: string | null;
  price: number;
  category: string;
  image_path?: string | null;
}

export interface PublicSecondaryOption {
  product_id: number;
  name: string;
  description?: string | null;
  price: number;
  image_path?: string | null;
  sort_order: number;
  is_default: boolean;
  max_quantity: number;
}

export interface PublicJourneyProduct {
  id: number;
  name: string;
  description?: string | null;
  price: number;
  category: string;
  image_path?: string | null;
  secondary_options: PublicSecondaryOption[];
}

export interface PublicJourneyCategory {
  name: string;
  products: PublicJourneyProduct[];
}

export interface PublicJourneyCatalog {
  categories: PublicJourneyCategory[];
  secondary_products: PublicSecondaryOption[];
}

export interface PublicOrderJourneyMeta {
  journey_version: string;
  generated_at: string;
}

export interface PublicJourneyDelivery {
  delivery_fee: number;
  min_order_amount: number;
  pricing_mode: string;
  structured_locations_enabled: boolean;
  zones_configured: boolean;
}

export interface PublicJourneyTableContext {
  table_id?: number | null;
  has_table_context: boolean;
  has_active_session: boolean;
  table_status?: TableInfo['status'] | null;
  total_orders: number;
  active_orders_count: number;
  unsettled_orders_count: number;
  unpaid_total: number;
  latest_order_status: OrderStatus | null;
}

export interface PublicJourneyRules {
  allowed_order_types: OrderType[];
  default_order_type: OrderType;
  workflow_profile: PublicWorkflowProfile;
  require_phone_for_takeaway: boolean;
  require_phone_for_delivery: boolean;
  require_address_for_delivery: boolean;
  allow_manual_table_selection: boolean;
}

export interface PublicOrderJourneyBootstrap {
  meta: PublicOrderJourneyMeta;
  catalog: PublicJourneyCatalog;
  capabilities: OperationalCapabilities;
  delivery: PublicJourneyDelivery;
  table_context: PublicJourneyTableContext;
  journey_rules: PublicJourneyRules;
}

export interface TableInfo {
  id: number;
  qr_code: string;
  status: 'available' | 'occupied' | 'reserved';
}

export interface ManagerTable extends TableInfo {
  total_orders_count: number;
  has_active_session: boolean;
  active_orders_count: number;
  unsettled_orders_count: number;
  unpaid_total: number;
}

export interface OrderItem {
  id: number;
  product_id: number;
  quantity: number;
  price: number;
  product_name: string;
}

export interface Order {
  id: number;
  tracking_code: string;
  type: OrderType;
  status: OrderStatus;
  table_id: number | null;
  phone: string | null;
  address: string | null;
  delivery_location_key?: string | null;
  delivery_location_label?: string | null;
  delivery_location_level?: string | null;
  subtotal: number;
  delivery_fee: number;
  total: number;
  created_at: string;
  notes: string | null;
  payment_status?: OrderPaymentStatus;
  paid_at?: string | null;
  paid_by?: number | null;
  amount_received?: number | null;
  change_amount?: number | null;
  payment_method?: string;
  delivery_team_notified_at?: string | null;
  delivery_team_notified_by?: number | null;
  delivery_failure_resolution_status?: DeliveryFailureResolutionAction | null;
  delivery_failure_resolution_note?: string | null;
  delivery_failure_resolved_at?: string | null;
  delivery_failure_resolved_by?: number | null;
  sent_to_kitchen_at?: string | null;
  delivery_settlement_id?: number | null;
  delivery_settlement_status?: string | null;
  delivery_settlement_remaining_store_due_amount?: number | null;
  delivery_assignment_status?: string | null;
  delivery_assignment_driver_id?: number | null;
  delivery_assignment_driver_name?: string | null;
  delivery_assignment_assigned_at?: string | null;
  delivery_assignment_departed_at?: string | null;
  delivery_assignment_delivered_at?: string | null;
  delivery_dispatch_id?: number | null;
  delivery_dispatch_status?: DeliveryDispatchStatus | null;
  delivery_dispatch_scope?: DeliveryDispatchScope | null;
  delivery_dispatch_provider_id?: number | null;
  delivery_dispatch_provider_name?: string | null;
  delivery_dispatch_driver_id?: number | null;
  delivery_dispatch_driver_name?: string | null;
  delivery_dispatch_sent_at?: string | null;
  delivery_dispatch_responded_at?: string | null;
  items: OrderItem[];
}

export interface PublicOrderTracking {
  tracking_code: string;
  type: OrderType;
  status: OrderStatus;
  workflow_profile: PublicWorkflowProfile;
  payment_status?: OrderPaymentStatus;
  created_at: string;
  subtotal: number;
  delivery_fee: number;
  total: number;
  notes?: string | null;
  items: OrderItem[];
}

export type PublicWorkflowProfile = 'kitchen_managed' | 'direct_fulfillment' | 'direct_delivery';
export type OperationalWorkflowProfile = 'base_direct' | 'kitchen_managed' | 'kitchen_delivery_managed';

export interface TableSession {
  table: TableInfo;
  has_active_session: boolean;
  total_orders: number;
  active_orders_count: number;
  unsettled_orders_count: number;
  unpaid_total: number;
  latest_order_status: OrderStatus | null;
  orders: Order[];
}

export interface TableSessionSettlement {
  table_id: number;
  settled_order_ids: number[];
  settled_total: number;
  amount_received: number;
  change_amount: number;
  table_status: TableInfo['status'];
}

export interface OrdersPage {
  items: Order[];
  total: number;
  page: number;
  page_size: number;
}

export interface KitchenMonitorSummary {
  sent_to_kitchen: number;
  in_preparation: number;
  ready: number;
  oldest_order_wait_seconds: number;
  metrics_window: 'day' | 'week' | 'month';
  avg_prep_minutes_today: number;
  warehouse_issued_quantity_today: number;
  warehouse_issue_vouchers_today: number;
  warehouse_issued_items_today: number;
}

export interface KitchenOrdersPage extends OrdersPage {
  scope: 'active' | 'history';
  summary: KitchenMonitorSummary;
}

export interface KitchenRuntimeSettings {
  order_polling_ms: number;
  kitchen_metrics_window: 'day' | 'week' | 'month';
}

export interface DashboardStats {
  created: number;
  confirmed: number;
  sent_to_kitchen: number;
  in_preparation: number;
  ready: number;
  out_for_delivery?: number;
  delivered: number;
  delivery_failed?: number;
  canceled: number;
  active_orders: number;
  today_sales?: number;
  today_expenses?: number;
  today_net?: number;
}

export interface OperationalHeartMeta {
  generated_at: string;
  local_business_date: string;
  refresh_recommended_ms: number;
  contract_version?: string;
}

export interface OperationalHeartCapabilities {
  kitchen_feature_enabled: boolean;
  delivery_feature_enabled: boolean;
  kitchen_runtime_enabled: boolean;
  delivery_runtime_enabled: boolean;
  kitchen_enabled: boolean;
  delivery_enabled: boolean;
  kitchen_active_users: number;
  delivery_active_users: number;
  kitchen_block_reason?: string | null;
  delivery_block_reason?: string | null;
}

export interface OperationalHeartKpis {
  active_orders: number;
  kitchen_active_orders: number;
  delivery_active_orders: number;
  ready_orders: number;
  today_sales: number;
  today_expenses: number;
  today_net: number;
  avg_prep_minutes_today: number;
  oldest_kitchen_wait_seconds: number;
}

export interface OperationalHeartQueue {
  key: string;
  label: string;
  count: number;
  oldest_age_seconds: number;
  aged_over_sla_count: number;
  sla_seconds: number;
  action_route: string;
}

export interface OperationalHeartIncident {
  code: string;
  severity: 'critical' | 'warning' | 'info' | string;
  title: string;
  message: string;
  count: number;
  oldest_age_seconds?: number | null;
  action_route: string;
}

export interface OperationalHeartTimelineItem {
  timestamp: string;
  domain: string;
  title: string;
  description: string;
  action_route?: string | null;
  order_id?: number | null;
  entity_id?: number | null;
}

export interface OperationalHeartFinancialControl {
  severity: 'critical' | 'warning' | 'info' | string;
  action_route: string;
  shift_closed_today: boolean;
  latest_shift_variance: number;
  sales_transactions_today: number;
  expense_transactions_today: number;
  today_net: number;
}

export interface OperationalHeartWarehouseControl {
  severity: 'critical' | 'warning' | 'info' | string;
  action_route: string;
  active_items: number;
  low_stock_items: number;
  pending_stock_counts: number;
  inbound_today: number;
  outbound_today: number;
}

export interface OperationalHeartTablesControl {
  severity: 'critical' | 'warning' | 'info' | string;
  action_route: string;
  active_sessions: number;
  blocked_settlement_tables: number;
  unpaid_orders: number;
  unpaid_total: number;
}

export interface OperationalHeartExpensesControl {
  severity: 'critical' | 'warning' | 'info' | string;
  action_route: string;
  pending_approvals: number;
  pending_amount: number;
  rejected_today: number;
  high_value_pending_amount: number;
}

export interface OperationalHeartReconciliation {
  key: string;
  label: string;
  ok: boolean;
  severity: 'critical' | 'warning' | 'info' | string;
  detail: string;
  action_route: string;
}

export interface OperationalHeartDashboard {
  meta: OperationalHeartMeta;
  capabilities: OperationalHeartCapabilities;
  kpis: OperationalHeartKpis;
  queues: OperationalHeartQueue[];
  incidents: OperationalHeartIncident[];
  timeline: OperationalHeartTimelineItem[];
  financial_control?: OperationalHeartFinancialControl;
  warehouse_control?: OperationalHeartWarehouseControl;
  tables_control?: OperationalHeartTablesControl;
  expenses_control?: OperationalHeartExpensesControl;
  reconciliations?: OperationalHeartReconciliation[];
}

export interface LoginPayload {
  username: string;
  password: string;
  role: UserRole;
}

export interface CreateOrderPayload {
  type: OrderType;
  table_id?: number;
  phone?: string;
  address?: string;
  delivery_location_key?: string;
  notes?: string;
  items: Array<{
    product_id: number;
    quantity: number;
  }>;
}

export interface DeliveryAddressNode {
  id: number;
  parent_id: number | null;
  level: 'admin_area_level_1' | 'admin_area_level_2' | 'locality' | 'sublocality' | string;
  country_code: string;
  code: string;
  name: string;
  display_name: string;
  postal_code?: string | null;
  notes?: string | null;
  active: boolean;
  visible_in_public: boolean;
  sort_order: number;
  child_count: number;
  can_expand: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeliveryAddressNodeList {
  parent_id: number | null;
  items: DeliveryAddressNode[];
  total: number;
}

export interface DeliveryLocationPricingQuote {
  selected_node_id: number | null;
  location_key: string | null;
  location_label: string | null;
  location_level: string | null;
  resolved_node_id: number | null;
  resolved_node_label: string | null;
  resolved_node_level: string | null;
  available: boolean;
  pricing_source: string;
  delivery_fee: number | null;
  active_zones_count: number;
  message: string | null;
}

export interface ProductPayload {
  name: string;
  description?: string | null;
  price: number;
  kind: ProductKind;
  category_id?: number | null;
  available: boolean;
  is_archived?: boolean;
  secondary_links?: Array<{
    secondary_product_id: number;
    sort_order: number;
    is_default: boolean;
    max_quantity: number;
  }>;
  consumption_components?: Array<{
    warehouse_item_id: number;
    quantity_per_unit: number;
  }>;
}

export interface ProductCategory {
  id: number;
  name: string;
  active: boolean;
  sort_order: number;
}

export interface ProductsPage {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export interface DeliveryDriver {
  id: number;
  user_id?: number | null;
  provider_id?: number | null;
  provider_name?: string | null;
  provider_type?: string | null;
  name: string;
  phone: string;
  status: 'available' | 'busy' | 'inactive';
  vehicle?: string | null;
  active: boolean;
  telegram_enabled?: boolean;
  telegram_username?: string | null;
  telegram_chat_id?: string | null;
  telegram_linked_at?: string | null;
  telegram_link_code?: string | null;
  telegram_link_expires_at?: string | null;
  can_delete?: boolean;
  delete_block_reason?: string | null;
  recommended_management_action?: 'delete' | 'deactivate' | 'configure_only' | string | null;
}

export interface DeliveryProvider {
  id: number;
  account_user_id?: number | null;
  account_user_name?: string | null;
  account_username?: string | null;
  name: string;
  provider_type: 'internal_team' | 'partner_company' | string;
  active: boolean;
  is_internal_default: boolean;
  created_at: string;
  can_delete?: boolean;
  delete_block_reason?: string | null;
  recommended_management_action?: 'delete' | 'deactivate' | 'configure_only' | string | null;
}

export interface DeliveryAssignment {
  id: number;
  order_id: number;
  driver_id: number;
  assigned_at: string;
  departed_at?: string | null;
  delivered_at?: string | null;
  status: 'notified' | 'assigned' | 'departed' | 'delivered' | 'failed';
}

export type DeliveryDispatchStatus = 'offered' | 'accepted' | 'rejected' | 'canceled';
export type DeliveryDispatchScope = 'driver' | 'provider';

export interface DeliveryDispatch {
  id: number;
  order_id: number;
  provider_id?: number | null;
  provider_name?: string | null;
  driver_id?: number | null;
  driver_name?: string | null;
  dispatch_scope: DeliveryDispatchScope;
  status: DeliveryDispatchStatus;
  channel: string;
  sent_at: string;
  responded_at?: string | null;
  expires_at?: string | null;
  created_by?: number | null;
}

export interface SystemContext {
  country_code: string;
  country_name: string;
  currency_code: string;
  currency_name: string;
  currency_symbol: string;
  currency_decimal_places: number;
}

export type StorefrontIconKey = 'utensils' | 'chef_hat' | 'shopping_bag' | 'bike';
export type StorefrontSocialPlatform = 'website' | 'whatsapp' | 'instagram' | 'facebook';

export interface StorefrontSocialLink {
  platform: StorefrontSocialPlatform;
  url?: string | null;
  enabled: boolean;
}

export interface StorefrontSettings {
  brand_name: string;
  brand_mark: string;
  brand_icon: StorefrontIconKey;
  brand_tagline?: string | null;
  socials: StorefrontSocialLink[];
}

export interface TelegramBotSettings {
  enabled: boolean;
  bot_token?: string | null;
  bot_username?: string | null;
  webhook_secret: string;
}

export type TelegramBotHealthStatus = 'healthy' | 'warning' | 'error';

export interface TelegramBotHealth {
  enabled: boolean;
  token_configured: boolean;
  username_configured: boolean;
  webhook_secret_configured: boolean;
  bot_api_ok: boolean;
  bot_id?: number | null;
  bot_username?: string | null;
  webhook_ok: boolean;
  webhook_url?: string | null;
  webhook_expected_path?: string | null;
  webhook_path_matches: boolean;
  pending_update_count: number;
  last_error_message?: string | null;
  last_error_at?: string | null;
  issues: string[];
  status: TelegramBotHealthStatus;
}

export interface DeliveryDriverTelegramLink {
  driver_id: number;
  driver_name: string;
  linked: boolean;
  telegram_enabled: boolean;
  provider_name?: string | null;
  telegram_username?: string | null;
  telegram_chat_id?: string | null;
  telegram_linked_at?: string | null;
  link_code?: string | null;
  link_expires_at?: string | null;
  bot_username?: string | null;
  deep_link?: string | null;
  has_active_task: boolean;
  active_order_id?: number | null;
  active_order_status?: string | null;
  has_open_offer: boolean;
  offered_order_id?: number | null;
  offered_order_status?: string | null;
  recovery_hint?: string | null;
  action_message?: string | null;
}

export interface DeliverySettings {
  delivery_fee: number;
  pricing_mode?: string;
  structured_locations_enabled?: boolean;
  active_zones_count?: number;
  system_context?: SystemContext;
}

export interface DeliveryPolicies {
  min_order_amount: number;
  auto_notify_team: boolean;
}

export interface DeliveryAddressNodeCreatePayload {
  parent_id?: number | null;
  level: 'admin_area_level_1' | 'admin_area_level_2' | 'locality' | 'sublocality' | string;
  code: string;
  name: string;
  display_name: string;
  postal_code?: string | null;
  notes?: string | null;
  active: boolean;
  visible_in_public: boolean;
  sort_order: number;
}

export interface DeliveryAddressNodeUpdatePayload {
  code: string;
  name: string;
  display_name: string;
  postal_code?: string | null;
  notes?: string | null;
  active: boolean;
  visible_in_public: boolean;
  sort_order: number;
}

export interface DeliveryAddressPricing {
  id: number;
  node_id: number;
  provider: string;
  location_key: string;
  parent_key?: string | null;
  parent_id?: number | null;
  level: string;
  external_id?: string | null;
  country_code?: string | null;
  code?: string | null;
  name: string;
  display_name: string;
  delivery_fee: number;
  active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface DeliveryAddressPricingList {
  items: DeliveryAddressPricing[];
  total: number;
}

export interface DeliveryAddressPricingUpsertPayload {
  node_id: number;
  delivery_fee: number;
  active: boolean;
  sort_order: number;
}

export interface OperationalCapabilities {
  activation_stage_id: string;
  workflow_profile: OperationalWorkflowProfile;
  kitchen_feature_enabled: boolean;
  delivery_feature_enabled: boolean;
  warehouse_feature_enabled: boolean;
  kitchen_runtime_enabled: boolean;
  delivery_runtime_enabled: boolean;
  warehouse_runtime_enabled: boolean;
  kitchen_enabled: boolean;
  delivery_enabled: boolean;
  warehouse_enabled: boolean;
  kitchen_active_users: number;
  delivery_active_users: number;
  warehouse_active_suppliers?: number;
  warehouse_active_items?: number;
  kitchen_block_reason?: string | null;
  delivery_block_reason?: string | null;
  warehouse_block_reason?: string | null;
}

export interface OperationalSetting {
  key: string;
  value: string;
  description: string;
  editable: boolean;
}

export interface DeliveryHistoryRow {
  assignment_id: number;
  order_id: number;
  assignment_status: 'assigned' | 'departed' | 'delivered' | 'failed' | 'notified';
  order_status: OrderStatus;
  assigned_at: string;
  departed_at?: string | null;
  delivered_at?: string | null;
  order_subtotal: number;
  delivery_fee: number;
  order_total: number;
  phone?: string | null;
  address?: string | null;
}

export interface FinancialTransaction {
  id: number;
  order_id?: number | null;
  delivery_settlement_id?: number | null;
  expense_id?: number | null;
  amount: number;
  type:
    | 'sale'
    | 'refund'
    | 'expense'
    | 'food_revenue'
    | 'delivery_revenue'
    | 'driver_payable'
    | 'collection_clearing'
    | 'collection_adjustment'
    | 'refund_food_revenue'
    | 'refund_delivery_revenue'
    | 'reverse_driver_payable'
    | 'reverse_collection_clearing';
  direction?: 'debit' | 'credit' | null;
  account_code?: string | null;
  reference_group?: string | null;
  created_by: number;
  created_at: string;
  note?: string | null;
}

export interface DeliverySettlement {
  id: number;
  order_id: number;
  assignment_id: number;
  driver_id: number;
  status: 'pending' | 'partially_remitted' | 'remitted' | 'settled' | 'variance' | 'reversed' | string;
  driver_share_model: 'full_delivery_fee' | 'fixed_amount' | 'percentage' | string;
  driver_share_value: number;
  expected_customer_total: number;
  actual_collected_amount: number;
  food_revenue_amount: number;
  delivery_revenue_amount: number;
  driver_due_amount: number;
  store_due_amount: number;
  remitted_amount: number;
  remaining_store_due_amount: number;
  variance_amount: number;
  variance_reason?: string | null;
  recognized_at: string;
  settled_at?: string | null;
  settled_by?: number | null;
  note?: string | null;
}

export interface CashboxMovement {
  id: number;
  delivery_settlement_id?: number | null;
  order_id?: number | null;
  type: 'driver_remittance' | 'driver_payout' | 'cash_order_collection' | 'cash_refund' | 'cash_adjustment' | string;
  direction: 'in' | 'out';
  amount: number;
  cash_channel: 'cash_drawer' | 'safe' | 'bank' | 'wallet' | string;
  performed_by: number;
  created_at: string;
  note?: string | null;
}

export interface DeliveryAccountingMigrationStatus {
  legacy_candidates: number;
  pending_migratable: number;
  blocked_missing_assignment: number;
  blocked_missing_driver: number;
  backfilled_orders: number;
  assumed_amount_received_orders: number;
  cutover_ready: boolean;
  cutover_completed_at?: string | null;
  last_backfill_at?: string | null;
  last_backfill_by?: number | null;
  pending_order_ids: number[];
  blocked_missing_assignment_order_ids: number[];
  blocked_missing_driver_order_ids: number[];
}

export interface DeliveryAccountingBackfillResult {
  processed_orders: number;
  migrated_orders: number;
  blocked_missing_assignment: number;
  blocked_missing_driver: number;
  assumed_amount_received_orders: number;
  dry_run: boolean;
  migrated_order_ids: number[];
  skipped_missing_assignment_order_ids: number[];
  skipped_missing_driver_order_ids: number[];
  status: DeliveryAccountingMigrationStatus;
}

export interface ShiftClosure {
  id: number;
  business_date: string;
  opening_cash: number;
  sales_total: number;
  refunds_total: number;
  expenses_total: number;
  expected_cash: number;
  actual_cash: number;
  variance: number;
  transactions_count: number;
  note?: string | null;
  closed_by: number;
  closed_at: string;
}

export interface Expense {
  id: number;
  title: string;
  category: string;
  cost_center_id: number;
  cost_center_name?: string | null;
  amount: number;
  note?: string | null;
  status: 'pending' | 'approved' | 'rejected' | string;
  reviewed_by?: number | null;
  reviewed_at?: string | null;
  review_note?: string | null;
  attachments: ExpenseAttachment[];
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface ExpenseCostCenter {
  id: number;
  code: string;
  name: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExpenseAttachment {
  id: number;
  expense_id: number;
  file_name: string;
  file_url: string;
  mime_type: string;
  size_bytes: number;
  uploaded_by: number;
  created_at: string;
}

export interface ReportDailyRow {
  day: string;
  food_sales?: number;
  delivery_revenue?: number;
  driver_cost?: number;
  refunds?: number;
  cash_in?: number;
  cash_out?: number;
  sales: number;
  expenses: number;
  net: number;
}

export interface ReportMonthlyRow {
  month: string;
  food_sales?: number;
  delivery_revenue?: number;
  driver_cost?: number;
  refunds?: number;
  cash_in?: number;
  cash_out?: number;
  sales: number;
  expenses: number;
  net: number;
}

export interface ReportByTypeRow {
  order_type: OrderType;
  orders_count: number;
  food_sales?: number;
  delivery_revenue?: number;
  sales: number;
}

export interface ReportPerformance {
  avg_prep_minutes: number;
}

export interface ReportProfitabilityProductRow {
  product_id: number;
  product_name: string;
  category_name: string;
  quantity_sold: number;
  revenue: number;
  estimated_unit_cost: number;
  estimated_cost: number;
  gross_profit: number;
  margin_percent: number;
}

export interface ReportProfitabilityCategoryRow {
  category_name: string;
  quantity_sold: number;
  revenue: number;
  estimated_cost: number;
  gross_profit: number;
  margin_percent: number;
}

export interface ReportProfitability {
  start_date?: string | null;
  end_date?: string | null;
  total_quantity_sold: number;
  total_revenue: number;
  total_estimated_cost: number;
  total_gross_profit: number;
  total_margin_percent: number;
  by_products: ReportProfitabilityProductRow[];
  by_categories: ReportProfitabilityCategoryRow[];
}

export interface ReportPeriodMetrics {
  label: string;
  start_date: string;
  end_date: string;
  days_count: number;
  food_sales?: number;
  delivery_revenue?: number;
  driver_cost?: number;
  refunds?: number;
  cash_in?: number;
  cash_out?: number;
  sales: number;
  expenses: number;
  net: number;
  delivered_orders_count: number;
  avg_order_value: number;
}

export interface ReportPeriodDeltaRow {
  metric: string;
  current_value: number;
  previous_value: number;
  absolute_change: number;
  change_percent?: number | null;
}

export interface ReportPeriodComparison {
  current_period: ReportPeriodMetrics;
  previous_period: ReportPeriodMetrics;
  deltas: ReportPeriodDeltaRow[];
}

export interface ReportPeakHourRow {
  hour_label: string;
  orders_count: number;
  food_sales?: number;
  delivery_revenue?: number;
  sales: number;
  avg_order_value: number;
  avg_prep_minutes: number;
}

export interface ReportPeakHoursPerformance {
  start_date: string;
  end_date: string;
  days_count: number;
  peak_hour?: string | null;
  peak_orders_count: number;
  peak_sales: number;
  overall_avg_prep_minutes: number;
  by_hours: ReportPeakHourRow[];
}

export interface OrderTransitionLog {
  id: number;
  order_id: number;
  from_status: OrderStatus;
  to_status: OrderStatus;
  performed_by: number;
  timestamp: string;
}

export interface SystemAuditLog {
  id: number;
  module: string;
  action: string;
  entity_type: string;
  entity_id?: number | null;
  description: string;
  performed_by: number;
  timestamp: string;
}

export interface SecurityAuditEvent {
  id: number;
  event_type: string;
  success: boolean;
  severity: string;
  username?: string | null;
  role?: UserRole | null;
  user_id?: number | null;
  ip_address?: string | null;
  user_agent?: string | null;
  detail?: string | null;
  created_at: string;
}

export interface WarehouseSupplier {
  id: number;
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
  created_at: string;
  updated_at: string;
}

export interface WarehouseItem {
  id: number;
  name: string;
  unit: string;
  alert_threshold: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WarehouseStockBalance {
  item_id: number;
  item_name: string;
  unit: string;
  alert_threshold: number;
  active: boolean;
  quantity: number;
  is_low: boolean;
}

export interface WarehouseInboundVoucherItem {
  item_id: number;
  item_name: string;
  quantity: number;
  unit_cost: number;
  line_total: number;
}

export interface WarehouseOutboundVoucherItem {
  item_id: number;
  item_name: string;
  quantity: number;
  unit_cost: number;
  line_total: number;
}

export interface WarehouseInboundVoucher {
  id: number;
  voucher_no: string;
  supplier_id: number;
  supplier_name: string;
  reference_no?: string | null;
  note?: string | null;
  posted_at: string;
  received_by: number;
  total_quantity: number;
  total_cost: number;
  items: WarehouseInboundVoucherItem[];
}

export interface WarehouseOutboundVoucher {
  id: number;
  voucher_no: string;
  reason_code: string;
  reason: string;
  note?: string | null;
  posted_at: string;
  issued_by: number;
  total_quantity: number;
  total_cost: number;
  items: WarehouseOutboundVoucherItem[];
}

export interface WarehouseLedgerRow {
  id: number;
  item_id: number;
  item_name: string;
  movement_kind: 'inbound' | 'outbound' | string;
  source_type: string;
  source_id: number;
  quantity: number;
  unit_cost: number;
  line_value: number;
  running_avg_cost: number;
  balance_before: number;
  balance_after: number;
  note?: string | null;
  created_by: number;
  created_at: string;
}

export interface WarehouseOutboundReason {
  code: string;
  label: string;
}

export interface WarehouseStockCountItem {
  item_id: number;
  item_name: string;
  unit: string;
  system_quantity: number;
  counted_quantity: number;
  variance_quantity: number;
  unit_cost: number;
  variance_value: number;
}

export interface WarehouseStockCount {
  id: number;
  count_no: string;
  note?: string | null;
  status: 'pending' | 'settled' | string;
  counted_by: number;
  counted_at: string;
  settled_by?: number | null;
  settled_at?: string | null;
  total_variance_quantity: number;
  total_variance_value: number;
  items: WarehouseStockCountItem[];
}

export interface WarehouseDashboard {
  active_items: number;
  active_suppliers: number;
  low_stock_items: number;
  inbound_today: number;
  outbound_today: number;
}

