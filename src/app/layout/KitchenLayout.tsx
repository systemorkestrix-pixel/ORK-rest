import { useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { ChefHat, ClipboardList, LogOut, Menu, X } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { sanitizeMojibakeText } from '@/shared/utils/textSanitizer';

const kitchenNavItems = [
  { to: '/kitchen/console/monitor', label: 'التنفيذ المباشر', icon: ChefHat },
  { to: '/kitchen/console/history', label: 'سجل الطلبات', icon: ClipboardList },
];

function isReadableKitchenIdentity(value: string): boolean {
  const normalized = value.trim();
  if (!normalized || normalized === 'جلسة المطبخ' || normalized === 'مستخدم المطبخ') {
    return false;
  }

  if (/[\u0600-\u06FF]/.test(normalized)) {
    return true;
  }

  if (/^[a-z0-9._-]{3,}$/i.test(normalized) && /[a-z]/i.test(normalized)) {
    return true;
  }

  if (/[A-Z]{3,}/.test(normalized) && /[\s()]/.test(normalized)) {
    return false;
  }

  return /^[A-Za-z0-9._-]+(?:\s[A-Za-z0-9._-]+)?$/.test(normalized);
}

function resolveKitchenDisplayName(name: string | undefined, username: string | undefined): string {
  const normalizedName = sanitizeMojibakeText(name, '');
  if (isReadableKitchenIdentity(normalizedName)) {
    return normalizedName;
  }

  const normalizedUsername = sanitizeMojibakeText(username, '');
  if (isReadableKitchenIdentity(normalizedUsername)) {
    return normalizedUsername;
  }

  return 'مستخدم المطبخ';
}

function kitchenNavClass(isActive: boolean): string {
  return isActive
    ? 'border-[#b98757] bg-[var(--surface-card)] text-[var(--text-primary-strong)] shadow-[var(--console-shadow)]'
    : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)] hover:border-[#b98757] hover:text-[var(--text-primary)]';
}

export function KitchenLayout() {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const displayName = useMemo(() => resolveKitchenDisplayName(user?.name, user?.username), [user?.name, user?.username]);

  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isMenuOpen || window.innerWidth >= 1024) {
      return;
    }
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [isMenuOpen]);

  return (
    <div className="min-h-screen bg-[var(--surface-page)] text-[var(--text-primary)]">
      <div className="mx-auto flex min-h-screen max-w-[1920px] flex-col">
        <button
          type="button"
          aria-label="إغلاق قائمة المطبخ"
          onClick={() => setIsMenuOpen(false)}
          className={`fixed inset-0 z-30 bg-[#1f1712]/45 transition-opacity lg:hidden ${
            isMenuOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
          }`}
        />

        <aside
          className={`fixed inset-y-0 right-0 z-40 flex w-[84vw] max-w-sm flex-col border-l border-[var(--console-border)] bg-[var(--surface-card)] p-4 shadow-[var(--console-shadow)] transition-transform lg:hidden ${
            isMenuOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="flex items-start justify-between gap-3 rounded-3xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
            <div>
              <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">KITCHEN CONSOLE</p>
              <h2 className="mt-2 text-lg font-black text-[var(--text-primary-strong)]">لوحة المطبخ</h2>
              <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">{displayName}</p>
            </div>
            <button
              type="button"
              onClick={() => setIsMenuOpen(false)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] text-[var(--text-secondary)]"
              aria-label="إغلاق"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <nav className="mt-4 space-y-2">
            {kitchenNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 transition ${kitchenNavClass(isActive)}`
                  }
                >
                  <span className="text-sm font-black">{item.label}</span>
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-[#f3b36b]">
                    <Icon className="h-4 w-4" />
                  </span>
                </NavLink>
              );
            })}
          </nav>

          <button
            type="button"
            onClick={logout}
            className="mt-auto inline-flex min-h-[46px] items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 text-sm font-black text-rose-700"
          >
            <LogOut className="h-4 w-4" />
            <span>تسجيل الخروج</span>
          </button>
        </aside>

        <header className="sticky top-0 z-20 border-b border-[var(--console-border)] bg-[var(--surface-card)]/95 backdrop-blur">
          <div className="mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-3 px-4 py-4 md:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setIsMenuOpen((previous) => !previous)}
                aria-expanded={isMenuOpen}
                className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)] lg:hidden"
              >
                <Menu className="h-4 w-4" />
              </button>

              <div className="inline-flex h-12 w-12 items-center justify-center rounded-3xl border border-[#d9b17e] bg-[#fff3df] text-[#b86d28]">
                <ChefHat className="h-5 w-5" />
              </div>

              <div>
                <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">KITCHEN CONSOLE</p>
                <h1 className="mt-1 text-xl font-black text-[var(--text-primary-strong)]">تشغيل المطبخ</h1>
              </div>
            </div>

            <div className="hidden items-center gap-2 lg:flex">
              {kitchenNavItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `inline-flex min-h-[44px] items-center gap-2 rounded-2xl border px-4 text-sm font-black transition ${kitchenNavClass(isActive)}`
                    }
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden text-left sm:block">
                <p className="text-[11px] font-bold text-[var(--text-muted)]">المستخدم الحالي</p>
                <p className="text-sm font-black text-[var(--text-primary)]">{displayName}</p>
              </div>
              <button
                type="button"
                onClick={logout}
                className="hidden min-h-[44px] items-center gap-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 text-sm font-black text-[var(--text-primary)] transition hover:border-[#b98757] lg:inline-flex"
              >
                <LogOut className="h-4 w-4" />
                <span>تسجيل الخروج</span>
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-4 md:px-8 md:py-6">
          <div className="mx-auto max-w-[1680px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
