import type { LucideIcon } from 'lucide-react';
import { BarChart3, Boxes, ChefHat, ClipboardList, Truck, Wallet } from 'lucide-react';

export type ConsoleChannel =
  | 'operations'
  | 'kitchen'
  | 'delivery'
  | 'warehouse'
  | 'finance'
  | 'intelligence'
  | 'system';

interface ConsoleChannelDefinition {
  id: ConsoleChannel;
  label: string;
  icon: LucideIcon;
}

const CHANNELS: ConsoleChannelDefinition[] = [
  { id: 'operations', label: 'العمليات', icon: ClipboardList },
  { id: 'kitchen', label: 'المطبخ', icon: ChefHat },
  { id: 'delivery', label: 'التوصيل', icon: Truck },
  { id: 'warehouse', label: 'المستودع', icon: Boxes },
  { id: 'finance', label: 'المالية', icon: Wallet },
  { id: 'intelligence', label: 'التحليلات', icon: BarChart3 },
];

interface ChannelBarProps {
  activeChannel: ConsoleChannel | null;
  channels?: ConsoleChannel[];
  onSelectChannel: (channel: ConsoleChannel) => void;
}

export function ChannelBar({ activeChannel, channels, onSelectChannel }: ChannelBarProps) {
  const visibleChannels = CHANNELS.filter((channel) => !channels || channels.includes(channel.id));

  return (
    <nav className="console-channel-layer border-b border-[var(--console-border)] px-3 py-2 backdrop-blur tablet:px-6 tablet:py-3">
      <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 tablet:hidden">
        {visibleChannels.map((channel) => {
          const Icon = channel.icon;
          const isActive = channel.id === activeChannel;
          return (
            <button
              key={channel.id}
              type="button"
              onClick={() => onSelectChannel(channel.id)}
              className={`inline-flex min-h-[58px] min-w-[112px] shrink-0 items-center justify-center gap-2 rounded-2xl border px-4 py-3 text-sm font-black transition ${
                isActive
                  ? 'border-[#9a5a2a] bg-gradient-to-b from-[#b86b34] to-[#8e4f24] text-[#fff8ef] shadow-[0_6px_16px_rgba(80,48,24,0.22)]'
                  : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)] hover:border-[#b48552] hover:bg-[var(--surface-card-hover)] hover:text-[var(--text-primary)]'
              }`}
              aria-label={channel.label}
              title={channel.label}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span className="whitespace-nowrap text-[12px] font-black leading-none">{channel.label}</span>
            </button>
          );
        })}
      </div>

      <div
        className="hidden tablet:grid tablet:gap-2"
        style={{ gridTemplateColumns: `repeat(${Math.max(visibleChannels.length, 1)}, minmax(0, 1fr))` }}
      >
        {visibleChannels.map((channel) => {
          const Icon = channel.icon;
          const isActive = channel.id === activeChannel;
          return (
            <button
              key={channel.id}
              type="button"
              onClick={() => onSelectChannel(channel.id)}
              className={`inline-flex h-14 items-center justify-center gap-2 rounded-xl border px-3 text-sm font-black tracking-wide transition ${
                isActive
                  ? 'border-[#9a5a2a] bg-gradient-to-b from-[#b86b34] to-[#8e4f24] text-[#fff8ef] shadow-sm'
                  : 'border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)] hover:border-[#b48552] hover:bg-[var(--surface-card-hover)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Icon className="h-5 w-5" />
              <span>{channel.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
