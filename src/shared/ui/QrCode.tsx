import { useEffect, useState } from 'react';
import QRCode from 'qrcode';

interface QrCodeProps {
  value: string;
  size?: number;
  className?: string;
}

function getThemeAwareQrColors() {
  if (typeof window === 'undefined') {
    return { dark: '#3a261b', light: '#fffaf2' };
  }

  const styles = window.getComputedStyle(document.documentElement);
  const dark = styles.getPropertyValue('--text-primary-strong').trim() || '#3a261b';
  const light = styles.getPropertyValue('--surface-card').trim() || '#fffaf2';
  return { dark, light };
}

export function QrCode({ value, size = 180, className = '' }: QrCodeProps) {
  const [dataUrl, setDataUrl] = useState<string>('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let active = true;
    setError('');
    if (!value) {
      setDataUrl('');
      return () => {
        active = false;
      };
    }

    const colors = getThemeAwareQrColors();

    QRCode.toDataURL(value, {
      width: size,
      margin: 1,
      color: colors,
    })
      .then((url) => {
        if (active) {
          setDataUrl(url);
        }
      })
      .catch(() => {
        if (active) {
          setDataUrl('');
          setError('تعذر توليد رمز الطاولة.');
        }
      });

    return () => {
      active = false;
    };
  }, [size, value]);

  if (!value) {
    return (
      <div className={`flex h-[180px] items-center justify-center rounded-xl border border-amber-200 bg-amber-50 text-xs font-semibold text-amber-700 ${className}`}>
        سيتم توليد الرمز بعد التأكيد.
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex h-[180px] items-center justify-center rounded-xl border border-rose-200 bg-rose-50 text-xs font-semibold text-rose-700 ${className}`}>
        {error}
      </div>
    );
  }

  return (
    <img
      src={dataUrl}
      width={size}
      height={size}
      alt="رمز الطاولة"
      className={`rounded-xl border border-[var(--console-border)] bg-[var(--surface-card)] p-2 shadow-[var(--console-shadow)] ${className}`}
    />
  );
}
