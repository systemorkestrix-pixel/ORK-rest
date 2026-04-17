import { Navigate } from 'react-router-dom';

export function StockLedgerPage() {
  return <Navigate to="/console?channel=warehouse&section=warehouseItems" replace />;
}
