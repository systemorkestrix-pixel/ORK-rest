import type { LucideIcon } from 'lucide-react';

import type { ConsoleChannel } from './ChannelBar';

export type ConsoleSection =
  | 'systemHub'
  | 'orders'
  | 'tables'
  | 'alerts'
  | 'menu'
  | 'kitchenMonitor'
  | 'kitchenSettings'
  | 'delivery'
  | 'deliverySettings'
  | 'warehouse'
  | 'warehouseOverview'
  | 'warehouseSuppliers'
  | 'warehouseItems'
  | 'warehouseBalances'
  | 'warehouseInbound'
  | 'warehouseOutbound'
  | 'warehouseCounts'
  | 'warehouseLedger'
  | 'staff'
  | 'financeOverview'
  | 'financeExpenses'
  | 'financeCashbox'
  | 'financeSettlements'
  | 'financeEntries'
  | 'financeClosures'
  | 'operationalHeart'
  | 'reports'
  | 'audit'
  | 'settings'
  | 'roles';

export interface ConsoleSectionCard {
  id: ConsoleSection;
  channel: ConsoleChannel;
  label: string;
  subtitle: string;
  icon: LucideIcon;
  metric?: number;
}

interface ChannelSectionBarProps {
  channel: ConsoleChannel;
  sections: ConsoleSectionCard[];
  activeSection: ConsoleSection | null;
  onOpenSection: (section: ConsoleSection) => void;
}

const CHANNEL_TITLES: Record<ConsoleChannel, string> = {
  operations: 'قناة العمليات',
  kitchen: 'قناة المطبخ',
  delivery: 'قناة التوصيل',
  warehouse: 'قناة المستودع',
  finance: 'قناة المالية',
  intelligence: 'قناة التحليلات',
  system: 'قناة النظام',
};

function formatMetric(metric: number): string {
  return metric > 99 ? '99+' : String(metric);
}

export function ChannelSectionBar({ channel, sections, activeSection, onOpenSection }: ChannelSectionBarProps) {
  if (sections.length === 0) {
    return null;
  }

  return (
    <nav
      className="console-channel-layer border-b border-[var(--console-border)] bg-[var(--surface-card-soft)]/55 px-3 py-2 backdrop-blur tablet:px-6 tablet:py-3"
      aria-label={CHANNEL_TITLES[channel]}
    >
      <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 tablet:mx-0 tablet:flex-wrap tablet:overflow-visible tablet:px-0 tablet:pb-0">
        {sections.map((section) => {
          const Icon = section.icon;
          const hasMetric = typeof section.metric === 'number' && section.metric > 0;
          const isActive = section.id === activeSection;

          return (
            <button
              key={section.id}
              type="button"
              onClick={() => onOpenSection(section.id)}
              className={`group inline-flex min-h-[58px] min-w-[146px] shrink-0 items-center justify-center gap-2 rounded-2xl border px-3 py-3 text-center text-sm font-black transition tablet:min-w-[168px] tablet:flex-1 tablet:gap-3 tablet:px-4 ${
                isActive
                  ? 'border-[#d0a06b] bg-[linear-gradient(180deg,rgba(76,56,41,0.98)_0%,rgba(55,39,29,0.98)_100%)] text-[#fff3e1] shadow-[inset_0_1px_0_rgba(255,232,204,0.12),0_10px_24px_rgba(0,0,0,0.18)]'
                  : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)] hover:border-[#b48552] hover:bg-[var(--surface-card-hover)] hover:text-[var(--text-primary)]'
              }`}
              title={section.subtitle}
              aria-pressed={isActive}
            >
              <span
                className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition ${
                  isActive
                    ? 'border-[#d9b284] bg-[#fff1dd] text-[#8a5428] shadow-[inset_0_1px_0_rgba(255,255,255,0.35)]'
                    : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)] group-hover:border-[#b48552] group-hover:bg-[var(--surface-card)] group-hover:text-[#f2c48e]'
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>

              <span className="truncate tracking-[0.01em]">{section.label}</span>

              {hasMetric ? (
                <span
                  className={`inline-flex min-w-6 shrink-0 items-center justify-center rounded-full border px-1.5 py-0.5 text-[11px] font-black leading-none ${
                    isActive
                      ? 'border-[#d9b284] bg-[#fff1dd] text-[#8a5428]'
                      : 'border-[#7c512c] bg-[#7c512c] text-[#fff3e1]'
                  }`}
                >
                  {formatMetric(section.metric)}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
