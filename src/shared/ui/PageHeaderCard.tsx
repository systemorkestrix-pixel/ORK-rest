import type { ReactNode } from 'react';

interface PageHeaderMetric {
  label: string;
  value: string | number;
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'info';
}

interface PageHeaderCardProps {
  title: string;
  description: string;
  icon?: ReactNode;
  actions?: ReactNode;
  metrics?: PageHeaderMetric[];
  metricsContainerClassName?: string;
}

const toneClassMap: Record<NonNullable<PageHeaderMetric['tone']>, string> = {
  default: 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-primary)]',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  danger: 'border-rose-200 bg-rose-50 text-rose-800',
  info: 'border-sky-200 bg-sky-50 text-sky-800',
};

export function PageHeaderCard({
  title,
  description,
  icon,
  actions,
  metrics = [],
  metricsContainerClassName,
}: PageHeaderCardProps) {
  return (
    <section className="admin-card space-y-3 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          {icon ? (
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-brand-100 bg-[var(--surface-card-soft)] text-[var(--text-secondary)]">
              {icon}
            </span>
          ) : null}
          <div>
            <h2 className="text-sm font-black text-[var(--text-primary-strong)] sm:text-base">{title}</h2>
            <p className="text-xs font-semibold text-[var(--text-muted)]">{description}</p>
          </div>
        </div>

        {actions ? <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">{actions}</div> : null}
      </div>

      {metrics.length > 0 ? (
        <div className={metricsContainerClassName ?? 'grid gap-2 sm:grid-cols-2 xl:grid-cols-3'}>
          {metrics.map((metric) => (
            <div
              key={`${metric.label}-${metric.value}`}
              className={`rounded-xl border px-3 py-2 ${toneClassMap[metric.tone ?? 'default']}`}
            >
              <p className="text-[11px] font-bold opacity-80">{metric.label}</p>
              <p className="mt-1 text-lg font-black">{metric.value}</p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
