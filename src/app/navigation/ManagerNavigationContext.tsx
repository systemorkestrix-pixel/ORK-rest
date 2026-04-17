import { createContext, type PropsWithChildren, useCallback, useContext, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Bell, Layers3, Settings, Users } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import {
  MANAGER_DASHBOARD_ROUTE,
  MANAGER_SECTIONS,
  type ManagerSectionDefinition,
  resolveManagerSectionFromPath,
} from './managerSections';

interface ManagerNavigationContextValue {
  sections: ManagerSectionDefinition[];
  currentSection: ManagerSectionDefinition | null;
  isDashboard: boolean;
  pageTitle: string;
  navigateToSection: (to: string) => void;
  navigateToDashboard: () => void;
}

const ManagerNavigationContext = createContext<ManagerNavigationContextValue | null>(null);

export function ManagerNavigationProvider({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);

  const sections = useMemo(() => {
    if (!Array.isArray(user?.permissions_effective)) {
      return MANAGER_SECTIONS;
    }
    const granted = new Set(user.permissions_effective);
    return MANAGER_SECTIONS.filter((section) => granted.has(section.capability));
  }, [user?.permissions_effective]);

  const currentSection = useMemo(() => {
    if (location.pathname === '/console/system') {
      return {
        to: '/console/system',
        label: 'إدارة الموظفين',
        capability: 'manager.users.view',
        description: 'إدارة موظفي المطعم ومعلوماتهم العملية من مكان واحد.',
        icon: Users,
      };
    }
    if (location.pathname.startsWith('/console/alerts')) {
      return {
        to: '/console/alerts',
        label: 'التنبيهات',
        capability: 'manager.orders.view',
        description: 'مراجعة الحالات التي تحتاج متابعة فورية من مكان واحد.',
        icon: Bell,
      };
    }
    if (location.pathname.startsWith('/console/system/settings')) {
      return {
        to: '/console/system/settings',
        label: 'الإعدادات',
        capability: 'manager.settings.view',
        description: 'إعدادات محلية تخص الواجهة العامة والحساب فقط.',
        icon: Settings,
      };
    }
    if (location.pathname.startsWith('/console/plans')) {
      return {
        to: '/console/plans',
        label: 'الإضافات',
        capability: 'manager.dashboard.view',
        description: 'عرض الأدوات المفعلة الآن، وما الأداة التالية التي يمكن فتحها.',
        icon: Layers3,
      };
    }
    if (location.pathname.startsWith('/console/system/users')) {
      return {
        to: '/console/system/users',
        label: 'إدارة الموظفين',
        capability: 'manager.users.view',
        description: 'إدارة موظفي المطعم داخل نفس المسار.',
        icon: Users,
      };
    }
    if (location.pathname.startsWith('/console/system/audit-log')) {
      return {
        to: '/console/system/settings',
        label: 'الإعدادات',
        capability: 'manager.settings.view',
        description: 'هذا المسار لم يعد جزءًا من لوحة المطعم الحالية.',
        icon: Settings,
      };
    }
    if (location.pathname.startsWith('/console/system/roles')) {
      return {
        to: '/console/system/settings',
        label: 'الإعدادات',
        capability: 'manager.settings.view',
        description: 'هذا المسار لم يعد جزءًا من لوحة المطعم الحالية.',
        icon: Settings,
      };
    }
    const resolved = resolveManagerSectionFromPath(location.pathname);
    if (resolved) {
      return resolved;
    }
    return sections.find((section) => location.pathname.startsWith(section.to)) ?? null;
  }, [location.pathname, sections]);

  const isDashboard = location.pathname === MANAGER_DASHBOARD_ROUTE;

  const pageTitle = useMemo(() => {
    if (isDashboard) {
      return 'لوحة المتابعة التشغيلية';
    }
    return currentSection?.label ?? 'الإدارة';
  }, [currentSection?.label, isDashboard]);

  const navigateToSection = useCallback(
    (to: string) => {
      navigate(to);
    },
    [navigate]
  );

  const navigateToDashboard = useCallback(() => {
    navigate(MANAGER_DASHBOARD_ROUTE);
  }, [navigate]);

  const value = useMemo<ManagerNavigationContextValue>(
    () => ({
      sections,
      currentSection,
      isDashboard,
      pageTitle,
      navigateToSection,
      navigateToDashboard,
    }),
    [sections, currentSection, isDashboard, pageTitle, navigateToSection, navigateToDashboard]
  );

  return <ManagerNavigationContext.Provider value={value}>{children}</ManagerNavigationContext.Provider>;
}

export function useManagerNavigation(): ManagerNavigationContextValue {
  const context = useContext(ManagerNavigationContext);
  if (!context) {
    throw new Error('useManagerNavigation must be used within ManagerNavigationProvider');
  }
  return context;
}
