import type { OrderPaymentStatus, OrderStatus, OrderType } from '../api/types';
import { resolveOrderStatusLabel, statusClasses } from '../utils/order';
import { TABLE_STATUS_CHIP_BASE } from './tableAppearance';

interface StatusBadgeProps {
  status: OrderStatus;
  orderType?: OrderType;
  paymentStatus?: OrderPaymentStatus | null;
}

export function StatusBadge({ status, orderType, paymentStatus }: StatusBadgeProps) {
  return (
    <span
      className={`${TABLE_STATUS_CHIP_BASE} ${statusClasses[status]}`}
    >
      {resolveOrderStatusLabel(status, orderType, paymentStatus)}
    </span>
  );
}
