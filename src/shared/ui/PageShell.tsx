import type { ReactNode } from 'react';

interface PageShellProps {
  header?: ReactNode;
  toolbar?: ReactNode;
  children?: ReactNode;
  className?: string;
  workspaceClassName?: string;
}

export function PageShell({ header, toolbar, children, className, workspaceClassName }: PageShellProps) {
  return (
    <div className={['flex flex-col gap-4', className].filter(Boolean).join(' ')}>
      {header ? <div>{header}</div> : null}
      {toolbar ? <div>{toolbar}</div> : null}
      <div className={['min-h-0', workspaceClassName].filter(Boolean).join(' ')}>{children}</div>
    </div>
  );
}
