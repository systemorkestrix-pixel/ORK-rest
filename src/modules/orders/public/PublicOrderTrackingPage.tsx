import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PackageCheck } from 'lucide-react';
import { useLocation, useOutletContext, useSearchParams } from 'react-router-dom';

import type { PublicLayoutOutletContext } from '@/app/layout/PublicLayout';
import { api } from '@/shared/api/client';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';
import { TrackingLookupHero } from './components/TrackingLookupHero';
import { TrackingStatusView } from './components/TrackingStatusView';
import { autoRefreshMs, resolveTrackingPresentation } from './tracking.helpers';

export function PublicOrderTrackingPage() {
  const { storefrontSettings } = useOutletContext<PublicLayoutOutletContext>();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const tenantCode = location.pathname.match(/^\/t\/([^/]+)(?:\/|$)/i)?.[1] ?? 'public';
  const urlCode = (searchParams.get('code') ?? '').trim().toUpperCase();

  const [trackingInput, setTrackingInput] = useState(urlCode);
  const [submittedCode, setSubmittedCode] = useState(urlCode);
  const [trackingError, setTrackingError] = useState('');
  const [copyFeedback, setCopyFeedback] = useState('');

  useEffect(() => {
    setTrackingInput(urlCode);
    if (urlCode.length >= 8) {
      setSubmittedCode(urlCode);
      setTrackingError('');
    }
  }, [urlCode]);

  useEffect(() => {
    if (!copyFeedback) {
      return;
    }
    const timeout = window.setTimeout(() => setCopyFeedback(''), 2200);
    return () => window.clearTimeout(timeout);
  }, [copyFeedback]);

  const trackingQuery = useQuery({
    queryKey: ['public-order-tracking', tenantCode, submittedCode],
    queryFn: () => api.publicTrackOrder(submittedCode, Date.now()),
    enabled: submittedCode.length >= 8,
    refetchInterval: adaptiveRefetchInterval(autoRefreshMs, {
      minimumMs: autoRefreshMs,
      maximumMs: autoRefreshMs,
      pauseWhenHidden: false,
    }),
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    retry: false,
  });

  useEffect(() => {
    if (!trackingQuery.isError) {
      return;
    }
    setTrackingError(trackingQuery.error instanceof Error ? trackingQuery.error.message : 'تعذر تتبع الطلب بهذا الكود.');
  }, [trackingQuery.error, trackingQuery.isError]);

  useEffect(() => {
    if (!trackingQuery.data) {
      return;
    }
    setTrackingError('');
    if (trackingQuery.data.tracking_code && trackingQuery.data.tracking_code !== urlCode) {
      setSearchParams({ code: trackingQuery.data.tracking_code }, { replace: true });
    }
  }, [setSearchParams, trackingQuery.data, urlCode]);

  const submitTrackingLookup = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = trackingInput.trim().toUpperCase();
    if (normalized.length < 8) {
      setTrackingError('أدخل كود التتبع كاملًا كما وصلك بعد اعتماد الطلب.');
      return;
    }
    setCopyFeedback('');
    setTrackingError('');
    setSubmittedCode(normalized);
    setSearchParams({ code: normalized }, { replace: true });
  };

  const copyCode = async () => {
    if (!trackingQuery.data?.tracking_code) {
      return;
    }
    try {
      await navigator.clipboard.writeText(trackingQuery.data.tracking_code);
      setCopyFeedback('تم نسخ كود التتبع.');
    } catch {
      setCopyFeedback('تعذر نسخ الكود الآن.');
    }
  };

  const presentation = useMemo(
    () =>
      trackingQuery.data
        ? resolveTrackingPresentation(
            trackingQuery.data.status,
            trackingQuery.data.type,
            trackingQuery.data.payment_status ?? null,
            trackingQuery.data.workflow_profile,
          )
        : null,
    [trackingQuery.data],
  );

  return (
    <div dir="rtl" className="mx-auto max-w-6xl space-y-4">
      <TrackingLookupHero
        brandMark={storefrontSettings.brand_mark}
        trackingInput={trackingInput}
        trackingError={trackingError}
        copyFeedback={copyFeedback}
        isLoading={trackingQuery.isLoading}
        onTrackingInputChange={setTrackingInput}
        onSubmit={submitTrackingLookup}
      />

      {trackingQuery.data && presentation ? (
        <TrackingStatusView
          trackedOrder={trackingQuery.data}
          presentation={presentation}
          isRefreshing={trackingQuery.isFetching && !trackingQuery.isLoading}
          lastUpdatedAt={trackingQuery.dataUpdatedAt || null}
          onCopyCode={copyCode}
        />
      ) : (
        <section className="rounded-[28px] border border-dashed border-white/10 bg-[#17110d] px-6 py-14 text-center shadow-[0_18px_50px_rgba(0,0,0,0.18)]">
          <PackageCheck className="mx-auto h-10 w-10 text-stone-500" />
          <p className="mt-4 text-lg font-black text-white md:text-xl">أدخل كود التتبع لتظهر البيانات مباشرة</p>
        </section>
      )}
    </div>
  );
}
