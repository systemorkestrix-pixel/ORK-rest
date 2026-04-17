import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  title: ReactNode;
  description?: string;
  open: boolean;
  onClose: () => void;
  headerActions?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
}

export function Modal({ title, description, open, onClose, headerActions, footer, children }: ModalProps) {
  if (!open || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-50 bg-black/40">
      <div className="flex h-full w-full items-stretch justify-center sm:items-center sm:p-4">
        <div className="flex h-[100dvh] w-full flex-col bg-[var(--surface-card)] shadow-[var(--console-shadow)] sm:h-auto sm:max-h-[88vh] sm:max-w-4xl sm:rounded-3xl sm:border sm:border-[var(--console-border)]">
          <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[var(--console-border)] bg-[var(--surface-card)] px-4 py-4 sm:rounded-t-3xl sm:px-6">
            <div className="min-w-0 flex-1">
              <h3 className="text-lg font-black text-[var(--text-primary-strong)]">{title}</h3>
              {description ? <p className="mt-1 text-sm text-[var(--text-muted)]">{description}</p> : null}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {headerActions}
              <button type="button" onClick={onClose} className="btn-secondary ui-size-sm shrink-0 px-3">
                إغلاق
              </button>
            </div>
          </div>

          <div className="console-scrollbar min-h-0 flex-1 overflow-y-auto p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:max-h-[74vh] sm:p-6">
            {children}
          </div>

          {footer ? (
            <div className="sticky bottom-0 z-10 border-t border-[var(--console-border)] bg-[var(--surface-card)] px-4 py-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:rounded-b-3xl sm:px-6">
              {footer}
            </div>
          ) : null}
        </div>
      </div>
    </div>,
    document.body
  );
}
