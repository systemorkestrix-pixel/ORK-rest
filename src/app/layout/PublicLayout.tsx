import { useQuery } from '@tanstack/react-query';
import { Outlet, useLocation } from 'react-router-dom';

import type { StorefrontSettings } from '@/shared/api/types';
import { api } from '@/shared/api/client';
import { defaultStorefrontSettings, mergeStorefrontSettings } from '@/shared/storefront/storefrontMeta';
import { PublicShellHeader } from './PublicShellHeader';
import { PublicSiteFooter } from './PublicSiteFooter';

export interface PublicLayoutOutletContext {
  storefrontSettings: StorefrontSettings;
}

export function PublicLayout() {
  const location = useLocation();
  const tenantCode = location.pathname.match(/^\/t\/([^/]+)(?:\/|$)/i)?.[1] ?? 'public';

  const storefrontQuery = useQuery({
    queryKey: ['public-storefront-settings', tenantCode],
    queryFn: () => api.publicStorefrontSettings(),
    staleTime: 5 * 60_000,
  });

  const storefrontSettings = mergeStorefrontSettings(storefrontQuery.data ?? defaultStorefrontSettings);

  return (
    <div dir="rtl" className="min-h-screen bg-transparent text-[var(--app-text)]">
      <div className="relative flex min-h-screen flex-col">
        <PublicShellHeader settings={storefrontSettings} />

        <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-4 md:px-6 md:py-6">
          <Outlet context={{ storefrontSettings }} />
        </main>

        <PublicSiteFooter settings={storefrontSettings} />
      </div>
    </div>
  );
}
