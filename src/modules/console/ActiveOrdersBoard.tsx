import { OrdersPage } from '@/modules/operations/orders/OrdersPage';

interface ActiveOrdersBoardProps {
  createRequestToken?: number;
}

export function ActiveOrdersBoard({ createRequestToken = 0 }: ActiveOrdersBoardProps) {
  return <OrdersPage scope="console" showCreateButton={false} createRequestToken={createRequestToken} />;
}
