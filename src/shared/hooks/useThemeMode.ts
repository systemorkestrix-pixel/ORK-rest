import { useEffect, useMemo, useState } from 'react';

export type ThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'restaurants-theme-mode';

function resolveInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'light';
  }

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') {
    return stored;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function useThemeMode() {
  const [mode, setMode] = useState<ThemeMode>(resolveInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = mode;
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const isDark = useMemo(() => mode === 'dark', [mode]);
  const toggleTheme = () => setMode((current) => (current === 'dark' ? 'light' : 'dark'));

  return {
    mode,
    isDark,
    toggleTheme,
  };
}
