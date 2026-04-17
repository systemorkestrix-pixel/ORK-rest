import type { FormEvent } from 'react';
import { Clipboard, Search, ShoppingBag } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

interface TrackingLookupHeroProps {
  brandMark: string;
  trackingInput: string;
  trackingError: string;
  copyFeedback: string;
  isLoading: boolean;
  onTrackingInputChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function TrackingLookupHero({
  brandMark,
  trackingInput,
  trackingError,
  copyFeedback,
  isLoading,
  onTrackingInputChange,
  onSubmit,
}: TrackingLookupHeroProps) {
  const location = useLocation();
  const tenantPrefix = location.pathname.match(/^\/t\/[^/]+/i)?.[0] ?? '';
  const scopedOrderPath = tenantPrefix ? `${tenantPrefix}/order` : '/order';

  return (
    <section className="rounded-[28px] border border-white/10 bg-[#17110d] p-4 shadow-[0_18px_50px_rgba(0,0,0,0.2)] md:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.24em] text-amber-300">{brandMark}</p>
          <h1 className="mt-1 text-xl font-black text-white md:text-2xl">تتبع الطلب</h1>
        </div>
        <Link to={scopedOrderPath} className="btn-secondary gap-2 border-white/15 bg-white/5 text-stone-100">
          <ShoppingBag className="h-4 w-4" />
          العودة للطلب
        </Link>
      </div>

      <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_170px]">
        <label className="block">
          <span className="mb-2 block text-xs font-bold text-stone-400">كود التتبع</span>
          <input
            value={trackingInput}
            onChange={(event) => onTrackingInputChange(event.target.value.toUpperCase())}
            className="form-input border-white/10 bg-white/5 text-white placeholder:text-stone-500"
            placeholder="ORD-000123-ABC456"
            dir="ltr"
          />
        </label>

        <button type="submit" className="btn-primary gap-2 md:self-end" disabled={isLoading}>
          <Search className="h-4 w-4" />
          {isLoading ? 'جارٍ البحث...' : 'بحث'}
        </button>
      </form>

      {trackingError ? (
        <div className="mt-3 rounded-2xl border border-rose-500/35 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-200">
          {trackingError}
        </div>
      ) : null}

      {copyFeedback ? (
        <div className="mt-3 rounded-2xl border border-emerald-500/35 bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-200">
          <span className="inline-flex items-center gap-2">
            <Clipboard className="h-4 w-4" />
            {copyFeedback}
          </span>
        </div>
      ) : null}
    </section>
  );
}
