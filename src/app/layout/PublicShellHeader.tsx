import type { LucideIcon } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

import type { StorefrontSettings } from '@/shared/api/types';
import { mergeStorefrontSettings, resolveStorefrontIcon } from '@/shared/storefront/storefrontMeta';

interface PublicShellHeaderProps {
  settings?: StorefrontSettings | null;
}

export function PublicShellHeader({ settings }: PublicShellHeaderProps) {
  const location = useLocation();
  const tenantPrefix = location.pathname.match(/^\/t\/[^/]+/i)?.[0] ?? '';
  const scopedOrderPath = tenantPrefix ? `${tenantPrefix}/order` : '/order';
  const scopedTrackPath = tenantPrefix ? `${tenantPrefix}/track` : '/track';
  const navigationItems = [
    { to: scopedOrderPath, label: 'الطلب' },
    { to: scopedTrackPath, label: 'التتبع' },
  ];
  const resolved = mergeStorefrontSettings(settings);
  const BrandIcon: LucideIcon = resolveStorefrontIcon(resolved.brand_icon);

  return (
    <header className="sticky top-0 z-30 border-b border-[#e8dcca] bg-[#fffaf3]/92 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-4 md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link to={scopedOrderPath} className="flex min-w-0 items-center gap-3">
            <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-[#ead9bf] bg-[#fff3df] text-[#d2852f] shadow-[0_10px_28px_rgba(170,126,70,0.16)]">
              <BrandIcon className="h-5 w-5" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-base font-black text-[#2f2218] md:text-lg">{resolved.brand_name}</span>
              <span className="block truncate text-xs font-semibold text-[#8b735d]">{resolved.brand_tagline}</span>
            </span>
          </Link>

          <nav className="flex w-full flex-wrap items-center justify-end gap-2 sm:w-auto">
            {navigationItems.map((item) => {
              const active =
                location.pathname === item.to ||
                (item.to.endsWith('/order') && location.pathname.endsWith('/menu'));
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`inline-flex min-h-[42px] items-center justify-center rounded-2xl border px-4 text-sm font-black transition ${
                    active
                      ? 'border-[#e3a056] bg-[#fff1dd] text-[#8a531c]'
                      : 'border-[#e8dcca] bg-white/70 text-[#695543] hover:bg-[#fff5e7] hover:text-[#2f2218]'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
