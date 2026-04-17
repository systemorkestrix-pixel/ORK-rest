import type { LucideIcon } from 'lucide-react';

import type { StorefrontSettings } from '@/shared/api/types';
import { getStorefrontSocialLabel, mergeStorefrontSettings, storefrontSocialOptions } from '@/shared/storefront/storefrontMeta';

interface PublicSiteFooterProps {
  settings?: StorefrontSettings | null;
}

export function PublicSiteFooter({ settings }: PublicSiteFooterProps) {
  const resolved = mergeStorefrontSettings(settings);
  const visibleSocials = resolved.socials.filter((row) => row.enabled && row.url);

  return (
    <footer className="border-t border-[#e8dcca] bg-[#fffaf3]">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-5 md:px-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1 text-right">
            <p className="text-sm font-black text-[#2f2218]">{resolved.brand_name}</p>
            <p className="text-xs font-semibold text-[#8b735d]">{resolved.brand_tagline}</p>
          </div>

          {visibleSocials.length > 0 ? (
            <div className="flex flex-wrap items-center justify-start gap-2 md:justify-end">
              {visibleSocials.map((row) => {
                const Icon = storefrontSocialOptions.find((option) => option.platform === row.platform)?.icon as LucideIcon | undefined;
                const accessibleLabel = getStorefrontSocialLabel(row.platform);
                return (
                  <a
                    key={row.platform}
                    href={row.url ?? '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#ead9bf] bg-white text-sm font-bold text-[#6b5642] transition hover:border-[#e0a05b] hover:bg-[#fff2df] hover:text-[#8a531c]"
                    aria-label={accessibleLabel}
                    title={accessibleLabel}
                  >
                    {Icon ? <Icon className="h-4 w-4" /> : null}
                  </a>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>
    </footer>
  );
}
