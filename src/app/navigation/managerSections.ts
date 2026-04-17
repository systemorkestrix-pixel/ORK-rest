import type { LucideIcon } from 'lucide-react';
import { BarChart3, Boxes, ChefHat, ClipboardList, Truck, UtensilsCrossed, Wallet } from 'lucide-react';

export const MANAGER_DASHBOARD_ROUTE = '/console';

export interface ManagerSectionDefinition {
  to: string;
  label: string;
  capability: string;
  description: string;
  icon: LucideIcon;
}

export const MANAGER_SECTIONS: ManagerSectionDefinition[] = [
  {
    to: '/console/operations/orders',
    label: 'العمليات',
    capability: 'manager.orders.view',
    description: 'إدارة الطلبات والطاولات والمسارات التشغيلية.',
    icon: ClipboardList,
  },
  {
    to: '/console/operations/menu',
    label: 'المنيو',
    capability: 'manager.products.view',
    description: 'إدارة قائمة الطعام والتصنيفات وبنية المنتجات.',
    icon: UtensilsCrossed,
  },
  {
    to: '/console/kitchen/monitor',
    label: 'المطبخ',
    capability: 'manager.kitchen_monitor.view',
    description: 'مراقبة طابور المطبخ وحالة التحضير من داخل لوحة المطعم.',
    icon: ChefHat,
  },
  {
    to: '/console/delivery/drivers',
    label: 'التوصيل',
    capability: 'manager.delivery.view',
    description: 'إدارة مهام المندوبين وحالات التسليم الميدانية.',
    icon: Truck,
  },
  {
    to: '/console/warehouse',
    label: 'المستودع',
    capability: 'manager.warehouse.view',
    description: 'الموردون والأصناف والاستلام والصرف والجرد في مكان واحد.',
    icon: Boxes,
  },
  {
    to: '/console/finance/transactions',
    label: 'المالية',
    capability: 'manager.financial.view',
    description: 'المبيعات والإغلاقات وتسوية النقد اليومية.',
    icon: Wallet,
  },
  {
    to: '/console/intelligence/operational-heart',
    label: 'التحليلات',
    capability: 'manager.reports.view',
    description: 'مؤشرات الأداء والتحليل التشغيلي والمالي.',
    icon: BarChart3,
  },
];

function sectionBasePath(path: string): string {
  const segments = path.split('/').filter(Boolean);
  if (segments.length >= 2) {
    return `/${segments[0]}/${segments[1]}`;
  }
  return path;
}

export function resolveManagerSectionFromPath(pathname: string): ManagerSectionDefinition | null {
  if (pathname === MANAGER_DASHBOARD_ROUTE) {
    return null;
  }
  for (const section of MANAGER_SECTIONS) {
    const basePath = sectionBasePath(section.to);
    if (pathname === basePath || pathname.startsWith(`${basePath}/`)) {
      return section;
    }
  }
  return null;
}
