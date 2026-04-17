import { Clipboard, RefreshCw } from 'lucide-react';

import type { PublicOrderTracking } from '@/shared/api/types';
import { parseApiDateMs } from '@/shared/utils/date';
import { orderTypeLabel } from '@/shared/utils/order';
import {
  buildTrackingSteps,
  formatTrackingMoney,
  statusCardToneClasses,
  type TrackingPresentation,
  trackingTimeFormatter,
} from '../tracking.helpers';

interface TrackingStatusViewProps {
  trackedOrder: PublicOrderTracking;
  presentation: TrackingPresentation;
  isRefreshing: boolean;
  lastUpdatedAt: number | null;
  onCopyCode: () => void;
}

export function TrackingStatusView({
  trackedOrder,
  presentation,
  isRefreshing,
  lastUpdatedAt,
  onCopyCode,
}: TrackingStatusViewProps) {
  const steps = buildTrackingSteps(
    trackedOrder.type,
    trackedOrder.status,
    trackedOrder.payment_status ?? null,
    trackedOrder.workflow_profile,
  );

  return (
    <section className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(320px,0.88fr)_minmax(0,1.12fr)]">
        <article className={`rounded-[30px] border p-5 md:p-6 ${statusCardToneClasses[presentation.tone]}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.22em] opacity-80">TRACKING STATUS</p>
              <p className="mt-3 text-3xl font-black md:text-4xl">{presentation.label}</p>
              <h3 className="mt-3 text-lg font-black md:text-xl">{presentation.title}</h3>
              <p className="mt-3 max-w-xl text-sm leading-7 opacity-90">{presentation.description}</p>
            </div>
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/30 bg-white/15">
              <presentation.Icon className="h-5 w-5" />
            </span>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <TrackingMetric label="كود التتبع" value={trackedOrder.tracking_code} strong />
            <TrackingMetric label="نوع الطلب" value={orderTypeLabel(trackedOrder.type)} />
            <TrackingMetric
              label="وقت الإنشاء"
              value={trackingTimeFormatter.format(new Date(parseApiDateMs(trackedOrder.created_at)))}
            />
            <TrackingMetric label="الإجمالي" value={formatTrackingMoney(trackedOrder.total)} />
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onCopyCode}
              className="inline-flex min-h-[42px] items-center gap-2 rounded-2xl border border-white/20 bg-white/10 px-4 text-sm font-black text-white transition hover:bg-white/15"
            >
              <Clipboard className="h-4 w-4" />
              <span>نسخ الكود</span>
            </button>

            <span className="inline-flex min-h-[42px] items-center gap-2 rounded-2xl border border-white/15 bg-white/5 px-4 text-xs font-bold text-white/90">
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>تحديث تلقائي كل 5 ثوان</span>
              {lastUpdatedAt ? (
                <span className="text-white/70">آخر تحديث {trackingTimeFormatter.format(new Date(lastUpdatedAt))}</span>
              ) : null}
            </span>
          </div>
        </article>

        <article className="rounded-[30px] border border-white/10 bg-[#17110d] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.2)]">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-black tracking-[0.18em] text-stone-400">ORDER FLOW</p>
              <h3 className="mt-2 text-xl font-black text-white">رحلة الطلب</h3>
            </div>
            <span className="text-xs font-semibold text-stone-400">{presentation.hint}</span>
          </div>

          <div className="space-y-3">
            {steps.map((step, index) => (
              <TrackingStepRow
                key={step.key}
                index={index + 1}
                label={step.label}
                status={step.status}
                isLast={index === steps.length - 1}
              />
            ))}
          </div>
        </article>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <section className="rounded-[30px] border border-white/10 bg-[#17110d] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.2)]">
          <div className="mb-4 flex items-center justify-between gap-3">
            <p className="text-lg font-black text-white">تفاصيل الطلب</p>
            {trackedOrder.delivery_fee > 0 ? (
              <span className="text-xs font-semibold text-stone-400">
                رسوم التوصيل {formatTrackingMoney(trackedOrder.delivery_fee)}
              </span>
            ) : null}
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {trackedOrder.items.map((item) => (
              <div
                key={`${trackedOrder.tracking_code}-${item.id}`}
                className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-black/10 px-3 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-black text-white">{item.product_name}</p>
                  <p className="mt-1 text-xs font-semibold text-stone-400">× {item.quantity}</p>
                </div>
                <p className="shrink-0 text-sm font-black text-amber-300">
                  {formatTrackingMoney(item.price * item.quantity)}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          {trackedOrder.notes ? (
            <article className="rounded-[28px] border border-amber-300/35 bg-[linear-gradient(180deg,#fff6e7_0%,#fff0d7_100%)] p-4 shadow-[0_12px_30px_rgba(170,126,70,0.12)]">
              <p className="text-xs font-black tracking-[0.18em] text-[#9d5d24]">ORDER NOTE</p>
              <p className="mt-3 text-sm font-black text-[#2d2117]">ملاحظة الطلب</p>
              <p className="mt-2 text-sm leading-7 text-[#5b4837]">{trackedOrder.notes}</p>
            </article>
          ) : null}

          <article className="rounded-[28px] border border-white/10 bg-[#17110d] p-4 shadow-[0_18px_50px_rgba(0,0,0,0.18)]">
            <p className="text-xs font-black tracking-[0.18em] text-stone-400">ORDER SUMMARY</p>
            <div className="mt-4 grid gap-3">
              <TrackingSummaryRow label="عدد الأصناف" value={String(trackedOrder.items.length)} />
              <TrackingSummaryRow label="نوع الطلب" value={orderTypeLabel(trackedOrder.type)} />
              <TrackingSummaryRow label="الإجمالي النهائي" value={formatTrackingMoney(trackedOrder.total)} />
            </div>
          </article>
        </section>
      </div>
    </section>
  );
}

function TrackingMetric({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <article className="rounded-2xl border border-white/15 bg-white/6 px-4 py-4">
      <p className="text-xs font-semibold text-white/70">{label}</p>
      <p className={`mt-2 ${strong ? 'text-xl md:text-2xl' : 'text-lg'} font-black text-white`}>{value}</p>
    </article>
  );
}

function TrackingStepRow({
  index,
  label,
  status,
  isLast,
}: {
  index: number;
  label: string;
  status: 'completed' | 'current' | 'upcoming';
  isLast: boolean;
}) {
  const indicatorClass =
    status === 'completed'
      ? 'border-emerald-300 bg-emerald-400 text-[#0f172a]'
      : status === 'current'
        ? 'border-amber-300 bg-amber-300 text-[#0f172a]'
        : 'border-white/15 bg-white/5 text-white/55';

  const lineClass = status === 'completed' ? 'bg-emerald-400/60' : 'bg-white/10';

  return (
    <div className="flex items-start gap-3">
      <div className="flex w-10 shrink-0 flex-col items-center">
        <span className={`inline-flex h-10 w-10 items-center justify-center rounded-full border text-sm font-black ${indicatorClass}`}>
          {index}
        </span>
        {!isLast ? <span className={`mt-2 h-10 w-px ${lineClass}`} /> : null}
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
        <p className="text-sm font-black text-white">{label}</p>
        <p className="mt-1 text-xs font-semibold text-stone-400">
          {status === 'completed' ? 'اكتملت' : status === 'current' ? 'المرحلة الحالية' : 'بانتظار التنفيذ'}
        </p>
      </div>
    </div>
  );
}

function TrackingSummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
      <p className="text-xs font-semibold text-stone-400">{label}</p>
      <p className="text-sm font-black text-white">{value}</p>
    </div>
  );
}
