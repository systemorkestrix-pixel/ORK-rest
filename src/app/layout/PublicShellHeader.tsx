import type { LucideIcon } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

import type { StorefrontSettings } from '@/shared/api/types';
import { mergeStorefrontSettings, resolveStorefrontIcon } from '@/shared/storefront/storefrontMeta';

interface PublicShellHeaderProps {
  settings?: StorefrontSettings | null;
}

interface NavigationItem {
  to: string;
  label: string;
}

export function PublicShellHeader({ settings }: PublicShellHeaderProps) {
  const location = useLocation();
  const tenantPrefix = location.pathname.match(/^\/t\/[^/]+/i)?.[0] ?? '';
  const scopedOrderPath = tenantPrefix ? `${tenantPrefix}/order` : null;
  const scopedTrackPath = tenantPrefix ? `${tenantPrefix}/track` : null;
  const navigationItems: NavigationItem[] = [
    ...(scopedOrderPath ? [{ to: scopedOrderPath, label: 'الطلب' }] : []),
    ...(scopedTrackPath ? [{ to: scopedTrackPath, label: 'التتبع' }] : []),
  ];
  const resolved = mergeStorefrontSettings(settings);
  const BrandIcon: LucideIcon = resolveStorefrontIcon(resolved.brand_icon);

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#0b1220]/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-3 md:px-6">
        {scopedOrderPath ? (
          <Link to={scopedOrderPath} className="flex min-w-0 items-center gap-3">
            <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-[var(--brand-blue-soft)] text-[var(--brand-blue)] shadow-[0_10px_28px_rgba(0,0,0,0.28)]">
              <BrandIcon className="h-4 w-4" />
            </span>
            <span className="truncate text-base font-black text-[var(--app-text)] md:text-lg">{resolved.brand_name}</span>
          </Link>
        ) : (
          <div className="flex min-w-0 items-center gap-3">
            <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-[var(--brand-blue-soft)] text-[var(--brand-blue)] shadow-[0_10px_28px_rgba(0,0,0,0.28)]">
              <BrandIcon className="h-4 w-4" />
            </span>
            <span className="truncate text-base font-black text-[var(--app-text)] md:text-lg">{resolved.brand_name}</span>
          </div>
        )}

        {navigationItems.length > 0 ? (
          <nav className="flex items-center gap-2">
            {navigationItems.map((item) => {
              const active = location.pathname === item.to || (item.to.endsWith('/order') && location.pathname.endsWith('/menu'));
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`inline-flex min-h-[40px] min-w-[84px] items-center justify-center rounded-2xl border px-4 text-sm font-black transition ${
                    active
                      ? 'border-[color:var(--brand-blue)] bg-[var(--brand-blue-soft)] text-white'
                      : 'border-white/10 bg-white/5 text-slate-200 hover:border-[color:var(--brand-blue)] hover:bg-[var(--brand-blue-soft)] hover:text-white'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        ) : null}
      </div>
    </header>
  );
}
