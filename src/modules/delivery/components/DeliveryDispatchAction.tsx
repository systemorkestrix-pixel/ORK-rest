import type { DeliveryDriver, DeliveryProvider, Order } from '@/shared/api/types';
import {
  canManageDeliveryDispatch,
  isAwaitingDispatchOffer,
  isAwaitingDispatchSelection,
  isOfferedDispatch,
} from '@/modules/delivery/shared/deliveryDispatchState';

interface DeliveryDispatchActionProps {
  order: Order;
  providers: DeliveryProvider[];
  drivers: DeliveryDriver[];
  autoNotifyTeam: boolean;
  selectedValue: string;
  onSelectedValueChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: (dispatchId: number) => void;
  submitPending: boolean;
  cancelPending: boolean;
  compact?: boolean;
}

export function DeliveryDispatchAction({
  order,
  providers,
  drivers,
  autoNotifyTeam,
  selectedValue,
  onSelectedValueChange,
  onSubmit,
  onCancel,
  submitPending,
  cancelPending,
  compact = false,
}: DeliveryDispatchActionProps) {
  if (!canManageDeliveryDispatch(order)) {
    return null;
  }

  const offeredDispatchId = order.delivery_dispatch_status === 'offered' && order.delivery_dispatch_id ? order.delivery_dispatch_id : null;
  const awaitingSelection = isAwaitingDispatchSelection(order, autoNotifyTeam);
  const awaitingOffer = isAwaitingDispatchOffer(order);
  const offered = isOfferedDispatch(order);

  if (offered && offeredDispatchId) {
    const targetLabel =
      order.delivery_dispatch_scope === 'driver'
        ? `مرسل إلى: ${order.delivery_dispatch_driver_name ?? '-'}`
        : `مرسل إلى: ${order.delivery_dispatch_provider_name ?? '-'}`;

    return (
      <div className={`flex w-full flex-col gap-2 ${compact ? 'min-w-0' : 'min-w-[220px]'}`}>
        <span className="rounded-xl border border-sky-200 bg-sky-50/80 px-3 py-2 text-center text-[12px] font-semibold text-sky-700">{targetLabel}</span>
        <button
          type="button"
          onClick={() => onCancel(offeredDispatchId)}
          disabled={cancelPending}
          className="btn-secondary ui-size-sm w-full"
        >
          {cancelPending ? 'جارٍ إلغاء العرض...' : 'إلغاء العرض'}
        </button>
      </div>
    );
  }

  if (!awaitingSelection && !awaitingOffer) {
    return null;
  }

  return (
    <div className={`flex w-full flex-col gap-2 ${compact ? 'min-w-0' : 'min-w-[220px]'}`}>
      <select
        className="form-select ui-size-sm"
        value={selectedValue}
        onChange={(event) => onSelectedValueChange(event.target.value)}
      >
        <option value="">اختر الجهة أو السائق</option>
        {providers
          .filter((provider) => provider.active)
          .map((provider) => (
            <option key={`provider-${provider.id}`} value={`provider:${provider.id}`}>
              جهة: {provider.name}
            </option>
          ))}
        {drivers
          .filter((driver) => driver.active && driver.status !== 'inactive')
          .map((driver) => (
            <option key={`driver-${driver.id}`} value={`driver:${driver.id}`}>
              سائق: {driver.name}
            </option>
          ))}
      </select>
      <button
        type="button"
        onClick={onSubmit}
        disabled={submitPending || !selectedValue}
        className="btn-primary ui-size-sm w-full"
      >
        {submitPending ? 'جارٍ الحفظ...' : awaitingSelection ? 'تحديد جهة التوصيل' : 'إرسال العرض'}
      </button>
    </div>
  );
}
