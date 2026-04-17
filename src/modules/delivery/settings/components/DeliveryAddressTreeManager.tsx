import { useEffect, useMemo, useState } from 'react';
import { Pencil, Plus } from 'lucide-react';

import type {
  DeliveryAddressNode,
  DeliveryAddressNodeCreatePayload,
  DeliveryAddressNodeUpdatePayload,
  DeliveryAddressPricing,
  DeliveryLocationPricingQuote,
} from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';

type TreeLevelKey = 'admin_area_level_1' | 'admin_area_level_2' | 'locality' | 'sublocality';
type AddressNodeModalStep = 'basic' | 'review';

interface DeliveryAddressTreeManagerProps {
  levels: Array<{
    key: TreeLevelKey;
    label: string;
    description: string;
    nodes: DeliveryAddressNode[];
    selectedId: number | null;
    onSelect: (nodeId: number | null) => void;
    emptyState: string;
  }>;
  selectedNode: DeliveryAddressNode | null;
  selectedPathLabel: string;
  pricingItems: DeliveryAddressPricing[];
  quote?: DeliveryLocationPricingQuote | null;
  onCreateNode: (payload: DeliveryAddressNodeCreatePayload) => Promise<DeliveryAddressNode>;
  onUpdateNode: (nodeId: number, payload: DeliveryAddressNodeUpdatePayload) => Promise<DeliveryAddressNode>;
  onDeleteNode: (nodeId: number) => Promise<unknown>;
  onSavePricing: (payload: { node_id: number; delivery_fee: number; active: boolean; sort_order: number }) => Promise<unknown>;
  onDeletePricing: (pricingId: number) => Promise<unknown>;
}

interface AddressNodeFormState {
  parent_id: number | null;
  level: TreeLevelKey;
  display_name: string;
  code: string;
  visible_in_public: boolean;
  delivery_fee: string;
  pricing_active: boolean;
  pricing_sort_order: number;
  name: string;
  postal_code: string;
  notes: string;
  active: boolean;
  sort_order: number;
  remove_direct_pricing: boolean;
}

const LEVEL_LABELS: Record<TreeLevelKey, string> = {
  admin_area_level_1: 'المنطقة الرئيسية',
  admin_area_level_2: 'الفرع الإداري',
  locality: 'المدينة',
  sublocality: 'الحي',
};

function getNextLevel(selectedNode: DeliveryAddressNode | null): TreeLevelKey | null {
  if (!selectedNode) return 'admin_area_level_1';
  if (selectedNode.level === 'admin_area_level_1') return 'admin_area_level_2';
  if (selectedNode.level === 'admin_area_level_2') return 'locality';
  if (selectedNode.level === 'locality') return 'sublocality';
  return null;
}

function deriveCode(displayName: string, explicitCode: string) {
  const direct = explicitCode.trim();
  if (direct) return direct;
  const fallback = displayName.trim().replace(/\s+/g, '-');
  return fallback || `node-${Date.now()}`;
}

function buildCreateForm(
  selectedNode: DeliveryAddressNode | null,
  nextLevel: TreeLevelKey | null
): AddressNodeFormState {
  return {
    parent_id: selectedNode?.id ?? null,
    level: nextLevel ?? 'admin_area_level_1',
    display_name: '',
    code: '',
    visible_in_public: true,
    delivery_fee: '',
    pricing_active: true,
    pricing_sort_order: 0,
    name: '',
    postal_code: '',
    notes: '',
    active: true,
    sort_order: 0,
    remove_direct_pricing: false,
  };
}

function buildEditForm(node: DeliveryAddressNode, pricing: DeliveryAddressPricing | null): AddressNodeFormState {
  return {
    parent_id: node.parent_id,
    level: (node.level as TreeLevelKey) ?? 'admin_area_level_1',
    display_name: node.display_name,
    code: node.code,
    visible_in_public: node.visible_in_public,
    delivery_fee: pricing ? String(pricing.delivery_fee) : '',
    pricing_active: pricing?.active ?? true,
    pricing_sort_order: pricing?.sort_order ?? 0,
    name: node.name,
    postal_code: node.postal_code ?? '',
    notes: node.notes ?? '',
    active: node.active,
    sort_order: node.sort_order,
    remove_direct_pricing: false,
  };
}

function pricingSourceLabel(source?: string | null) {
  switch (source) {
    case 'manual_tree':
      return 'من شجرة العناوين';
    case 'fixed':
      return 'من الرسم الاحتياطي';
    case 'unavailable':
      return 'غير متاح';
    default:
      return 'غير محدد';
  }
}

function NodeFormFields({
  mode,
  form,
  levelLabel,
  directPricingExists,
  quote,
  advancedOpen,
  onAdvancedToggle,
  onChange,
}: {
  mode: 'create' | 'edit';
  form: AddressNodeFormState;
  levelLabel: string;
  directPricingExists: boolean;
  quote?: DeliveryLocationPricingQuote | null;
  advancedOpen: boolean;
  onAdvancedToggle: () => void;
  onChange: (patch: Partial<AddressNodeFormState>) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1">
          <span className="form-label">المستوى الحالي</span>
          <input className="form-input" value={levelLabel} disabled />
        </label>

        <label className="space-y-1">
          <span className="form-label">الاسم الذي سيظهر للعميل</span>
          <input
            className="form-input"
            value={form.display_name}
            onChange={(event) => onChange({ display_name: event.target.value })}
            placeholder="مثال: حي النصر أو باب الزوار"
            required
          />
        </label>

        <label className="space-y-1">
          <span className="form-label">الرمز الداخلي</span>
          <input
            className="form-input"
            value={form.code}
            onChange={(event) => onChange({ code: event.target.value })}
            placeholder="اختياري"
          />
        </label>

        <label className="space-y-1">
          <span className="form-label">رسم التوصيل لهذه العقدة</span>
          <input
            type="number"
            min={0}
            step="0.1"
            className="form-input"
            value={form.delivery_fee}
            onChange={(event) => onChange({ delivery_fee: event.target.value, remove_direct_pricing: false })}
            placeholder={mode === 'create' ? 'اتركه فارغًا إن لم ترد تسعيرًا مباشرًا' : 'اتركه كما هو أو حدّثه'}
          />
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="flex items-center gap-2 rounded-xl border border-[var(--console-border)] px-3 py-3 text-sm">
          <input
            type="checkbox"
            checked={form.visible_in_public}
            onChange={(event) => onChange({ visible_in_public: event.target.checked })}
          />
          متاح للعميل في الواجهة العامة
        </label>

        <label className="flex items-center gap-2 rounded-xl border border-[var(--console-border)] px-3 py-3 text-sm">
          <input
            type="checkbox"
            checked={form.pricing_active}
            onChange={(event) => onChange({ pricing_active: event.target.checked })}
            disabled={!form.delivery_fee.trim()}
          />
          فعّل السعر المباشر لهذه العقدة
        </label>
      </div>

      {mode === 'edit' && quote ? (
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3 text-xs">
            <p className="font-bold text-[var(--text-muted)]">السعر الحالي للعميل</p>
            <p className="mt-1 text-lg font-black text-[var(--text-primary-strong)]">
              {quote.available && quote.delivery_fee !== null ? quote.delivery_fee.toFixed(2) : '--'}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3 text-xs">
            <p className="font-bold text-[var(--text-muted)]">مصدر السعر</p>
            <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">
              {pricingSourceLabel(quote.pricing_source)}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3 text-xs">
            <p className="font-bold text-[var(--text-muted)]">العقدة المرجعية</p>
            <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">
              {quote.resolved_node_label ?? 'غير محددة'}
            </p>
          </div>
        </div>
      ) : null}

      {mode === 'edit' && directPricingExists ? (
        <label className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-3 text-sm">
          <input
            type="checkbox"
            checked={form.remove_direct_pricing}
            onChange={(event) => onChange({ remove_direct_pricing: event.target.checked })}
          />
          إزالة السعر المباشر والاعتماد على سعر الأب إن وجد
        </label>
      ) : null}

      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)]">
        <button
          type="button"
          className="flex w-full items-center justify-between gap-3 px-4 py-3 text-sm font-black text-[var(--text-primary-strong)]"
          onClick={onAdvancedToggle}
        >
          <span>خيارات إضافية</span>
          <span className="text-xs font-semibold text-[var(--text-muted)]">
            {advancedOpen ? 'إخفاء' : 'إظهار'}
          </span>
        </button>

        {advancedOpen ? (
          <div className="grid gap-3 border-t border-[var(--console-border)] p-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="form-label">الاسم الداخلي</span>
              <input
                className="form-input"
                value={form.name}
                onChange={(event) => onChange({ name: event.target.value })}
                placeholder="يُشتق تلقائيًا من الاسم الظاهر إذا تُرك فارغًا"
              />
            </label>

            <label className="space-y-1">
              <span className="form-label">ترتيب ظهور العنوان</span>
              <input
                type="number"
                min={0}
                className="form-input"
                value={form.sort_order}
                onChange={(event) => onChange({ sort_order: Number(event.target.value) || 0 })}
              />
            </label>

            <label className="space-y-1">
              <span className="form-label">الرمز البريدي</span>
              <input
                className="form-input"
                value={form.postal_code}
                onChange={(event) => onChange({ postal_code: event.target.value })}
              />
            </label>

            <label className="space-y-1">
              <span className="form-label">ترتيب قاعدة السعر</span>
              <input
                type="number"
                min={0}
                className="form-input"
                value={form.pricing_sort_order}
                onChange={(event) => onChange({ pricing_sort_order: Number(event.target.value) || 0 })}
              />
            </label>

            <label className="space-y-1 md:col-span-2">
              <span className="form-label">ملاحظات داخلية</span>
              <textarea
                className="form-textarea"
                value={form.notes}
                onChange={(event) => onChange({ notes: event.target.value })}
                placeholder="اختياري"
              />
            </label>

            <label className="flex items-center gap-2 rounded-xl border border-[var(--console-border)] px-3 py-3 text-sm">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(event) => onChange({ active: event.target.checked })}
              />
              العنوان نشط داخل الشجرة
            </label>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function DeliveryAddressTreeManager({
  levels,
  selectedNode,
  selectedPathLabel,
  pricingItems,
  quote,
  onCreateNode,
  onUpdateNode,
  onDeleteNode,
  onSavePricing,
  onDeletePricing,
}: DeliveryAddressTreeManagerProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [createStep, setCreateStep] = useState<AddressNodeModalStep>('basic');
  const [editStep, setEditStep] = useState<AddressNodeModalStep>('basic');
  const [createAdvancedOpen, setCreateAdvancedOpen] = useState(false);
  const [editAdvancedOpen, setEditAdvancedOpen] = useState(false);
  const [createPending, setCreatePending] = useState(false);
  const [editPending, setEditPending] = useState(false);
  const [deletePending, setDeletePending] = useState(false);
  const [createError, setCreateError] = useState('');
  const [editError, setEditError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');
  const [editSuccess, setEditSuccess] = useState('');

  const nextLevel = getNextLevel(selectedNode);
  const selectedPricing = useMemo(
    () => pricingItems.find((item) => item.node_id === selectedNode?.id) ?? null,
    [pricingItems, selectedNode?.id]
  );
  const directPricingByNodeId = useMemo(
    () => new Map(pricingItems.map((item) => [item.node_id, item])),
    [pricingItems]
  );

  const [createForm, setCreateForm] = useState<AddressNodeFormState>(buildCreateForm(selectedNode, nextLevel));
  const [editForm, setEditForm] = useState<AddressNodeFormState | null>(
    selectedNode ? buildEditForm(selectedNode, selectedPricing) : null
  );

  useEffect(() => {
    if (!createOpen) {
      setCreateStep('basic');
      setCreateAdvancedOpen(false);
      setCreateError('');
      setCreateSuccess('');
      setCreateForm(buildCreateForm(selectedNode, nextLevel));
    }
  }, [createOpen, selectedNode, nextLevel]);

  useEffect(() => {
    setEditForm(selectedNode ? buildEditForm(selectedNode, selectedPricing) : null);
    setEditStep('basic');
    setEditAdvancedOpen(false);
    setEditError('');
    setEditSuccess('');
  }, [selectedNode, selectedPricing]);

  const createTitle = useMemo(() => {
    if (!nextLevel) return 'وصلت إلى آخر مستوى متاح';
    return selectedNode ? `إضافة عنوان جديد تحت ${selectedNode.display_name}` : 'إضافة عنوان رئيسي جديد';
  }, [nextLevel, selectedNode]);

  const visibleLevels = useMemo(
    () =>
      levels.filter((level, index) => {
        if (index === 0) return true;
        return Boolean(levels[index - 1]?.selectedId);
      }),
    [levels]
  );

  async function handleCreateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!nextLevel) return;

    setCreatePending(true);
    setCreateError('');
    setCreateSuccess('');

    try {
      const displayName = createForm.display_name.trim();
      const code = deriveCode(displayName, createForm.code);
      const name = createForm.name.trim() || displayName;

      const node = await onCreateNode({
        parent_id: selectedNode?.id ?? null,
        level: nextLevel,
        code,
        name,
        display_name: displayName,
        postal_code: createForm.postal_code.trim() || null,
        notes: createForm.notes.trim() || null,
        active: createForm.active,
        visible_in_public: createForm.visible_in_public,
        sort_order: createForm.sort_order,
      });

      if (createForm.delivery_fee.trim()) {
        await onSavePricing({
          node_id: node.id,
          delivery_fee: Number(createForm.delivery_fee) || 0,
          active: createForm.pricing_active,
          sort_order: createForm.pricing_sort_order,
        });
      }

      setCreateSuccess('تم حفظ العنوان الجديد بنجاح.');
      setCreateOpen(false);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'تعذر حفظ العنوان الجديد.');
    } finally {
      setCreatePending(false);
    }
  }

  async function handleEditSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedNode || !editForm) return;

    setEditPending(true);
    setEditError('');
    setEditSuccess('');

    try {
      const displayName = editForm.display_name.trim();
      const code = deriveCode(displayName, editForm.code);
      const name = editForm.name.trim() || displayName;

      await onUpdateNode(selectedNode.id, {
        code,
        name,
        display_name: displayName,
        postal_code: editForm.postal_code.trim() || null,
        notes: editForm.notes.trim() || null,
        active: editForm.active,
        visible_in_public: editForm.visible_in_public,
        sort_order: editForm.sort_order,
      });

      if (editForm.remove_direct_pricing && selectedPricing) {
        await onDeletePricing(selectedPricing.id);
      } else if (editForm.delivery_fee.trim()) {
        await onSavePricing({
          node_id: selectedNode.id,
          delivery_fee: Number(editForm.delivery_fee) || 0,
          active: editForm.pricing_active,
          sort_order: editForm.pricing_sort_order,
        });
      }

      setEditSuccess('تم تحديث العنوان بنجاح.');
      setEditOpen(false);
    } catch (error) {
      setEditError(error instanceof Error ? error.message : 'تعذر تحديث العنوان المحدد.');
    } finally {
      setEditPending(false);
    }
  }

  async function handleDeleteNode() {
    if (!selectedNode) return;
    const deleteLabel = selectedNode.child_count > 0 ? 'الفرع وكل ما يتبعه' : 'العنوان';
    const confirmed = window.confirm(`سيتم حذف ${deleteLabel} نهائيًا. هل تريد المتابعة؟`);
    if (!confirmed) return;

    setDeletePending(true);
    setEditError('');
    setEditSuccess('');

    try {
      await onDeleteNode(selectedNode.id);
      setEditSuccess(selectedNode.child_count > 0 ? 'تم حذف الفرع المحدد.' : 'تم حذف العنوان المحدد.');
      setEditOpen(false);
      setEditStep('basic');
    } catch (error) {
      setEditError(error instanceof Error ? error.message : 'تعذر حذف العنوان المحدد.');
    } finally {
      setDeletePending(false);
    }
  }

  return (
    <section className="admin-card space-y-4 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <h3 className="text-sm font-black text-[var(--text-primary-strong)]">شجرة عناوين التوصيل</h3>
          <p className="text-xs text-[var(--text-muted)]">ابدأ من المستوى الأول، ثم اختر العقدة المطلوبة لفتح المستوى التالي أو تعديل العقدة المحددة.</p>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[1.4fr_0.8fr_0.8fr]">
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 py-3 text-sm">
          <p className="font-bold text-[var(--text-muted)]">العنوان المحدد الآن</p>
          <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">
            {selectedPathLabel || 'لم يتم تحديد عنوان بعد'}
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 py-3 text-sm">
          <p className="font-bold text-[var(--text-muted)]">السعر الفعلي</p>
          <p className="mt-1 text-lg font-black text-[var(--text-primary-strong)]">
            {quote?.available && quote.delivery_fee !== null ? quote.delivery_fee.toFixed(2) : '--'}
          </p>
        </div>
        <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 py-3 text-sm">
          <p className="font-bold text-[var(--text-muted)]">مصدر السعر</p>
          <p className="mt-1 text-sm font-black text-[var(--text-primary-strong)]">
            {pricingSourceLabel(quote?.pricing_source)}
          </p>
        </div>
      </div>

      <div className={`grid gap-3 ${visibleLevels.length > 1 ? 'xl:grid-cols-2' : ''}`}>
        {visibleLevels.map((level) => {
          const levelSelectedNode = level.nodes.find((node) => node.id === level.selectedId) ?? null;
          const canAddHere =
            (level.key === 'admin_area_level_1' && !selectedNode && nextLevel === 'admin_area_level_1') ||
            (selectedNode?.id === levelSelectedNode?.id && nextLevel !== null && nextLevel !== level.key);

          return (
          <div key={level.key} className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3">
            <div className="flex items-start justify-between gap-3 border-b border-[var(--console-border)] pb-2">
              <div>
                <h4 className="text-sm font-black text-[var(--text-primary-strong)]">{level.label}</h4>
                <p className="mt-1 text-xs text-[var(--text-muted)]">{level.description}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {canAddHere ? (
                  <button
                    type="button"
                    className="btn-secondary ui-size-sm gap-2"
                    onClick={() => setCreateOpen(true)}
                  >
                    <Plus className="h-4 w-4" />
                    {nextLevel ? `إضافة ${LEVEL_LABELS[nextLevel]}` : 'إضافة'}
                  </button>
                ) : null}
                {levelSelectedNode ? (
                  <button
                    type="button"
                    className="btn-secondary ui-size-sm gap-2"
                    onClick={() => setEditOpen(true)}
                  >
                    <Pencil className="h-4 w-4" />
                    تعديل
                  </button>
                ) : null}
              </div>
            </div>

            <div className="mt-3 space-y-2">
              {level.nodes.length === 0 ? (
                <p className="rounded-xl border border-dashed border-[var(--console-border)] px-3 py-4 text-center text-xs text-[var(--text-muted)]">
                  {level.emptyState}
                </p>
              ) : (
                level.nodes.map((node) => {
                  const isSelected = level.selectedId === node.id;
                  const directPricing = directPricingByNodeId.get(node.id) ?? null;

                  return (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => level.onSelect(isSelected ? null : node.id)}
                      className={`w-full rounded-xl border px-3 py-3 text-right transition ${
                        isSelected
                          ? 'border-[var(--primary-button-bg)] bg-[color:color-mix(in_srgb,var(--primary-button-bg)_18%,transparent)]'
                          : 'border-[var(--console-border)] bg-[var(--surface-card)] hover:bg-[var(--surface-card-hover)]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 space-y-2">
                          <p className="truncate text-sm font-black text-[var(--text-primary-strong)]">{node.display_name}</p>
                          <div className="flex flex-wrap gap-2 text-[11px] font-semibold">
                            <span
                              className={`rounded-full px-2 py-1 ${
                                node.visible_in_public
                                  ? 'bg-emerald-500/10 text-emerald-300'
                                  : 'bg-amber-500/10 text-amber-300'
                              }`}
                            >
                              {node.visible_in_public ? 'متاح للعامة' : 'مخفي عن العامة'}
                            </span>
                            {directPricing ? (
                              <span className="rounded-full bg-sky-500/10 px-2 py-1 text-sky-300">
                                {directPricing.delivery_fee.toFixed(2)}
                              </span>
                            ) : null}
                          </div>
                        </div>

                        <div className="shrink-0 text-left text-[11px] font-bold text-[var(--text-muted)]">
                          {node.child_count > 0 ? `${node.child_count} فرع` : 'نهاية'}
                        </div>
                      </div>

                      {!node.active ? (
                        <p className="mt-2 text-[11px] font-semibold text-rose-300">العقدة موقوفة حاليًا</p>
                      ) : null}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        );
        })}
      </div>

      <Modal
        open={createOpen}
        onClose={() => {
          setCreateOpen(false);
          setCreateStep('basic');
        }}
        title={createTitle}
        description="أدخل بيانات العنوان أولًا، ثم راجعه قبل الحفظ."
      >
        <form className="space-y-4" onSubmit={handleCreateSubmit}>
          <div className="grid gap-2 sm:grid-cols-2">
            {(
              [
                { id: 'basic', label: '1. بيانات العنوان' },
                { id: 'review', label: '2. المراجعة' },
              ] as Array<{ id: AddressNodeModalStep; label: string }>
            ).map((stepCard) => {
              const active = createStep === stepCard.id;
              return (
                <button
                  key={stepCard.id}
                  type="button"
                  onClick={() => {
                    if (stepCard.id === 'review' && !createForm.display_name.trim()) return;
                    setCreateStep(stepCard.id);
                  }}
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

          {createStep === 'basic' ? (
            <NodeFormFields
              mode="create"
              form={createForm}
              levelLabel={LEVEL_LABELS[(nextLevel ?? createForm.level) as TreeLevelKey] ?? createForm.level}
              directPricingExists={false}
              onAdvancedToggle={() => setCreateAdvancedOpen((value) => !value)}
              advancedOpen={createAdvancedOpen}
              onChange={(patch) => setCreateForm((prev) => ({ ...prev, ...patch }))}
            />
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                <p className="text-xs font-bold text-[var(--text-muted)]">العنوان</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">{createForm.display_name || '—'}</p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {LEVEL_LABELS[(nextLevel ?? createForm.level) as TreeLevelKey] ?? createForm.level}
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                <p className="text-xs font-bold text-[var(--text-muted)]">التسعير والظهور</p>
                <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                  {createForm.delivery_fee.trim() ? `${createForm.delivery_fee} د.ج` : 'بدون سعر مباشر'}
                </p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  {createForm.visible_in_public ? 'متاح للعميل' : 'مخفي عن العميل'}
                </p>
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <button type="button" className="btn-secondary" onClick={() => { setCreateOpen(false); setCreateStep('basic'); }}>
              إلغاء
            </button>
            {createStep === 'review' ? (
              <button type="button" className="btn-secondary" onClick={() => setCreateStep('basic')}>
                رجوع
              </button>
            ) : null}
            {createStep === 'basic' ? (
              <button
                type="button"
                className="btn-primary"
                disabled={!nextLevel || !createForm.display_name.trim()}
                onClick={() => setCreateStep('review')}
              >
                مراجعة العنوان
              </button>
            ) : null}
            {createStep === 'review' ? (
              <button type="submit" className="btn-primary" disabled={createPending || !nextLevel}>
                {createPending ? 'جارٍ الحفظ...' : 'حفظ العنوان'}
              </button>
            ) : null}
          </div>

          {createError ? <p className="text-sm font-semibold text-rose-400">{createError}</p> : null}
          {createSuccess ? <p className="text-sm font-semibold text-emerald-400">{createSuccess}</p> : null}
        </form>
      </Modal>

      <Modal
        open={editOpen}
        onClose={() => {
          setEditOpen(false);
          setEditStep('basic');
        }}
        title={selectedNode ? `تعديل ${selectedNode.display_name}` : 'تعديل العنوان'}
        description="عدّل بيانات العنوان أولًا، ثم راجع التغييرات قبل الحفظ."
      >
        {selectedNode && editForm ? (
          <form className="space-y-4" onSubmit={handleEditSubmit}>
            <div className="grid gap-2 sm:grid-cols-2">
              {(
                [
                  { id: 'basic', label: '1. تعديل البيانات' },
                  { id: 'review', label: '2. مراجعة التغييرات' },
                ] as Array<{ id: AddressNodeModalStep; label: string }>
              ).map((stepCard) => {
                const active = editStep === stepCard.id;
                return (
                  <button
                    key={stepCard.id}
                    type="button"
                    onClick={() => {
                      if (stepCard.id === 'review' && !editForm.display_name.trim()) return;
                      setEditStep(stepCard.id);
                    }}
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

            {editStep === 'basic' ? (
              <NodeFormFields
                mode="edit"
                form={editForm}
                levelLabel={LEVEL_LABELS[selectedNode.level as TreeLevelKey] ?? selectedNode.level}
                directPricingExists={Boolean(selectedPricing)}
                quote={quote}
                onAdvancedToggle={() => setEditAdvancedOpen((value) => !value)}
                advancedOpen={editAdvancedOpen}
                onChange={(patch) => setEditForm((prev) => (prev ? { ...prev, ...patch } : prev))}
              />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                  <p className="text-xs font-bold text-[var(--text-muted)]">العنوان</p>
                  <p className="mt-1 font-black text-[var(--text-primary-strong)]">{editForm.display_name || '—'}</p>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    {LEVEL_LABELS[selectedNode.level as TreeLevelKey] ?? selectedNode.level}
                  </p>
                </div>
                <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-3 text-sm">
                  <p className="text-xs font-bold text-[var(--text-muted)]">التسعير والظهور</p>
                  <p className="mt-1 font-black text-[var(--text-primary-strong)]">
                    {editForm.remove_direct_pricing
                      ? 'إزالة السعر المباشر'
                      : editForm.delivery_fee.trim()
                        ? `${editForm.delivery_fee} د.ج`
                        : 'بدون سعر مباشر'}
                  </p>
                  <p className="mt-1 text-xs text-[var(--text-muted)]">
                    {editForm.visible_in_public ? 'متاح للعميل' : 'مخفي عن العميل'}
                  </p>
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <button type="button" className="btn-secondary" onClick={() => { setEditOpen(false); setEditStep('basic'); }}>
                إلغاء
              </button>
              {editStep === 'review' ? (
                <button
                  type="button"
                  className="btn-danger"
                  disabled={deletePending || editPending}
                  onClick={handleDeleteNode}
                >
                  {deletePending ? 'جارٍ الحذف...' : selectedNode.child_count > 0 ? 'حذف الفرع' : 'حذف العنوان'}
                </button>
              ) : null}
              {editStep === 'review' ? (
                <button type="button" className="btn-secondary" onClick={() => setEditStep('basic')}>
                  رجوع
                </button>
              ) : null}
              {editStep === 'basic' ? (
                <button
                  type="button"
                  className="btn-primary"
                  disabled={!editForm.display_name.trim()}
                  onClick={() => setEditStep('review')}
                >
                  مراجعة التغييرات
                </button>
              ) : null}
              {editStep === 'review' ? (
                <button type="submit" className="btn-primary" disabled={editPending}>
                  {editPending ? 'جارٍ الحفظ...' : 'حفظ التعديلات'}
                </button>
              ) : null}
            </div>

            {editError ? <p className="text-sm font-semibold text-rose-400">{editError}</p> : null}
            {editSuccess ? <p className="text-sm font-semibold text-emerald-400">{editSuccess}</p> : null}
          </form>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">اختر عنوانًا من الشجرة أولًا.</p>
        )}
      </Modal>
    </section>
  );
}
