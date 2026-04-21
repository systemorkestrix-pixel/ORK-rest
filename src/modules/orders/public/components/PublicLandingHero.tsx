import type { ReactElement } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Bike, Search, Store, UtensilsCrossed } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

import type { StorefrontIconKey } from '@/shared/api/types';
import { resolveStorefrontIcon } from '@/shared/storefront/storefrontMeta';

interface PublicLandingHeroProps {
  brandMark: string;
  brandName: string;
  brandIcon: StorefrontIconKey;
  categoriesCount: number;
  totalProducts: number;
  deliveryEnabled: boolean;
  hasTableContext: boolean;
  hasActiveSession: boolean;
}

export function PublicLandingHero({
  brandMark,
  brandName,
  brandIcon,
  categoriesCount,
  totalProducts,
  deliveryEnabled,
  hasTableContext,
  hasActiveSession,
}: PublicLandingHeroProps) {
  const location = useLocation();
  const tenantPrefix = location.pathname.match(/^\/t\/[^/]+/i)?.[0] ?? '';
  const scopedTrackPath = tenantPrefix ? `${tenantPrefix}/track` : '/track';
  const BrandIcon: LucideIcon = resolveStorefrontIcon(brandIcon);

  return (
    <section className="overflow-hidden rounded-[34px] border border-[color:rgba(24,160,251,0.18)] bg-[radial-gradient(circle_at_top_right,rgba(232,166,89,0.18),transparent_30%),radial-gradient(circle_at_top_left,rgba(24,160,251,0.12),transparent_34%),linear-gradient(180deg,#fffaf3_0%,#f7ede0_100%)] p-5 shadow-[0_26px_64px_rgba(0,0,0,0.16)] md:p-7">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.95fr)] xl:items-stretch">
        <div className="flex flex-col justify-between gap-5">
          <div className="space-y-4">
            <div className="inline-flex w-fit items-center gap-3 rounded-full border border-[#eadbc7] bg-white/85 px-4 py-2">
              <span className="rounded-full bg-[var(--brand-gold)] px-2.5 py-1 text-xs font-black uppercase tracking-[0.24em] text-[#1a120d]">
                {brandMark}
              </span>
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[var(--brand-gold-soft)] text-[color:var(--brand-gold-strong)]">
                <BrandIcon className="h-4 w-4" />
              </span>
              <span className="text-xs font-bold text-[#725b45]">طلب سريع وواضح من أول خطوة</span>
            </div>

            <div>
              <h1 className="text-3xl font-black leading-tight text-[#2d2117] md:text-5xl">{brandName}</h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-[#6f5b49] md:text-base">
                اختر منتجك، راجع الطلب، ثم تابع حالته لحظة بلحظة من نفس الواجهة دون أي تعقيد.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to={scopedTrackPath}
              className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-2xl bg-[var(--brand-gold)] px-5 text-sm font-black text-[#1a120d] transition hover:bg-[var(--brand-gold-strong)]"
            >
              <Search className="h-4 w-4" />
              <span>تتبع الطلب</span>
            </Link>

            <span className="inline-flex min-h-[48px] items-center rounded-2xl border border-[#eadbc7] bg-white/85 px-4 text-xs font-black text-[#6d5845]">
              {deliveryEnabled ? 'التوصيل متاح' : 'الاستلام من المطعم'}
            </span>

            {hasTableContext ? (
              <span className="inline-flex min-h-[48px] items-center rounded-2xl border border-[color:var(--brand-blue)] bg-[var(--brand-blue-soft)] px-4 text-xs font-black text-[color:var(--brand-blue-strong)]">
                {hasActiveSession ? 'جلسة الطاولة نشطة' : 'الطلب مرتبط بهذه الطاولة'}
              </span>
            ) : null}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <HeroMetricCard
            label="أقسام المنيو"
            value={categoriesCount}
            icon={<UtensilsCrossed className="h-5 w-5" />}
            tone="amber"
          />
          <HeroMetricCard
            label="الأصناف المتاحة"
            value={totalProducts}
            icon={<Store className="h-5 w-5" />}
            tone="sky"
          />
          <HeroMetricCard
            label="طريقة الاستلام"
            value={deliveryEnabled ? 'استلام أو توصيل أو طاولة' : 'استلام أو طاولة'}
            icon={<Bike className="h-5 w-5" />}
            tone="emerald"
            wide
          />
        </div>
      </div>
    </section>
  );
}

function HeroMetricCard({
  label,
  value,
  icon,
  tone,
  wide = false,
}: {
  label: string;
  value: string | number;
  icon: ReactElement;
  tone: 'amber' | 'sky' | 'emerald';
  wide?: boolean;
}) {
  const toneClasses: Record<typeof tone, string> = {
    amber: 'bg-[var(--brand-gold-soft)] text-[color:var(--brand-gold-strong)]',
    sky: 'bg-[var(--brand-blue-soft)] text-[color:var(--brand-blue-strong)]',
    emerald: 'bg-[var(--brand-green-soft)] text-[color:var(--brand-green)]',
  };

  return (
    <article className={`rounded-[26px] border border-[#eadbc7] bg-white/82 p-4 ${wide ? 'sm:col-span-2' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-[#8b735d]">{label}</p>
          <p className="mt-2 text-xl font-black text-[#2d2117]">{value}</p>
        </div>
        <span className={`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${toneClasses[tone]}`}>{icon}</span>
      </div>
    </article>
  );
}
