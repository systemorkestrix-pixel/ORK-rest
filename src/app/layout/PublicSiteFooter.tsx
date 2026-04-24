import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';

import type { StorefrontSettings } from '@/shared/api/types';
import { getStorefrontSocialLabel, mergeStorefrontSettings, storefrontSocialOptions } from '@/shared/storefront/storefrontMeta';

interface PublicSiteFooterProps {
  settings?: StorefrontSettings | null;
}

export function PublicSiteFooter({ settings }: PublicSiteFooterProps) {
  const resolved = mergeStorefrontSettings(settings);
  const visibleSocials = resolved.socials.filter((row) => row.enabled && row.url);
  const [logoVisible, setLogoVisible] = useState(true);
  const brandLogoSrc = `${import.meta.env.BASE_URL}brand/logo.png`;

  return (
    <footer className="border-t border-[color:rgba(24,160,251,0.18)] bg-[#0b1220]/72 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-5 md:px-6">
        <div className="grid gap-3">
          <div className="grid w-full grid-cols-2 items-center gap-3" dir="ltr">
            <div className="inline-flex flex-row-reverse items-center justify-self-start gap-2" dir="ltr">
              <span className="shrink-0 text-sm font-black leading-none text-white md:text-base">
                {resolved.brand_mark || '.rest'}
              </span>
              {logoVisible ? (
                <img
                  src={brandLogoSrc}
                  alt={resolved.brand_name}
                  className="h-10 w-auto md:h-11"
                  loading="lazy"
                  onError={() => setLogoVisible(false)}
                />
              ) : (
                <span className="inline-flex h-10 min-w-[2.75rem] items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-3 text-xs font-black text-slate-200 md:h-11">
                  {resolved.brand_mark || resolved.brand_name.slice(0, 2)}
                </span>
              )}
            </div>

            <div className="justify-self-end space-y-1 text-right" dir="rtl">
              <p className="text-sm font-black text-[var(--app-text)]">{resolved.brand_name}</p>
              <p className="text-xs font-semibold text-slate-200/70">{resolved.brand_tagline}</p>
            </div>
          </div>

          {visibleSocials.length > 0 ? (
            <div className="flex flex-wrap items-center justify-center gap-2">
              {visibleSocials.map((row) => {
                const Icon = storefrontSocialOptions.find((option) => option.platform === row.platform)?.icon as LucideIcon | undefined;
                const accessibleLabel = getStorefrontSocialLabel(row.platform);
                return (
                  <a
                    key={row.platform}
                    href={row.url ?? '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-sm font-bold text-slate-200 transition hover:border-[color:var(--brand-gold)] hover:bg-white/10 hover:text-white md:h-11 md:w-11"
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
