function sanitizeOrigin(value: string): string {
  return value.replace(/\/$/, '');
}

export function resolveBackendOrigin(): string {
  const explicitOrigin = (import.meta.env.VITE_BACKEND_ORIGIN as string | undefined)?.trim();
  if (explicitOrigin) {
    return sanitizeOrigin(explicitOrigin);
  }

  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  if (apiBaseUrl && /^https?:\/\//i.test(apiBaseUrl)) {
    try {
      return sanitizeOrigin(new URL(apiBaseUrl).origin);
    } catch {
      // Ignore malformed absolute URL and continue to safer fallbacks.
    }
  }

  if (typeof window !== 'undefined' && !import.meta.env.DEV && apiBaseUrl?.startsWith('/')) {
    return sanitizeOrigin(window.location.origin);
  }

  return 'http://127.0.0.1:8124';
}
