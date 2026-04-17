import { Navigate } from 'react-router-dom';

export function WarehouseSuppliersPage() {
  return <Navigate to="/console?channel=warehouse&section=warehouseInbound" replace />;
}
