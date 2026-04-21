import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { StorefrontSettings } from '@/shared/api/types';
import {
  defaultStorefrontSettings,
  mergeStorefrontSettings,
  normalizeStorefrontSocialUrl,
  resolveStorefrontIcon,
  storefrontIconOptions,
  storefrontSocialOptions,
} from '@/shared/storefront/storefrontMeta';

export function StorefrontSettingsPanel() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();
  const [form, setForm] = useState<StorefrontSettings>(defaultStorefrontSettings);

  const publicOrderUrl = useMemo(() => {
    if (typeof window === 'undefined') {
      return '/order';
    }
    const tenantCode = window.sessionStorage.getItem('active_tenant_code')?.trim();
    return tenantCode ? `/t/${encodeURIComponent(tenantCode)}/order` : '/order';
  }, []);

  const storefrontQuery = useQuery({
    queryKey: ['manager-storefront-settings'],
    queryFn: () => api.managerStorefrontSettings(role ?? 'manager'),
    enabled: role === 'manager',
  });

  useEffect(() => {
    if (storefrontQuery.data) {
      setForm(mergeStorefrontSettings(storefrontQuery.data));
    }
  }, [storefrontQuery.data]);

  const updateMutation = useMutation({
    mutationFn: (payload: StorefrontSettings) => api.managerUpdateStorefrontSettings(role ?? 'manager', payload),
    onSuccess: (result) => {
      const normalized = mergeStorefrontSettings(result);
      setForm(normalized);
      queryClient.invalidateQueries({ queryKey: ['manager-storefront-settings'] });
      queryClient.invalidateQueries({ queryKey: ['public-storefront-settings'] });
    },
  });

  const BrandPreviewIcon = useMemo(() => resolveStorefrontIcon(form.brand_icon), [form.brand_icon]);

  if (role !== 'manager') {
    return null;
  }

  const errorText = updateMutation.isError
    ? updateMutation.error instanceof Error
      ? updateMutation.error.message
      : 'تعذر حفظ إعدادات الواجهة العامة.'
    : '';

  return (
    <section className="admin-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 className="text-sm font-black text-gray-800">هوية الواجهة العامة</h3>
          <p className="text-xs text-gray-600">عدّل اسم الواجهة والأيقونة وروابط التواصل التي تظهر للزائر.</p>
        </div>
        <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#120d09] px-4 py-3 text-right shadow-[0_16px_30px_rgba(0,0,0,0.18)]">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-[#f3b36b]">
            <BrandPreviewIcon className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-black text-white">{form.brand_name}</p>
            <p className="text-xs font-semibold text-stone-400">{form.brand_tagline || 'بدون سطر تعريفي'}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="space-y-1">
          <span className="form-label">اسم الواجهة</span>
          <input
            className="form-input"
            value={form.brand_name}
            onChange={(event) => setForm((prev) => ({ ...prev, brand_name: event.target.value }))}
            placeholder="اسم الواجهة العامة"
          />
        </label>
        <label className="space-y-1">
          <span className="form-label">شارة الاسم المختصرة</span>
          <input
            className="form-input"
            value={form.brand_mark}
            onChange={(event) => setForm((prev) => ({ ...prev, brand_mark: event.target.value }))}
            placeholder="مثال: sPeeD SyS"
          />
        </label>
        <label className="space-y-1">
          <span className="form-label">الأيقونة</span>
          <select
            className="form-select"
            value={form.brand_icon}
            onChange={(event) => setForm((prev) => ({ ...prev, brand_icon: event.target.value as StorefrontSettings['brand_icon'] }))}
          >
            {storefrontIconOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="form-label">سطر تعريفي مختصر</span>
          <input
            className="form-input"
            value={form.brand_tagline ?? ''}
            onChange={(event) => setForm((prev) => ({ ...prev, brand_tagline: event.target.value }))}
            placeholder="مثال: وجباتك جاهزة بخطوات أوضح."
          />
        </label>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {storefrontSocialOptions.map((option) => {
          const row = form.socials.find((item) => item.platform === option.platform) ?? {
            platform: option.platform,
            url: '',
            enabled: false,
          };

          return (
            <div key={option.platform} className="rounded-2xl border border-gray-200 bg-gray-50 px-3 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-gray-200 bg-white text-[#8a5428]">
                    <option.icon className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-sm font-black text-gray-800">{option.label}</p>
                    <p className="text-xs text-gray-500">أدخل الرابط أو الرقم ثم فعّل الظهور.</p>
                  </div>
                </div>
                <label className="inline-flex items-center gap-2 text-xs font-bold text-gray-700">
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    onChange={(event) =>
                      setForm((prev) => ({
                        ...prev,
                        socials: prev.socials.map((item) =>
                          item.platform === option.platform ? { ...item, enabled: event.target.checked } : item,
                        ),
                      }))
                    }
                  />
                  إظهار
                </label>
              </div>

              <div className="mt-3">
                <input
                  className="form-input"
                  value={row.url ?? ''}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      socials: prev.socials.map((item) =>
                        item.platform === option.platform ? { ...item, url: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder={option.platform === 'whatsapp' ? 'أدخل الرقم أو الرابط' : 'أدخل الرابط'}
                  dir="ltr"
                />
              </div>
            </div>
          );
        })}
      </div>

      {errorText ? <p className="mt-3 text-xs font-semibold text-rose-700">{errorText}</p> : null}
      {updateMutation.isSuccess ? <p className="mt-3 text-xs font-semibold text-emerald-700">تم حفظ هوية الواجهة العامة بنجاح.</p> : null}

      <button
        type="button"
        className="btn-secondary mt-4 w-full justify-center"
        onClick={() => window.open(publicOrderUrl, '_blank', 'noopener,noreferrer')}
      >
        <ExternalLink className="h-4 w-4" />
        <span>فتح الواجهة العامة</span>
      </button>

      <button
        type="button"
        className="btn-primary mt-4"
        disabled={updateMutation.isPending || storefrontQuery.isLoading}
        onClick={() =>
          updateMutation.mutate({
            ...form,
            brand_name: form.brand_name.trim(),
            brand_mark: form.brand_mark.trim(),
            brand_tagline: form.brand_tagline?.trim() || null,
            socials: form.socials.map((row) => ({
              ...row,
              url: row.url ? normalizeStorefrontSocialUrl(row.platform, row.url) : null,
            })),
          })
        }
      >
        {updateMutation.isPending ? 'جارٍ الحفظ...' : 'حفظ هوية الواجهة'}
      </button>
    </section>
  );
}
