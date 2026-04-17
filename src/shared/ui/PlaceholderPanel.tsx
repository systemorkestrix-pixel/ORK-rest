interface PlaceholderPanelProps {
  title: string;
  description?: string;
}

export function PlaceholderPanel({ title, description }: PlaceholderPanelProps) {
  return (
    <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-6 text-[var(--text-primary)] shadow-[var(--console-shadow)]">
      <h2 className="text-lg font-bold text-[var(--text-primary-strong)]">{title}</h2>
      <p className="mt-2 text-sm text-[var(--text-muted)]">
        {description ?? 'هذه الصفحة مهيأة وجاهزة للاستكمال عند الحاجة.'}
      </p>
    </div>
  );
}
