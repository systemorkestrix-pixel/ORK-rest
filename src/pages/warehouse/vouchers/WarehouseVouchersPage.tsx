import { Navigate } from 'react-router-dom';

export function WarehouseVouchersPage() {
  return <Navigate to="/console?channel=warehouse&section=warehouseInbound" replace />;
}
