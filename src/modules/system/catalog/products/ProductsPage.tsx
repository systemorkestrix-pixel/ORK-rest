import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Archive, ArrowDown, ArrowDownUp, ArrowUp, Check, ExternalLink, Package, PackagePlus, Pencil, Power, RotateCcw, Search, SlidersHorizontal, Trash2 } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type {
  Product,
  ProductCategory,
  ProductConsumptionComponent,
  ProductKind,
  ProductPayload,
  WarehouseItem,
} from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';
import { PageShell } from '@/shared/ui/PageShell';
import { TABLE_ACTION_BUTTON_BASE, TABLE_STATUS_CHIP_BASE } from '@/shared/ui/tableAppearance';
import { resolveBackendOrigin } from '@/shared/utils/backendOrigin';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';

const ARCHIVED_PAGE_SIZE = 100;
const backendOrigin = resolveBackendOrigin();
const PROTECTED_CATEGORY_NAMES = new Set(['عام']);
const MENU_TABLE_ACTION_WITH_ICON = `${TABLE_ACTION_BUTTON_BASE} gap-1.5`;

type ProductSort = 'id' | 'name' | 'category' | 'price' | 'available';
type ProductAvailabilityState = 'available' | 'unavailable' | 'archived';
type ProductModalStep = 'identity' | 'exposure' | 'inventory' | 'review';
type EntryModalMode = 'choose' | 'category' | 'product';

interface ConsumptionComponentFormRow {
  warehouse_item_id: number;
  quantity_per_unit: number;
}

const emptyProductForm = {
  name: '',
  description: '',
  price: 0,
  kind: 'primary' as ProductKind,
  category_id: 0,
  available: true,
  is_archived: false,
  consumption_components: [] as ConsumptionComponentFormRow[],
};

const emptyConsumptionRow = (): ConsumptionComponentFormRow => ({
  warehouse_item_id: 0,
  quantity_per_unit: 1,
});

function normalizeWarehouseUnit(unit?: string | null): string {
  return (unit ?? '').trim().toLowerCase();
}

function isKilogramUnit(unit?: string | null): boolean {
  const normalized = normalizeWarehouseUnit(unit);
  return normalized === 'kg' || normalized === 'كغ' || normalized === 'كيلوغرام' || normalized === 'kilogram';
}

function getConsumptionInputUnitLabel(unit?: string | null): string {
  if (isKilogramUnit(unit)) {
    return 'غرام';
  }
  return unit?.trim() || 'وحدة';
}

function getConsumptionInputValue(quantityPerUnit: number, unit?: string | null): number {
  if (isKilogramUnit(unit)) {
    return Math.round(quantityPerUnit * 1000);
  }
  return quantityPerUnit;
}

function parseConsumptionInputValue(rawValue: string, unit?: string | null): number {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return isKilogramUnit(unit) ? 0.001 : 0.01;
  }
  if (isKilogramUnit(unit)) {
    return Math.max(0.001, parsed / 1000);
  }
  return Math.max(0.01, parsed);
}

function formatConsumptionQuantityForHumans(quantityPerUnit: number, unit?: string | null): string {
  if (isKilogramUnit(unit)) {
    return `${Math.round(quantityPerUnit * 1000)} غرام`;
  }
  const safeUnit = unit?.trim() || 'وحدة';
  return `${quantityPerUnit} ${safeUnit}`;
}

function buildConsumptionPreview(components: ProductConsumptionComponent[], limit = 2): string | null {
  if (components.length === 0) {
    return null;
  }
  const preview = components
    .slice(0, limit)
    .map((component) => {
      const itemName = component.warehouse_item_name ?? `#${component.warehouse_item_id}`;
      return `${itemName} ${formatConsumptionQuantityForHumans(component.quantity_per_unit, component.warehouse_item_unit)}`;
    })
    .join('، ');
  const remaining = components.length - limit;
  return remaining > 0 ? `${preview} +${remaining}` : preview;
}

function compareProductsForMenu(
  left: Product,
  right: Product,
  sortBy: ProductSort,
  sortDirection: 'asc' | 'desc',
): number {
  const direction = sortDirection === 'asc' ? 1 : -1;
  switch (sortBy) {
    case 'name':
      return left.name.localeCompare(right.name, 'ar') * direction;
    case 'category':
      return left.category.localeCompare(right.category, 'ar') * direction;
    case 'price':
      return (left.price - right.price) * direction;
    case 'available':
      return (Number(left.available) - Number(right.available)) * direction;
    case 'id':
    default:
      return (left.id - right.id) * direction;
  }
}

function getProductExposureSummary(product: Product): { badge: string; tone: string; note: string } {
  if (product.kind === 'primary') {
    return {
      badge: 'منتج أساسي',
      tone: 'border border-emerald-200 bg-emerald-100 text-emerald-700',
      note: 'يظهر أولًا',
    };
  }

  return {
    badge: 'منتج ثانوي',
    tone: 'border border-sky-200 bg-sky-100 text-sky-700',
    note: 'يظهر بعد الأصناف الأساسية',
  };
}

function getProductInventorySummary(
  product: Product,
  inventoryToolEnabled: boolean,
  warehouseBlockReason?: string,
): { badge: string; tone: string; note: string } {
  if (!inventoryToolEnabled) {
    return {
      badge: 'غير متاح',
      tone: 'border border-amber-300 bg-amber-50 text-amber-700',
      note: warehouseBlockReason ?? 'إدارة المكونات غير متاحة في هذه النسخة الحالية.',
    };
  }
  const linkedCount = product.consumption_components.length;
  if (linkedCount === 0) {
    return {
      badge: 'غير مربوط',
      tone: 'border border-stone-300 bg-stone-100 text-stone-700',
      note: 'لا يوجد استهلاك مخزني مسجل لهذا المنتج',
    };
  }

  return {
    badge: `${linkedCount} صنف`,
    tone: 'border border-amber-300 bg-amber-50 text-amber-700',
    note: buildConsumptionPreview(product.consumption_components) ?? 'مربوط بالمخزن',
  };
}

function renderProductThumbnail(product: Product, imageUrl: string | null) {
  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={product.name}
        className="h-14 w-14 rounded-xl border border-gray-200 object-cover shadow-sm"
        loading="lazy"
      />
    );
  }

  return (
    <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white text-[11px] font-bold text-gray-400">
      لا صورة
    </div>
  );
}

function CompactMenuStat({
  label,
  value,
  icon,
  tone = 'default',
}: {
  label: string;
  value: string | number;
  icon: any;
  tone?: 'default' | 'warning' | 'info';
}) {
  const toneClass =
    tone === 'warning'
      ? 'border-amber-300 bg-amber-100/80 text-amber-900'
      : tone === 'info'
        ? 'border-sky-300 bg-sky-100/80 text-sky-900'
        : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]';

  return (
    <div dir="rtl" className={`flex min-h-[42px] w-full items-center justify-between gap-2 rounded-xl border px-3 ${toneClass}`}>
      <div className="flex flex-col items-end text-right leading-none">
        <span className="text-[10px] font-bold opacity-80">{label}</span>
        <span className="mt-1 text-sm font-black">{value}</span>
      </div>
      <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-current/15 bg-white/40">
        {icon}
      </span>
    </div>
  );
}

function resolveProductRowTone(available: boolean): 'success' | 'warning' | 'danger' {
  return available ? 'success' : 'warning';
}

function resolveCategoryRowTone(active: boolean): 'success' | 'warning' | 'danger' {
  return active ? 'success' : 'warning';
}

export function ProductsPage() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [searchDraft, setSearchDraft] = useState('');
  const [sortBy, setSortBy] = useState<ProductSort>('id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  const [form, setForm] = useState(emptyProductForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [entryModalMode, setEntryModalMode] = useState<EntryModalMode>('choose');
  const [productStep, setProductStep] = useState<ProductModalStep>('identity');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [submitError, setSubmitError] = useState('');

  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryActive, setNewCategoryActive] = useState(true);
  const [categoryEditorRows, setCategoryEditorRows] = useState<ProductCategory[]>([]);

  const archivedProductsQuery = useQuery({
    queryKey: ['manager-products-paged', 'archived', search, sortBy, sortDirection],
    queryFn: () =>
      api.managerProductsPaged(role ?? 'manager', {
        page: 1,
        pageSize: ARCHIVED_PAGE_SIZE,
        search,
        sortBy,
        sortDirection,
        archiveState: 'archived',
        kind: 'all',
      }),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const categoriesQuery = useQuery({
    queryKey: ['manager-categories'],
    queryFn: () => api.managerCategories(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const allProductsQuery = useQuery({
    queryKey: ['manager-products', 'all'],
    queryFn: () => api.managerProducts(role ?? 'manager', 'all'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context'],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });

  const publicOrderUrl = useMemo(() => {
    const tenantCode =
      tenantContextQuery.data?.tenant_code?.trim() ||
      (typeof window === 'undefined' ? '' : window.sessionStorage.getItem('active_tenant_code')?.trim() || '');
    return tenantCode ? `/t/${encodeURIComponent(tenantCode)}/order` : null;
  }, [tenantContextQuery.data?.tenant_code]);

  const warehouseChannelEnabled =
    tenantContextQuery.isSuccess && (tenantContextQuery.data?.channel_modes?.warehouse ?? 'disabled') === 'core';

  const warehouseItemsQuery = useQuery({
    queryKey: ['manager-warehouse-items'],
    queryFn: () => api.managerWarehouseItems(role ?? 'manager'),
    enabled: role === 'manager' && warehouseChannelEnabled,
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const operationalCapabilitiesQuery = useQuery({
    queryKey: ['manager-operational-capabilities'],
    queryFn: () => api.managerOperationalCapabilities(role ?? 'manager'),
    enabled: role === 'manager',
    refetchInterval: adaptiveRefetchInterval(5000),
  });

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['manager-products-paged'] });
    queryClient.invalidateQueries({ queryKey: ['manager-products'] });
    queryClient.invalidateQueries({ queryKey: ['manager-categories'] });
    queryClient.invalidateQueries({ queryKey: ['manager-warehouse-items'] });
    queryClient.invalidateQueries({ queryKey: ['public-products'] });
  };

  const createMutation = useMutation({
    mutationFn: (payload: ProductPayload) => api.managerCreateProduct(role ?? 'manager', payload),
    onSuccess: refreshAll,
  });

  const updateMutation = useMutation({
    mutationFn: ({ productId, payload }: { productId: number; payload: ProductPayload }) =>
      api.managerUpdateProduct(role ?? 'manager', productId, payload),
    onSuccess: refreshAll,
  });

  const uploadImageMutation = useMutation({
    mutationFn: ({ productId, file }: { productId: number; file: File }) =>
      toBase64Payload(file).then((payload) => api.managerUploadProductImage(role ?? 'manager', productId, payload)),
    onSuccess: refreshAll,
  });

  const archiveMutation = useMutation({
    mutationFn: (productId: number) => api.managerDeleteProduct(role ?? 'manager', productId),
    onSuccess: refreshAll,
  });

  const permanentDeleteMutation = useMutation({
    mutationFn: (productId: number) => api.managerDeleteProductPermanently(role ?? 'manager', productId),
    onSuccess: refreshAll,
  });

  const statusMutation = useMutation({
    mutationFn: ({ productId, payload }: { productId: number; payload: ProductPayload }) =>
      api.managerUpdateProduct(role ?? 'manager', productId, payload),
    onSuccess: refreshAll,
  });

  const createCategoryMutation = useMutation({
    mutationFn: (payload: { name: string; active: boolean; sort_order: number }) =>
      api.managerCreateCategory(role ?? 'manager', payload),
    onSuccess: () => {
      refreshAll();
      setNewCategoryName('');
      setNewCategoryActive(true);
    },
  });

  const updateCategoryMutation = useMutation({
    mutationFn: ({ categoryId, payload }: { categoryId: number; payload: { name: string; active: boolean; sort_order: number } }) =>
      api.managerUpdateCategory(role ?? 'manager', categoryId, payload),
    onSuccess: refreshAll,
  });

  const saveCategoryChangesMutation = useMutation({
    mutationFn: async (rows: ProductCategory[]) => {
      const currentById = new Map<number, ProductCategory>(
        categories.map((category) => [category.id, category] as const),
      );
      const changedRows = rows
        .map((row, index) => ({
          row,
          nextSortOrder: index,
          current: currentById.get(row.id),
        }))
        .filter(({ row, nextSortOrder, current }) => {
          if (!current) {
            return false;
          }
          return current.name !== row.name.trim() || current.active !== row.active || current.sort_order !== nextSortOrder;
        });

      for (const { row, nextSortOrder } of changedRows) {
        await api.managerUpdateCategory(role ?? 'manager', row.id, {
          name: row.name.trim(),
          active: row.active,
          sort_order: nextSortOrder,
        });
      }
    },
    onSuccess: refreshAll,
    onError: refreshAll,
  });

  const deleteCategoryMutation = useMutation({
    mutationFn: (categoryId: number) => api.managerDeleteCategory(role ?? 'manager', categoryId),
    onSuccess: refreshAll,
  });

  const categories = useMemo<ProductCategory[]>(
    () =>
      [...(categoriesQuery.data ?? [])].sort(
        (left, right) => left.sort_order - right.sort_order || left.id - right.id,
      ),
    [categoriesQuery.data],
  );
  const allProducts = allProductsQuery.data ?? [];
  const warehouseItems = warehouseItemsQuery.data ?? [];
  const operationalCapabilities = operationalCapabilitiesQuery.data;
  const activeCategories = useMemo(() => categories.filter((category) => category.active), [categories]);
  const hasActiveCategories = activeCategories.length > 0;
  const defaultCategoryId = activeCategories[0]?.id ?? 0;
  const warehouseItemsMap = useMemo(() => new Map<number, WarehouseItem>(warehouseItems.map((item) => [item.id, item])), [warehouseItems]);
  const activeCategoriesCount = useMemo(() => activeCategories.length, [activeCategories]);
  const primaryProductsCount = useMemo(() => activeRowsByKind(allProducts, 'primary').length, [allProducts]);
  const secondaryProductsCount = useMemo(() => activeRowsByKind(allProducts, 'secondary').length, [allProducts]);
  const warehouseFeatureEnabled = operationalCapabilities?.warehouse_feature_enabled ?? true;
  const warehouseRuntimeEnabled = operationalCapabilities?.warehouse_runtime_enabled ?? true;
  const warehouseEnabled = operationalCapabilities?.warehouse_enabled ?? true;
  const warehouseBlockReason =
    warehouseChannelEnabled
      ? operationalCapabilities?.warehouse_block_reason ?? 'إدارة المكونات غير متاحة في هذه النسخة الحالية.'
      : 'إدارة المكونات غير متاحة في هذه النسخة الحالية.';
  const inventoryToolEnabled = warehouseChannelEnabled && warehouseFeatureEnabled && warehouseEnabled;
  const inventoryStepEnabled = inventoryToolEnabled;
  const resolveCategoryId = (product: Product): number => {
    if (product.category_id && product.category_id > 0) {
      return product.category_id;
    }
    const byName = categories.find((category) => category.name === product.category);
    return byName?.id ?? 0;
  };

  const resetModalState = () => {
    setEditingId(null);
    setEditingCategoryId(null);
    setForm({ ...emptyProductForm, category_id: 0 });
    setProductStep('identity');
    setEntryModalMode('choose');
    setImageFile(null);
    setSubmitError('');
    setNewCategoryName('');
    setNewCategoryActive(true);
  };

  const openCreateModal = () => {
    resetModalState();
    setIsModalOpen(true);
  };

  const startProductCreation = (kind: ProductKind) => {
    setEditingId(null);
    setForm({ ...emptyProductForm, kind, category_id: kind === 'primary' ? defaultCategoryId : 0 });
    setProductStep('identity');
    setEntryModalMode('product');
    setImageFile(null);
    setSubmitError('');
    setIsModalOpen(true);
  };

  const startCategoryCreation = () => {
    setEditingId(null);
    setEditingCategoryId(null);
    setEntryModalMode('category');
    setNewCategoryName('');
    setNewCategoryActive(true);
    setSubmitError('');
    setIsModalOpen(true);
  };

  const openEditCategoryModal = (category: ProductCategory) => {
    setEditingId(null);
    setEditingCategoryId(category.id);
    setEntryModalMode('category');
    setNewCategoryName(category.name);
    setNewCategoryActive(category.active);
    setSubmitError('');
    setIsModalOpen(true);
  };

  const openEditModal = (product: Product) => {
    const resolvedCategoryId = resolveCategoryId(product);
    setEditingId(product.id);
    setForm({
      name: product.name,
      description: product.description ?? '',
      price: product.price,
      kind: product.kind,
      category_id: product.kind === 'primary' ? resolvedCategoryId : 0,
      available: product.available,
      is_archived: Boolean(product.is_archived),
      consumption_components: product.consumption_components.map(mapConsumptionComponentToForm),
    });
    setProductStep('identity');
    setEntryModalMode('product');
    setImageFile(null);
    setSubmitError('');
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    resetModalState();
  };

  const onImageChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setImageFile(file);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError('');

    if (!productIdentityReady) {
      setProductStep('identity');
      setSubmitError(productIdentityError ?? 'أكمل تعريف المنتج أولًا.');
      return;
    }

    if (!productExposureReady) {
      setProductStep('exposure');
      setSubmitError(productExposureError ?? 'أكمل ظهور المنتج داخل الطلب أولًا.');
      return;
    }

    if (!productInventoryReady) {
      setProductStep('inventory');
      setSubmitError(productInventoryError ?? 'أكمل ربط المنتج بالمخزن أولًا.');
      return;
    }

    const payload: ProductPayload = {
      name: normalizedProductName,
      description: form.description || null,
      price: Number(form.price),
      kind: form.kind,
      available: form.available,
      secondary_links: [],
      consumption_components: validConsumptionComponents,
    };
    if (form.kind === 'primary') {
      payload.category_id = form.category_id;
    }
    if (editingId) {
      payload.is_archived = form.is_archived;
    }

    try {
      const product = editingId
        ? await updateMutation.mutateAsync({ productId: editingId, payload })
        : await createMutation.mutateAsync(payload);

      if (imageFile) {
        await uploadImageMutation.mutateAsync({ productId: product.id, file: imageFile });
      }

      closeModal();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'تعذر حفظ المنتج');
    }
  };

  const submitNewCategory = async () => {
    const normalized = newCategoryName.trim();
    if (normalized.length < 2) {
      return;
    }
    if (editingCategoryId) {
      const current = categories.find((category) => category.id === editingCategoryId);
      await updateCategoryMutation.mutateAsync({
        categoryId: editingCategoryId,
        payload: {
          name: normalized,
          active: newCategoryActive,
          sort_order: current?.sort_order ?? 0,
        },
      });
    } else {
      await createCategoryMutation.mutateAsync({
        name: normalized,
        active: true,
        sort_order: categories.length,
      });
    }
    closeModal();
  };

  const moveCategoryRow = (categoryId: number, direction: 'up' | 'down') => {
    const currentIndex = categoryEditorRows.findIndex((category) => category.id === categoryId);
    if (currentIndex < 0) {
      return;
    }

    const nextIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (nextIndex < 0 || nextIndex >= categoryEditorRows.length) {
      return;
    }

    const reordered = [...categoryEditorRows];
    const [movedCategory] = reordered.splice(currentIndex, 1);
    reordered.splice(nextIndex, 0, movedCategory);
    const normalizedRows = reordered.map((category, index) => ({ ...category, sort_order: index }));
    setCategoryEditorRows(normalizedRows);
    saveCategoryChangesMutation.mutate(normalizedRows);
  };

  const categoryRowsVersion = useMemo(
    () => JSON.stringify(categories.map((category) => [category.id, category.name, category.active, category.sort_order])),
    [categories],
  );

  useEffect(() => {
    setCategoryEditorRows(categories.map((category, index) => ({ ...category, sort_order: index })));
  }, [categoryRowsVersion, categories]);

  useEffect(() => {
    if (searchDraft.trim() === '' && search !== '') {
      setSearch('');
    }
  }, [search, searchDraft]);

  const isSubmitting =
    createMutation.isPending ||
    updateMutation.isPending ||
    uploadImageMutation.isPending ||
    archiveMutation.isPending ||
    permanentDeleteMutation.isPending ||
    statusMutation.isPending ||
    createCategoryMutation.isPending ||
    updateCategoryMutation.isPending ||
    saveCategoryChangesMutation.isPending ||
    deleteCategoryMutation.isPending ||
    false;

  const generalError =
    (archiveMutation.error as Error | null)?.message ??
    (permanentDeleteMutation.error as Error | null)?.message ??
    (statusMutation.error as Error | null)?.message ??
    (createCategoryMutation.error as Error | null)?.message ??
    (saveCategoryChangesMutation.error as Error | null)?.message ??
    (deleteCategoryMutation.error as Error | null)?.message ??
    '';

  const archivedRows = archivedProductsQuery.data?.items ?? [];
  const archivedTotalRows = archivedProductsQuery.data?.total ?? 0;
  const normalizedSearch = search.trim().toLowerCase();
  const activeDisplayRows = useMemo(() => {
    const rows = allProducts
      .filter((product) => !product.is_archived)
      .filter((product) => {
        if (!normalizedSearch) {
          return true;
        }
        return [product.id.toString(), product.name, product.category, product.description ?? ''].some((value) =>
          value.toLowerCase().includes(normalizedSearch),
        );
      })
      .sort((left, right) => compareProductsForMenu(left, right, sortBy, sortDirection));
    return rows;
  }, [allProducts, normalizedSearch, sortBy, sortDirection]);

  const buildPayloadFromProduct = (product: Product, nextState: ProductAvailabilityState): ProductPayload | null => {
    const categoryId = product.kind === 'primary' ? resolveCategoryId(product) : null;
    if (product.kind === 'primary' && (!categoryId || categoryId <= 0)) {
      return null;
    }

    return {
      name: product.name,
      description: product.description ?? null,
      price: product.price,
      kind: product.kind,
      category_id: categoryId,
      available: nextState === 'available',
      is_archived: nextState === 'archived',
    };
  };

  const formAvailabilityState: ProductAvailabilityState = form.is_archived
    ? 'archived'
    : form.available
      ? 'available'
      : 'unavailable';
  const selectedCategoryName =
    form.kind === 'secondary'
      ? 'لا ينطبق'
      : categories.find((category) => category.id === form.category_id)?.name ?? 'لم يحدد بعد';
  const normalizedProductName = form.name.trim();
  const validConsumptionComponents = form.consumption_components
    .filter((row) => row.warehouse_item_id > 0 && Number(row.quantity_per_unit) > 0)
    .map((row) => ({
      warehouse_item_id: row.warehouse_item_id,
      quantity_per_unit: Number(row.quantity_per_unit),
    }));
  const hasIncompleteConsumptionComponents = form.consumption_components.some(
    (row) => row.warehouse_item_id <= 0 || Number(row.quantity_per_unit) <= 0,
  );
  const hasDuplicateConsumptionComponents =
    new Set(validConsumptionComponents.map((row) => row.warehouse_item_id)).size !== validConsumptionComponents.length;
  const productIdentityError = !normalizedProductName
    ? 'أدخل اسم المنتج أولًا.'
    : form.kind === 'primary' && !hasActiveCategories
      ? 'أضف تصنيفًا نشطًا أولًا قبل تعريف المنتج.'
      : form.kind === 'primary' && form.category_id <= 0
        ? 'اختر تصنيفًا صالحًا للمنتج.'
        : null;
  const productExposureError = null;
  const productInventoryError = !inventoryToolEnabled
    ? null
    : hasIncompleteConsumptionComponents
      ? 'أكمل أصناف الاستهلاك المضافة أو احذف الصفوف الفارغة.'
      : hasDuplicateConsumptionComponents
        ? 'لا تكرر نفس صنف المستودع داخل مكونات الاستهلاك.'
        : null;
  const productIdentityReady = productIdentityError === null;
  const productExposureReady = productExposureError === null;
  const productInventoryReady = productInventoryError === null;
  const productReviewReady = productIdentityReady && productExposureReady && productInventoryReady;
  const availabilitySummaryLabel =
    formAvailabilityState === 'available'
      ? 'متاح'
      : formAvailabilityState === 'archived'
        ? 'مؤرشف'
        : 'غير متاح';
  const exposureSummaryLabel =
    form.kind === 'primary'
      ? 'منتج أساسي'
      : 'منتج ثانوي';
  const inventorySummaryLabel = !inventoryToolEnabled
    ? 'غير متاح في هذه النسخة'
    : validConsumptionComponents.length > 0
      ? `${validConsumptionComponents.length} صنف مستهلك`
      : 'لا يوجد ربط مخزني';

  if (
    archivedProductsQuery.isLoading ||
    allProductsQuery.isLoading ||
    warehouseItemsQuery.isLoading ||
    operationalCapabilitiesQuery.isLoading
  ) {
    return <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">جارٍ تحميل المنيو...</div>;
  }

  if (
    archivedProductsQuery.isError ||
    allProductsQuery.isError ||
    warehouseItemsQuery.isError ||
    operationalCapabilitiesQuery.isError
  ) {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">تعذر تحميل بيانات المنيو.</div>;
  }

  const activePrimaryRows = activeDisplayRows.filter((product) => product.kind === 'primary');
  const activeSecondaryRows = activeDisplayRows.filter((product) => product.kind === 'secondary');

  return (
    <PageShell
      className="admin-page"
      header={
        <div dir="rtl" className="space-y-3 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)]/70 px-3 py-3 text-right md:px-4">
          <div className="grid grid-cols-1 gap-2 xl:grid-cols-[minmax(0,1fr)_280px]">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <CompactMenuStat label="تصنيفات نشطة" value={activeCategoriesCount} icon={<SlidersHorizontal className="h-4 w-4" />} />
              <CompactMenuStat label="أصناف أساسية" value={primaryProductsCount} icon={<Package className="h-4 w-4" />} />
              <CompactMenuStat label="منتجات ثانوية" value={secondaryProductsCount} icon={<PackagePlus className="h-4 w-4" />} tone="info" />
              <CompactMenuStat label="مؤرشف حاليًا" value={archivedTotalRows} icon={<Archive className="h-4 w-4" />} tone="warning" />
            </div>

            <div className="grid gap-2">
              <button
                type="button"
                onClick={openCreateModal}
                className="btn-primary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
              >
                <PackagePlus className="h-4 w-4" />
                <span>إدراج</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  if (!publicOrderUrl) {
                    return;
                  }
                  window.open(publicOrderUrl, '_blank', 'noopener,noreferrer');
                }}
                className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
                disabled={!publicOrderUrl}
              >
                <ExternalLink className="h-4 w-4" />
                <span>فتح الواجهة العامة</span>
              </button>
            </div>
          </div>

          <div className="ops-surface-soft hidden rounded-2xl border p-3 md:block">
            <div className="grid gap-2 xl:grid-cols-[minmax(260px,1.15fr)_120px_180px_160px_120px]">
            <label>
              <span className="form-label">حقل البحث</span>
              <div className="flex min-h-[42px] items-center gap-2 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3">
                <Search className="h-4 w-4 text-[var(--text-secondary)]" />
                <input
                  value={searchDraft}
                  onChange={(event) => setSearchDraft(event.target.value)}
                  placeholder="ابحث بالاسم أو التصنيف أو الرقم"
                  className="w-full border-0 bg-transparent p-0 text-right text-sm font-semibold text-[var(--text-primary)] placeholder:text-[var(--text-secondary)]/75 focus:outline-none"
                />
              </div>
            </label>

            <div>
              <span className="form-label">تنفيذ</span>
              <button
                type="button"
                onClick={() => setSearch(searchDraft.trim())}
                className="btn-primary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
              >
                <Search className="h-4 w-4" />
                <span>بحث</span>
              </button>
            </div>

            <label>
              <span className="form-label">الترتيب حسب</span>
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value as ProductSort)}
                className="form-select min-h-[42px] w-full rounded-xl"
              >
                <option value="id">الرقم</option>
                <option value="name">الاسم</option>
                <option value="category">التصنيف</option>
                <option value="price">السعر</option>
                <option value="available">التوفر</option>
              </select>
            </label>

            <div>
              <span className="form-label">اتجاه الترتيب</span>
              <button
                type="button"
                onClick={() => setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))}
                className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
              >
                <ArrowDownUp className="h-4 w-4" />
                <span>{sortDirection === 'asc' ? 'تصاعدي' : 'تنازلي'}</span>
              </button>
            </div>

            <div>
              <span className="form-label">إعادة الضبط</span>
              <button
                type="button"
                onClick={() => {
                  setSearch('');
                  setSearchDraft('');
                  setSortBy('id');
                  setSortDirection('desc');
                }}
                className="btn-secondary inline-flex min-h-[42px] w-full items-center justify-center gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                <span>مسح</span>
              </button>
            </div>
          </div>
          </div>

          <div className="ops-surface-soft rounded-2xl border p-3 md:hidden">
            <div className="space-y-2">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                <div className="flex min-h-[42px] items-center gap-2 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] px-3">
                  <Search className="h-4 w-4 text-[var(--text-secondary)]" />
                  <input
                    value={searchDraft}
                    onChange={(event) => setSearchDraft(event.target.value)}
                    placeholder="ابحث بالاسم أو التصنيف أو الرقم"
                    className="w-full border-0 bg-transparent p-0 text-right text-sm font-semibold text-[var(--text-primary)] placeholder:text-[var(--text-secondary)]/75 focus:outline-none"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setSearch(searchDraft.trim())}
                  className="btn-primary ui-size-sm inline-flex items-center gap-2 whitespace-nowrap"
                >
                  <Search className="h-4 w-4" />
                  <span>بحث</span>
                </button>
              </div>

              <button
                type="button"
                className="btn-secondary ui-size-sm inline-flex w-full items-center justify-center gap-2"
                onClick={() => setShowAdvancedFilters((current) => !current)}
              >
                <SlidersHorizontal className="h-4 w-4" />
                <span>{showAdvancedFilters ? 'إخفاء الفلاتر المتقدمة' : 'إظهار الفلاتر المتقدمة'}</span>
              </button>

              {showAdvancedFilters ? (
                <div className="grid gap-2 pt-1">
                  <label>
                    <span className="form-label">الترتيب حسب</span>
                    <select
                      value={sortBy}
                      onChange={(event) => setSortBy(event.target.value as ProductSort)}
                      className="form-select"
                    >
                      <option value="id">الرقم</option>
                      <option value="name">الاسم</option>
                      <option value="category">التصنيف</option>
                      <option value="price">السعر</option>
                      <option value="available">التوفر</option>
                    </select>
                  </label>

                  <button
                    type="button"
                    onClick={() => setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))}
                    className="btn-secondary ui-size-sm inline-flex w-full items-center justify-center gap-2"
                  >
                    <ArrowDownUp className="h-4 w-4" />
                    <span>{sortDirection === 'asc' ? 'اتجاه الترتيب: تصاعدي' : 'اتجاه الترتيب: تنازلي'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setSearch('');
                      setSearchDraft('');
                      setSortBy('id');
                      setSortDirection('desc');
                    }}
                    className="btn-secondary ui-size-sm inline-flex w-full items-center justify-center gap-2"
                  >
                    <RotateCcw className="h-4 w-4" />
                    <span>مسح</span>
                  </button>
                </div>
              ) : null}
            </div>
          </div>
          {!inventoryToolEnabled ? (
            <div className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-800">
              أدوات المكونات مجمّدة الآن. {warehouseBlockReason}
            </div>
          ) : null}
        </div>
      }
      workspaceClassName="space-y-5 md:space-y-6"
    >
      <section className="admin-table-shell shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--console-border)] px-4 py-4">
          <div className="space-y-1">
            <p className="text-[11px] font-bold tracking-[0.14em] text-brand-700">جدول التصنيفات</p>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-black text-gray-800">التصنيفات</h3>
              <span className={`${TABLE_STATUS_CHIP_BASE} border border-brand-200 bg-brand-50 text-brand-700`}>
                {categories.length}
              </span>
            </div>
            <p className="text-xs text-gray-500">عدّل من الإجراء، وغيّر الترتيب من السهمين.</p>
          </div>
        </div>
        {generalError ? (
          <div className="border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{generalError}</div>
        ) : null}
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-[var(--surface-card-subtle)] text-gray-600">
              <tr>
                <th className="px-3 py-3 font-bold">الرقم</th>
                <th className="px-3 py-3 font-bold">اسم التصنيف</th>
                <th className="px-3 py-3 font-bold">الحالة</th>
                <th className="px-3 py-3 font-bold">الترتيب</th>
                <th className="px-3 py-3 font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {categoryEditorRows.map((category, index) => {
                const isProtected = isProtectedCategoryName(category.name);
                const categoryRank = index + 1;
                return (
                  <tr
                    key={category.id}
                    className={`border-t border-gray-100 transition-transform duration-200 table-row--${resolveCategoryRowTone(category.active)}`}
                  >
                    <td data-label="الرقم" className="px-3 py-3">
                      <span className="inline-flex min-w-12 items-center justify-center rounded-full border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-1 text-center text-xs font-black text-[var(--text-primary)]">
                        {categoryRank}
                      </span>
                    </td>
                    <td data-label="اسم التصنيف" className="px-3 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-gray-800">{category.name}</span>
                        {isProtected ? (
                          <span className={`${TABLE_STATUS_CHIP_BASE} border border-amber-200 bg-amber-100 text-amber-700`}>
                            افتراضي
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td data-label="الحالة" className="px-3 py-3">
                      <span
                        className={`${TABLE_STATUS_CHIP_BASE} ${
                          category.active
                            ? 'border border-emerald-200 bg-emerald-100 text-emerald-700'
                            : 'border border-gray-200 bg-gray-100 text-gray-700'
                        }`}
                      >
                        {category.active ? 'نشط' : 'غير نشط'}
                      </span>
                    </td>
                    <td data-label="الترتيب" className="px-3 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          type="button"
                          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-700 transition hover:-translate-y-0.5 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                          onClick={() => moveCategoryRow(category.id, 'up')}
                          disabled={isProtected || categoryRank === 1 || saveCategoryChangesMutation.isPending}
                          aria-label={`رفع تصنيف ${category.name}`}
                          title="رفع"
                        >
                          <ArrowUp className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-rose-300 bg-rose-50 text-rose-700 transition hover:translate-y-0.5 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                          onClick={() => moveCategoryRow(category.id, 'down')}
                          disabled={isProtected || categoryRank === categoryEditorRows.length || saveCategoryChangesMutation.isPending}
                          aria-label={`خفض تصنيف ${category.name}`}
                          title="خفض"
                        >
                          <ArrowDown className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                    <td data-label="الإجراءات" className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          dir="rtl"
                          onClick={() => openEditCategoryModal(category)}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-gray-300 text-gray-700`}
                        >
                          <span>تعديل</span>
                          <Pencil className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          disabled={isProtected}
                          onClick={() =>
                            setCategoryEditorRows((prev) =>
                              prev.map((row) => (row.id === category.id ? { ...row, active: !row.active } : row)),
                            )
                          }
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-brand-300 text-brand-700`}
                        >
                          <span>{category.active ? 'تعطيل' : 'تفعيل'}</span>
                          <Power className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          disabled={isProtected}
                          onClick={() => deleteCategoryMutation.mutate(category.id)}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-rose-300 text-rose-700`}
                        >
                          <span>حذف</span>
                          <Trash2 className="h-3.5 w-3.5 shrink-0" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {categories.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-gray-500">
                    لا توجد تصنيفات بعد.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-table-shell shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--console-border)] px-4 py-4">
          <div className="space-y-1">
            <p className="text-[11px] font-bold tracking-[0.14em] text-brand-700">المرحلة الأولى</p>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-black text-gray-800">المنتجات الأساسية</h3>
              <span className={`${TABLE_STATUS_CHIP_BASE} border border-brand-200 bg-brand-50 text-brand-700`}>
                {activePrimaryRows.length}
              </span>
            </div>
            <p className="text-xs text-gray-500">تظهر أولًا في الطلب العام والطلب اليدوي.</p>
          </div>
        </div>
          <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-[var(--surface-card-subtle)] text-gray-600">
              <tr>
                <th className="px-4 py-3 font-bold">المنتج</th>
                <th className="px-4 py-3 font-bold">الظهور في الطلب</th>
                <th className="px-4 py-3 font-bold">المكونات</th>
                <th className="px-4 py-3 font-bold">التصنيف</th>
                <th className="px-4 py-3 font-bold">السعر</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {activePrimaryRows.map((product) => {
                const imageUrl = resolveImageUrl(product.image_path);
                const activePayload = buildPayloadFromProduct(product, 'available');
                const unavailablePayload = buildPayloadFromProduct(product, 'unavailable');
                const canUpdateQuickState = Boolean(activePayload && unavailablePayload);
                const exposureSummary = getProductExposureSummary(product);
                const inventorySummary = getProductInventorySummary(product, inventoryToolEnabled, warehouseBlockReason);
                return (
                  <tr key={product.id} className={`border-t border-gray-100 align-top table-row--${resolveProductRowTone(product.available)}`}>
                    <td data-label="المنتج" className="px-4 py-3">
                      <div className="grid min-w-[280px] grid-cols-[56px_minmax(0,1fr)] items-start gap-3">
                        <div className="shrink-0">{renderProductThumbnail(product, imageUrl)}</div>
                        <div className="space-y-2 text-right">
                          <p className="font-bold text-gray-900">{product.name}</p>
                          <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold text-gray-500">
                            <span className="rounded-full bg-gray-100 px-2 py-1 text-gray-600">#{product.id}</span>
                          </div>
                          {product.description ? (
                            <p className="max-w-xs text-xs leading-6 text-gray-500">{product.description}</p>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td data-label="الظهور في الطلب" className="px-4 py-3">
                      <div className="space-y-2">
                        <span className={`${TABLE_STATUS_CHIP_BASE} ${exposureSummary.tone}`}>
                          {exposureSummary.badge}
                        </span>
                        <p className="text-xs leading-6 text-gray-500">{exposureSummary.note}</p>
                      </div>
                    </td>
                    <td data-label="المكونات" className="px-4 py-3">
                      <div className="space-y-2">
                        <span className={`${TABLE_STATUS_CHIP_BASE} ${inventorySummary.tone}`}>
                          {inventorySummary.badge}
                        </span>
                        <p className="text-xs leading-6 text-gray-500">{inventorySummary.note}</p>
                      </div>
                    </td>
                    <td data-label="التصنيف" className="px-4 py-3">
                      <span className="font-semibold text-gray-700">{product.category}</span>
                    </td>
                    <td data-label="السعر" className="px-4 py-3">
                      <span className="font-black text-gray-900">{product.price.toFixed(2)} د.ج</span>
                    </td>
                    <td data-label="الحالة" className="px-4 py-3">
                      <div className="space-y-2">
                        <span
                          className={`${TABLE_STATUS_CHIP_BASE} ${
                            product.available
                              ? 'border border-emerald-200 bg-emerald-100 text-emerald-700'
                              : 'border border-amber-200 bg-amber-100 text-amber-700'
                          }`}
                        >
                          {product.available ? 'متاح' : 'غير متاح'}
                        </span>
                      </div>
                    </td>
                    <td data-label="الإجراءات" className="px-4 py-3">
                      <div className="flex min-w-[170px] flex-wrap gap-2">
                        <button
                          type="button"
                          dir="rtl"
                          onClick={() => openEditModal(product)}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-gray-300 text-gray-700`}
                        >
                          <span>تعديل</span>
                          <Pencil className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          disabled={!canUpdateQuickState}
                          onClick={() => {
                            const payload = product.available ? unavailablePayload : activePayload;
                            if (!payload) {
                              return;
                            }
                            statusMutation.mutate({
                              productId: product.id,
                              payload,
                            });
                          }}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} ${
                            product.available
                              ? 'border border-amber-300 text-amber-700'
                              : 'border border-emerald-300 text-emerald-700'
                          }`}
                        >
                          <span>{product.available ? 'إيقاف مؤقت' : 'إعادة الإتاحة'}</span>
                          <Power className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          onClick={() => archiveMutation.mutate(product.id)}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-rose-300 text-rose-700`}
                        >
                          <span>أرشفة</span>
                          <Archive className="h-3.5 w-3.5 shrink-0" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {activePrimaryRows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-gray-500">
                    لا توجد منتجات أساسية ضمن نتائج البحث الحالية.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-table-shell shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--console-border)] px-4 py-4">
          <div className="space-y-1">
            <p className="text-[11px] font-bold tracking-[0.14em] text-sky-700">المرحلة الثانية</p>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-black text-gray-800">المنتجات الثانوية</h3>
              <span className={`${TABLE_STATUS_CHIP_BASE} border border-sky-200 bg-sky-50 text-sky-700`}>
                {activeSecondaryRows.length}
              </span>
            </div>
            <p className="text-xs text-gray-500">تظهر بعد اختيار المنتجات الأساسية.</p>
          </div>
        </div>
          <div className="adaptive-table overflow-x-auto">
            <table className="table-unified min-w-full text-sm">
              <thead className="bg-[var(--surface-card-subtle)] text-gray-600">
                <tr>
                  <th className="px-4 py-3 font-bold">المنتج</th>
                  <th className="px-4 py-3 font-bold">الظهور في الطلب</th>
                  <th className="px-4 py-3 font-bold">المكونات</th>
                  <th className="px-4 py-3 font-bold">السعر</th>
                  <th className="px-4 py-3 font-bold">الحالة</th>
                  <th className="px-4 py-3 font-bold">الإجراءات</th>
                </tr>
              </thead>
              <tbody>
                {activeSecondaryRows.map((product) => {
                  const imageUrl = resolveImageUrl(product.image_path);
                  const activePayload = buildPayloadFromProduct(product, 'available');
                  const unavailablePayload = buildPayloadFromProduct(product, 'unavailable');
                  const canUpdateQuickState = Boolean(activePayload && unavailablePayload);
                  const exposureSummary = getProductExposureSummary(product);
                  const inventorySummary = getProductInventorySummary(product, inventoryToolEnabled, warehouseBlockReason);
                  return (
                    <tr key={`secondary-${product.id}`} className={`border-t border-gray-100 align-top table-row--${resolveProductRowTone(product.available)}`}>
                      <td data-label="المنتج" className="px-4 py-3">
                        <div className="grid min-w-[280px] grid-cols-[56px_minmax(0,1fr)] items-start gap-3">
                          <div className="shrink-0">{renderProductThumbnail(product, imageUrl)}</div>
                          <div className="space-y-2 text-right">
                            <p className="font-bold text-gray-900">{product.name}</p>
                            <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold text-gray-500">
                              <span className="rounded-full bg-gray-100 px-2 py-1 text-gray-600">#{product.id}</span>
                            </div>
                            {product.description ? (
                              <p className="max-w-xs text-xs leading-6 text-gray-500">{product.description}</p>
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td data-label="الظهور في الطلب" className="px-4 py-3">
                        <div className="space-y-2">
                          <span className={`${TABLE_STATUS_CHIP_BASE} ${exposureSummary.tone}`}>
                            {exposureSummary.badge}
                          </span>
                          <p className="text-xs leading-6 text-gray-500">{exposureSummary.note}</p>
                        </div>
                      </td>
                      <td data-label="المكونات" className="px-4 py-3">
                        <div className="space-y-2">
                          <span className={`${TABLE_STATUS_CHIP_BASE} ${inventorySummary.tone}`}>
                            {inventorySummary.badge}
                          </span>
                          <p className="text-xs leading-6 text-gray-500">{inventorySummary.note}</p>
                        </div>
                      </td>
                      <td data-label="السعر" className="px-4 py-3">
                        <span className="font-black text-gray-900">{product.price.toFixed(2)} د.ج</span>
                      </td>
                      <td data-label="الحالة" className="px-4 py-3">
                        <span
                          className={`${TABLE_STATUS_CHIP_BASE} ${
                            product.available
                              ? 'border border-emerald-200 bg-emerald-100 text-emerald-700'
                              : 'border border-amber-200 bg-amber-100 text-amber-700'
                          }`}
                        >
                          {product.available ? 'متاح' : 'غير متاح'}
                        </span>
                      </td>
                      <td data-label="الإجراءات" className="px-4 py-3">
                        <div className="flex min-w-[170px] flex-wrap gap-2">
                        <button
                          type="button"
                          dir="rtl"
                          onClick={() => openEditModal(product)}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-gray-300 text-gray-700`}
                        >
                          <span>تعديل</span>
                          <Pencil className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          disabled={!canUpdateQuickState}
                          onClick={() => {
                            const payload = product.available ? unavailablePayload : activePayload;
                              if (!payload) {
                                return;
                              }
                              statusMutation.mutate({
                                productId: product.id,
                                payload,
                              });
                            }}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} ${
                            product.available
                              ? 'border border-amber-300 text-amber-700'
                              : 'border border-emerald-300 text-emerald-700'
                          }`}
                        >
                          <span>{product.available ? 'إيقاف مؤقت' : 'إعادة الإتاحة'}</span>
                          <Power className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          onClick={() => archiveMutation.mutate(product.id)}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-rose-300 text-rose-700`}
                        >
                          <span>أرشفة</span>
                          <Archive className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {activeSecondaryRows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-gray-500">
                      لا توجد منتجات ثانوية ضمن نتائج البحث الحالية.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
      </section>

      <section className="admin-table-shell border-gray-200 shadow-sm">
        <div className="space-y-1 border-b border-[var(--console-border)] px-4 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-black text-gray-800">الأرشيف</h3>
            <span className={`${TABLE_STATUS_CHIP_BASE} border border-gray-300 bg-gray-100 text-gray-700`}>
              {archivedTotalRows}
            </span>
          </div>
          <p className="text-xs text-gray-500">المنتجات المؤرشفة.</p>
          {archivedTotalRows > ARCHIVED_PAGE_SIZE ? (
            <p className="text-xs text-gray-500">يظهر أول {ARCHIVED_PAGE_SIZE} منتجًا من الأرشيف.</p>
          ) : null}
        </div>
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-[var(--surface-card-subtle)] text-gray-600">
              <tr>
                <th className="px-4 py-3 font-bold">المنتج</th>
                <th className="px-4 py-3 font-bold">الظهور في الطلب</th>
                <th className="px-4 py-3 font-bold">المكونات</th>
                <th className="px-4 py-3 font-bold">التصنيف</th>
                <th className="px-4 py-3 font-bold">السعر</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {archivedRows.map((product) => {
                const imageUrl = resolveImageUrl(product.image_path);
                const availablePayload = buildPayloadFromProduct(product, 'available');
                const unavailablePayload = buildPayloadFromProduct(product, 'unavailable');
                const canRestore = Boolean(availablePayload && unavailablePayload);
                const exposureSummary = getProductExposureSummary(product);
                const inventorySummary = getProductInventorySummary(product, inventoryToolEnabled, warehouseBlockReason);
                return (
                  <tr key={`archived-${product.id}`} className="border-t border-gray-100 align-top table-row--danger">
                    <td data-label="المنتج" className="px-4 py-3">
                      <div className="grid min-w-[280px] grid-cols-[56px_minmax(0,1fr)] items-start gap-3">
                        <div className="shrink-0">{renderProductThumbnail(product, imageUrl)}</div>
                        <div className="space-y-2 text-right">
                          <p className="font-bold text-gray-900">{product.name}</p>
                          <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold text-gray-500">
                            <span className="rounded-full bg-gray-100 px-2 py-1 text-gray-600">#{product.id}</span>
                          </div>
                          {product.description ? (
                            <p className="max-w-xs text-xs leading-6 text-gray-500">{product.description}</p>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td data-label="الظهور في الطلب" className="px-4 py-3">
                      <div className="space-y-2">
                        <span className={`${TABLE_STATUS_CHIP_BASE} ${exposureSummary.tone}`}>
                          {exposureSummary.badge}
                        </span>
                        <p className="text-xs leading-6 text-gray-500">{exposureSummary.note}</p>
                      </div>
                    </td>
                    <td data-label="المكونات" className="px-4 py-3">
                      <div className="space-y-2">
                        <span className={`${TABLE_STATUS_CHIP_BASE} ${inventorySummary.tone}`}>
                          {inventorySummary.badge}
                        </span>
                        <p className="text-xs leading-6 text-gray-500">{inventorySummary.note}</p>
                      </div>
                    </td>
                    <td data-label="التصنيف" className="px-4 py-3">
                      <span className="font-semibold text-gray-700">{product.category}</span>
                    </td>
                    <td data-label="السعر" className="px-4 py-3">
                      <span className="font-black text-gray-900">{product.price.toFixed(2)} د.ج</span>
                    </td>
                    <td data-label="الحالة" className="px-4 py-3">
                      <div className="space-y-2">
                        <span className={`${TABLE_STATUS_CHIP_BASE} border border-gray-300 bg-gray-200 text-gray-700`}>مؤرشف</span>
                      </div>
                    </td>
                    <td data-label="الإجراءات" className="px-4 py-3">
                      <div className="flex min-w-[200px] flex-wrap gap-2">
                        <button
                          type="button"
                          dir="rtl"
                          onClick={() => openEditModal(product)}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-gray-300 text-gray-700`}
                        >
                          <span>تعديل</span>
                          <Pencil className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          disabled={!canRestore}
                          onClick={() => {
                            if (!unavailablePayload) {
                              return;
                            }
                            statusMutation.mutate({
                              productId: product.id,
                              payload: unavailablePayload,
                            });
                          }}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-brand-300 text-brand-700`}
                        >
                          <span>استعادة كغير متاح</span>
                          <RotateCcw className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          disabled={!canRestore}
                          onClick={() => {
                            if (!availablePayload) {
                              return;
                            }
                            statusMutation.mutate({
                              productId: product.id,
                              payload: availablePayload,
                            });
                          }}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-emerald-300 text-emerald-700`}
                        >
                          <span>استعادة وتفعيل</span>
                          <Check className="h-3.5 w-3.5 shrink-0" />
                        </button>
                        <button
                          type="button"
                          dir="rtl"
                          disabled={permanentDeleteMutation.isPending}
                          onClick={() => {
                            const confirmed = window.confirm(
                              `سيتم حذف المنتج رقم ${product.id} نهائيا ولا يمكن التراجع. هل تريد المتابعة؟`
                            );
                            if (!confirmed) {
                              return;
                            }
                            permanentDeleteMutation.mutate(product.id);
                          }}
                          className={`${MENU_TABLE_ACTION_WITH_ICON} border-rose-300 text-rose-700`}
                        >
                          <span>حذف نهائي</span>
                          <Trash2 className="h-3.5 w-3.5 shrink-0" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {archivedRows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    لا توجد منتجات مؤرشفة ضمن نتائج البحث الحالية.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Modal
        open={isModalOpen}
        onClose={closeModal}
        title={
          entryModalMode === 'choose'
            ? 'إدراج'
            : entryModalMode === 'category'
              ? editingCategoryId
                ? `تعديل التصنيف رقم ${editingCategoryId}`
                : 'إضافة تصنيف'
              : editingId
                ? `تعديل المنتج رقم ${editingId}`
                : form.kind === 'primary'
                  ? 'إضافة منتج أساسي'
                  : 'إضافة منتج ثانوي'
        }
        description={undefined}
      >
        {entryModalMode === 'choose' ? (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              {[
                {
                  id: 'category',
                  label: 'إضافة تصنيف',
                  icon: SlidersHorizontal,
                  action: startCategoryCreation,
                },
                {
                  id: 'primary',
                  label: 'إضافة منتج أساسي',
                  icon: Package,
                  action: () => startProductCreation('primary'),
                },
                {
                  id: 'secondary',
                  label: 'إضافة منتج ثانوي',
                  icon: PackagePlus,
                  action: () => startProductCreation('secondary'),
                },
              ].map((card) => {
                const Icon = card.icon;
                return (
                  <button
                    key={card.id}
                    type="button"
                    onClick={card.action}
                    className="flex min-h-[156px] flex-col items-start gap-3 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 py-4 text-right transition hover:border-brand-200 hover:bg-white"
                  >
                    <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)]">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="text-sm font-black text-[var(--text-primary-strong)]">{card.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : entryModalMode === 'category' ? (
          <div className="space-y-4">
            <label className="space-y-1">
              <span className="form-label">اسم التصنيف</span>
              <input
                className="form-input"
                placeholder="مثال: مشروبات ساخنة"
                value={newCategoryName}
                onChange={(event) => setNewCategoryName(event.target.value)}
              />
            </label>

            {editingCategoryId ? (
              <label className="space-y-1">
                <span className="form-label">الحالة</span>
                <select
                  className="form-select"
                  value={newCategoryActive ? 'active' : 'inactive'}
                  onChange={(event) => setNewCategoryActive(event.target.value === 'active')}
                >
                  <option value="active">نشط</option>
                  <option value="inactive">غير نشط</option>
                </select>
              </label>
            ) : null}

            {createCategoryMutation.error ? (
              <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {(createCategoryMutation.error as Error).message || 'تعذر إضافة التصنيف.'}
              </p>
            ) : null}
            {updateCategoryMutation.error ? (
              <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {(updateCategoryMutation.error as Error).message || 'تعذر تحديث التصنيف.'}
              </p>
            ) : null}

            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-gray-200 pt-3">
              <button type="button" onClick={() => setEntryModalMode('choose')} className="btn-secondary">
                رجوع
              </button>
              <button
                type="button"
                onClick={submitNewCategory}
                className="btn-primary"
                disabled={(createCategoryMutation.isPending || updateCategoryMutation.isPending) || newCategoryName.trim().length < 2}
              >
                {editingCategoryId
                  ? updateCategoryMutation.isPending
                    ? 'جارٍ حفظ التعديل...'
                    : 'حفظ التعديل'
                  : createCategoryMutation.isPending
                    ? 'جارٍ الإضافة...'
                    : 'إضافة التصنيف'}
              </button>
            </div>
          </div>
        ) : (
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className={`grid gap-2 ${inventoryStepEnabled ? 'md:grid-cols-4' : 'md:grid-cols-3'}`}>
            {([
              { id: 'identity', label: '1. تعريف المنتج', ready: true },
              { id: 'exposure', label: '2. ظهوره في الطلب', ready: productIdentityReady },
              ...(inventoryStepEnabled
                ? [{ id: 'inventory', label: '3. المكونات', ready: productIdentityReady && productExposureReady } as const]
                : []),
              {
                id: 'review',
                label: inventoryStepEnabled ? '4. المراجعة' : '3. المراجعة',
                ready: productIdentityReady && productExposureReady && productInventoryReady,
              },
            ] as Array<{ id: ProductModalStep; label: string; ready: boolean }>).map((stepCard) => {
              const isActive = productStep === stepCard.id;
              const isCompleted =
                (stepCard.id === 'identity' && productIdentityReady && productStep !== 'identity') ||
                (stepCard.id === 'exposure' &&
                  productExposureReady &&
                  (inventoryStepEnabled ? ['inventory', 'review'] : ['review']).includes(productStep)) ||
                (stepCard.id === 'inventory' && productInventoryReady && productStep === 'review');
              const isDisabled = !stepCard.ready && !isActive;

              return (
                <button
                  key={stepCard.id}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => !isDisabled && setProductStep(stepCard.id)}
                  className={`rounded-2xl border px-4 py-3 text-right transition ${
                    isActive
                      ? 'border-brand-300 bg-brand-50 text-brand-800'
                      : isCompleted
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                        : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)]'
                  } ${isDisabled ? 'cursor-not-allowed opacity-60' : 'hover:border-brand-200 hover:bg-white'}`}
                >
                  <p className="text-sm font-black">{stepCard.label}</p>
                </button>
              );
            })}
          </div>

          {productStep === 'identity' ? (
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1">
                <span className="form-label">اسم المنتج</span>
                <input
                  className="form-input"
                  placeholder="مثال: بيتزا خضار كبيرة"
                  value={form.name}
                  onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                  required
                />
              </label>

              {form.kind === 'primary' ? (
                <label className="space-y-1">
                  <span className="form-label">التصنيف</span>
                  <select
                    className="form-select"
                    value={form.category_id}
                    onChange={(event) => setForm((prev) => ({ ...prev, category_id: Number(event.target.value) }))}
                    required
                  >
                    <option value={0}>اختر تصنيف المنتج</option>
                    {categories
                      .filter((category) => category.active || category.id === form.category_id)
                      .map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name} {category.active ? '' : '(غير نشط)'}
                        </option>
                      ))}
                  </select>
                </label>
              ) : null}

              <label className="space-y-1">
                <span className="form-label">حالة الإتاحة</span>
                <select
                  className="form-select"
                  value={formAvailabilityState}
                  onChange={(event) => {
                    const nextState = event.target.value as ProductAvailabilityState;
                    setForm((prev) => {
                      if (nextState === 'available') {
                        return { ...prev, available: true, is_archived: false };
                      }
                      if (nextState === 'archived') {
                        return { ...prev, available: false, is_archived: true };
                      }
                      return { ...prev, available: false, is_archived: false };
                    });
                  }}
                >
                  <option value="available">متاح للطلب</option>
                  <option value="unavailable">غير متاح للطلب</option>
                  <option value="archived">مؤرشف</option>
                </select>
              </label>

              {form.kind === 'primary' && !hasActiveCategories ? (
                <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700 md:col-span-2">
                  لا يوجد تصنيف نشط الآن. أضف تصنيفًا أولًا ثم واصل إدراج المنتج.
                </p>
              ) : null}

              <label className="space-y-1">
                <span className="form-label">السعر (د.ج)</span>
                <input
                  className="form-input"
                  placeholder="مثال: 850"
                  type="number"
                  min={0}
                  step="0.1"
                  value={form.price}
                  onChange={(event) => setForm((prev) => ({ ...prev, price: Number(event.target.value) }))}
                  required
                />
              </label>

              <label className="space-y-1 md:col-span-2">
                <span className="form-label">وصف المنتج</span>
                <textarea
                  className="form-textarea"
                  placeholder="وصف مختصر يساعد الفريق على تمييز المنتج بسرعة"
                  value={form.description}
                  onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
                />
              </label>

              <div className="md:col-span-2">
                <label className="form-label">صورة المنتج (اختياري)</label>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={onImageChange}
                  className="form-input"
                />
                <p className="mt-1 text-xs text-gray-500">الأنواع المدعومة: PNG / JPG / WEBP.</p>
                {imageFile ? <p className="mt-1 text-xs text-gray-500">تم اختيار: {imageFile.name}</p> : null}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <p className="text-xs font-bold text-[var(--text-muted)]">تعريف المنتج</p>
                  <div className="flex flex-wrap gap-2 text-xs font-semibold text-[var(--text-secondary)]">
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">{normalizedProductName || 'بدون اسم'}</span>
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">
                      {form.kind === 'primary' ? 'منتج أساسي' : 'منتج ثانوي'}
                    </span>
                    {form.kind === 'primary' ? (
                      <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">{selectedCategoryName}</span>
                    ) : null}
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">{availabilitySummaryLabel}</span>
                  </div>
                </div>
                <button type="button" onClick={() => setProductStep('identity')} className="btn-secondary ui-size-sm">
                  تعديل التعريف
                </button>
              </div>
            </div>
          )}

          {productStep === 'exposure' ? (
            <div className="space-y-3 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="space-y-2">
                <h3 className="text-sm font-black text-[var(--text-primary-strong)]">مكانه في الطلب</h3>
                <p className="text-xs font-semibold text-[var(--text-muted)]">
                  {form.kind === 'primary' ? 'يظهر أولًا.' : 'يظهر بعد المنتجات الأساسية.'}
                </p>
              </div>
            </div>
          ) : (inventoryStepEnabled && productStep === 'inventory') || productStep === 'review' ? (
            <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <p className="text-xs font-bold text-[var(--text-muted)]">ظهور المنتج داخل الطلب</p>
                  <div className="flex flex-wrap gap-2 text-xs font-semibold text-[var(--text-secondary)]">
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">{exposureSummaryLabel}</span>
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">
                      {form.kind === 'primary' ? 'المرحلة الأولى' : 'المرحلة الثانية'}
                    </span>
                  </div>
                </div>
                <button type="button" onClick={() => setProductStep('exposure')} className="btn-secondary ui-size-sm">
                  تعديل الظهور
                </button>
              </div>
            </div>
          ) : null}

          {inventoryStepEnabled && productStep === 'inventory' ? (
            <div className="space-y-3 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="space-y-1">
                  <h3 className="text-sm font-black text-[var(--text-primary-strong)]">المكونات</h3>
                  <p className="text-xs font-semibold text-[var(--text-muted)]">{inventoryToolEnabled ? 'حدد المكونات إن كانت مفعلة.' : warehouseBlockReason}</p>
                </div>
                {inventoryToolEnabled ? (
                  <button
                    type="button"
                    onClick={() =>
                      setForm((prev) => ({
                        ...prev,
                        consumption_components: [...prev.consumption_components, emptyConsumptionRow()],
                      }))
                    }
                    className="btn-secondary ui-size-sm"
                  >
                    إضافة صنف مستهلك
                  </button>
                ) : null}
              </div>

              {form.consumption_components.length === 0 ? (
                <p className="rounded-xl border border-dashed border-[var(--console-border)] px-3 py-2 text-xs font-semibold text-[var(--text-muted)]">
                  لا يوجد ربط مخزني الآن.
                </p>
              ) : (
                <div className="space-y-2">
                  {form.consumption_components.map((row, index) => {
                    const selectedItem = warehouseItemsMap.get(row.warehouse_item_id);
                    return (
                      <div key={`consumption-${index}-${row.warehouse_item_id}`} className="grid gap-2 rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)]/70 p-3 md:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)_auto]">
                        <label className="space-y-1">
                          <span className="form-label">صنف المستودع</span>
                          <select
                            className="form-select"
                            value={row.warehouse_item_id}
                            onChange={(event) =>
                              setForm((prev) => ({
                                ...prev,
                                consumption_components: prev.consumption_components.map((current, currentIndex) =>
                                  currentIndex === index
                                    ? { ...current, warehouse_item_id: Number(event.target.value) }
                                    : current,
                                ),
                              }))
                            }
                          >
                            <option value={0}>اختر صنفًا من المستودع</option>
                            {warehouseItems
                              .filter((item) => item.active)
                              .map((item) => (
                                <option key={item.id} value={item.id}>
                                  {item.name} ({item.unit})
                                </option>
                              ))}
                          </select>
                        </label>

                        <label className="space-y-1">
                          <span className="form-label">
                            الكمية لكل وحدة {selectedItem ? `(${getConsumptionInputUnitLabel(selectedItem.unit)})` : ''}
                          </span>
                          <input
                            className="form-input"
                            type="number"
                            min={isKilogramUnit(selectedItem?.unit) ? 1 : 0.01}
                            step={isKilogramUnit(selectedItem?.unit) ? 1 : '0.01'}
                            value={getConsumptionInputValue(row.quantity_per_unit, selectedItem?.unit)}
                            onChange={(event) =>
                              setForm((prev) => ({
                                ...prev,
                                consumption_components: prev.consumption_components.map((current, currentIndex) =>
                                  currentIndex === index
                                    ? {
                                        ...current,
                                        quantity_per_unit: parseConsumptionInputValue(event.target.value, selectedItem?.unit),
                                      }
                                    : current,
                                ),
                              }))
                            }
                          />
                          {selectedItem ? (
                            <p className="text-[11px] font-semibold text-[var(--text-muted)]">
                              يسجل في النظام: {formatConsumptionQuantityForHumans(row.quantity_per_unit, selectedItem.unit)}
                            </p>
                          ) : null}
                        </label>

                        <div className="flex items-end">
                          <button
                            type="button"
                            onClick={() =>
                              setForm((prev) => ({
                                ...prev,
                                consumption_components: prev.consumption_components.filter((_, currentIndex) => currentIndex !== index),
                              }))
                            }
                            className="btn-danger ui-size-sm w-full"
                          >
                            حذف
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : productStep === 'review' ? (
            <div className="space-y-4 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-xl border border-[var(--console-border)] bg-white px-3 py-3">
                  <p className="text-[11px] font-bold text-[var(--text-muted)]">تعريف المنتج</p>
                  <p className="mt-1 text-sm font-black text-[var(--text-primary)]">{normalizedProductName || 'بدون اسم'}</p>
                  <p className="mt-2 text-xs font-semibold text-[var(--text-secondary)]">
                    {form.kind === 'primary' ? `${selectedCategoryName} • ` : ''}{availabilitySummaryLabel} • {Number(form.price).toFixed(2)} د.ج
                  </p>
                </div>
                <div className="rounded-xl border border-[var(--console-border)] bg-white px-3 py-3">
                  <p className="text-[11px] font-bold text-[var(--text-muted)]">الظهور في الطلب</p>
                  <p className="mt-1 text-sm font-black text-[var(--text-primary)]">{exposureSummaryLabel}</p>
                  <p className="mt-2 text-xs font-semibold text-[var(--text-secondary)]">
                    {form.kind === 'primary' ? 'يظهر أولًا في الطلب' : 'يظهر بعد المنتجات الأساسية'}
                  </p>
                </div>
                <div className="rounded-xl border border-[var(--console-border)] bg-white px-3 py-3">
                  <p className="text-[11px] font-bold text-[var(--text-muted)]">المكونات</p>
                  <p className="mt-1 text-sm font-black text-[var(--text-primary)]">{inventorySummaryLabel}</p>
                  <p className="mt-2 text-xs font-semibold text-[var(--text-secondary)]">
                    {!inventoryToolEnabled
                      ? 'غير متاح في هذه النسخة'
                      : validConsumptionComponents.length > 0
                        ? 'خصم مع كل بيع'
                        : 'لا يوجد خصم الآن'}
                  </p>
                </div>
              </div>

              {validConsumptionComponents.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs font-bold text-[var(--text-muted)]">الاستهلاك المخزني</p>
                  <div className="flex flex-wrap gap-2">
                    {validConsumptionComponents.map((component) => {
                      const item = warehouseItemsMap.get(component.warehouse_item_id);
                      return (
                        <span key={`review-consumption-${component.warehouse_item_id}`} className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1 text-xs font-semibold text-[var(--text-secondary)]">
                          {item?.name ?? `#${component.warehouse_item_id}`} • {formatConsumptionQuantityForHumans(component.quantity_per_unit, item?.unit)}
                        </span>
                      );
                    })}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {submitError ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">{submitError}</p> : null}
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-gray-200 pt-3">
            <div className="flex flex-wrap items-center justify-end gap-2">
              {productStep === 'identity' && editingId === null ? (
                <button type="button" onClick={() => setEntryModalMode('choose')} className="btn-secondary" disabled={isSubmitting}>
                  رجوع
                </button>
              ) : null}
              {productStep === 'exposure' ? (
                <button type="button" onClick={() => setProductStep('identity')} className="btn-secondary" disabled={isSubmitting}>
                  رجوع
                </button>
              ) : null}
              {inventoryStepEnabled && productStep === 'inventory' ? (
                <button type="button" onClick={() => setProductStep('exposure')} className="btn-secondary" disabled={isSubmitting}>
                  رجوع
                </button>
              ) : null}
              {productStep === 'review' ? (
                <button
                  type="button"
                  onClick={() => setProductStep(inventoryStepEnabled ? 'inventory' : 'exposure')}
                  className="btn-secondary"
                  disabled={isSubmitting}
                >
                  رجوع
                </button>
              ) : null}

              {productStep === 'identity' ? (
                <button
                  type="button"
                  onClick={() => {
                    if (!productIdentityReady) {
                      setSubmitError(productIdentityError ?? 'أكمل تعريف المنتج أولًا.');
                      return;
                    }
                    setSubmitError('');
                    setProductStep('exposure');
                  }}
                  className="btn-primary"
                  disabled={isSubmitting}
                >
                  متابعة الظهور
                </button>
              ) : null}

              {productStep === 'exposure' ? (
                <button
                  type="button"
                  onClick={() => {
                    if (!productExposureReady) {
                      setSubmitError(productExposureError ?? 'أكمل هذه الخطوة أولًا.');
                      return;
                    }
                    setSubmitError('');
                    setProductStep(inventoryStepEnabled ? 'inventory' : 'review');
                  }}
                  className="btn-primary"
                  disabled={isSubmitting}
                >
                  {inventoryStepEnabled ? 'متابعة المكونات' : 'متابعة المراجعة'}
                </button>
              ) : null}

              {inventoryStepEnabled && productStep === 'inventory' ? (
                <button
                  type="button"
                  onClick={() => {
                    if (!productInventoryReady) {
                      setSubmitError(productInventoryError ?? 'أكمل هذه الخطوة أولًا.');
                      return;
                    }
                    setSubmitError('');
                    setProductStep('review');
                  }}
                  className="btn-primary"
                  disabled={isSubmitting}
                >
                  مراجعة المنتج
                </button>
              ) : null}

              {productStep === 'review' ? (
                <button type="submit" className="btn-primary" disabled={isSubmitting || !productReviewReady}>
                  {editingId ? 'حفظ التعديلات' : 'إضافة المنتج'}
                </button>
              ) : null}
            </div>
          </div>
        </form>
        )}
      </Modal>
    </PageShell>
  );
}

function mapConsumptionComponentToForm(component: ProductConsumptionComponent): ConsumptionComponentFormRow {
  return {
    warehouse_item_id: component.warehouse_item_id,
    quantity_per_unit: Number(component.quantity_per_unit),
  };
}

function activeRowsByKind(rows: Product[], kind: ProductKind): Product[] {
  return rows.filter((product) => product.kind === kind && !product.is_archived);
}

function resolveImageUrl(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (import.meta.env.DEV && normalizedPath.startsWith('/static/')) {
    return normalizedPath;
  }
  return `${backendOrigin}${normalizedPath}`;
}

function isProtectedCategoryName(name: string): boolean {
  return PROTECTED_CATEGORY_NAMES.has(name.trim().toLowerCase());
}

function toBase64Payload(file: File): Promise<{ mime_type: string; data_base64: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== 'string') {
        reject(new Error('تعذر قراءة ملف الصورة'));
        return;
      }
      const [, base64] = result.split(',', 2);
      if (!base64) {
        reject(new Error('صيغة الصورة غير صالحة'));
        return;
      }
      resolve({
        mime_type: file.type || 'image/jpeg',
        data_base64: base64,
      });
    };
    reader.onerror = () => reject(new Error('تعذر قراءة ملف الصورة'));
    reader.readAsDataURL(file);
  });
}
