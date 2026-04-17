import type { LucideIcon } from 'lucide-react';
import { Bike, ChefHat, Facebook, Globe, Instagram, MessageCircle, ShoppingBag, UtensilsCrossed } from 'lucide-react';

import type { StorefrontIconKey, StorefrontSettings, StorefrontSocialPlatform } from '@/shared/api/types';

export const defaultStorefrontSettings: StorefrontSettings = {
  brand_name: 'sPeeD SyS',
  brand_mark: 'sPeeD SyS',
  brand_icon: 'utensils',
  brand_tagline: 'وجباتك جاهزة بخطوات أوضح.',
  socials: [
    { platform: 'website', url: null, enabled: false },
    { platform: 'whatsapp', url: null, enabled: false },
    { platform: 'instagram', url: null, enabled: false },
    { platform: 'facebook', url: null, enabled: false },
  ],
};

export const storefrontIconOptions: Array<{ value: StorefrontIconKey; label: string; icon: LucideIcon }> = [
  { value: 'utensils', label: 'أدوات الطعام', icon: UtensilsCrossed },
  { value: 'chef_hat', label: 'قبعة الطاهي', icon: ChefHat },
  { value: 'shopping_bag', label: 'حقيبة الطلب', icon: ShoppingBag },
  { value: 'bike', label: 'دراجة التوصيل', icon: Bike },
];

export function resolveStorefrontIcon(iconKey: StorefrontIconKey | string | null | undefined): LucideIcon {
  return storefrontIconOptions.find((option) => option.value === iconKey)?.icon ?? UtensilsCrossed;
}

export const storefrontSocialOptions: Array<{ platform: StorefrontSocialPlatform; label: string; icon: LucideIcon }> = [
  { platform: 'website', label: 'الموقع', icon: Globe },
  { platform: 'whatsapp', label: 'واتساب', icon: MessageCircle },
  { platform: 'instagram', label: 'إنستغرام', icon: Instagram },
  { platform: 'facebook', label: 'فيسبوك', icon: Facebook },
];

export function getStorefrontSocialLabel(platform: StorefrontSocialPlatform): string {
  return storefrontSocialOptions.find((option) => option.platform === platform)?.label ?? platform;
}

export function mergeStorefrontSettings(settings?: StorefrontSettings | null): StorefrontSettings {
  if (!settings) {
    return defaultStorefrontSettings;
  }
  const socials = storefrontSocialOptions.map((option) => {
    const matched = settings.socials.find((row) => row.platform === option.platform);
    return matched ?? defaultStorefrontSettings.socials.find((row) => row.platform === option.platform)!;
  });
  return {
    brand_name: settings.brand_name || defaultStorefrontSettings.brand_name,
    brand_mark: settings.brand_mark || defaultStorefrontSettings.brand_mark,
    brand_icon: settings.brand_icon || defaultStorefrontSettings.brand_icon,
    brand_tagline: settings.brand_tagline || defaultStorefrontSettings.brand_tagline,
    socials,
  };
}

export function normalizeStorefrontSocialUrl(platform: StorefrontSocialPlatform, value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  if (platform === 'whatsapp') {
    const digitsOnly = trimmed.replace(/[^\d+]/g, '');
    if (/^https?:\/\//i.test(trimmed) || /^wa\.me\//i.test(trimmed)) {
      return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    }
    return `https://wa.me/${digitsOnly.replace(/^\+/, '')}`;
  }
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  return `https://${trimmed}`;
}
