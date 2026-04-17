import type { ReactNode } from 'react';

interface ContentPanelProps {
  children: ReactNode;
}

export function ContentPanel({ children }: ContentPanelProps) {
  return (
    <section className="console-content-layer console-panel-surface flex h-full min-h-0 flex-col rounded-2xl border">
      <div className="manager-section-shell console-panel-muted console-scrollbar flex-1 min-h-0 overflow-auto p-4 md:p-5">
        {children}
      </div>
    </section>
  );
}
