import { ChevronLeft, ShoppingBag } from 'lucide-react';

interface PublicCartSummaryBarProps {
  itemCount: number;
  total: number;
  onOpenCheckout: () => void;
}

export function PublicCartSummaryBar({ itemCount, total, onOpenCheckout }: PublicCartSummaryBarProps) {
  if (itemCount === 0) {
    return null;
  }

  const itemLabel = itemCount === 1 ? 'صنف' : 'أصناف';

  return (
    <div className="pointer-events-none sticky bottom-3 z-30 px-1 md:px-0">
      <div className="pointer-events-auto mx-auto max-w-5xl rounded-[28px] border border-[#eadbc7] bg-[#fffaf3]/96 shadow-[0_22px_48px_rgba(170,126,70,0.18)] backdrop-blur">
        <div className="grid gap-3 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:p-4">
          <div className="flex items-center gap-3">
            <div className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#fff2df] text-[#cf7f2a]">
              <ShoppingBag className="h-5 w-5" />
            </div>

            <div className="min-w-0">
              <p className="text-sm font-black text-[#2d2117]">السلة جاهزة</p>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-semibold text-[#7c6651]">
                <span>
                  {itemCount} {itemLabel}
                </span>
                <span className="text-[#d3b694]">•</span>
                <span>الإجمالي {total.toFixed(2)} د.ج</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onOpenCheckout}
            className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-2xl bg-[#e38b38] px-5 text-sm font-black text-[#1a120d] transition hover:bg-[#ef9a4b] sm:min-w-[220px] sm:w-auto"
          >
            <span>متابعة الطلب</span>
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
