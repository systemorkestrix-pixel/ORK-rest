import {
  BellRing,
  Boxes,
  CreditCard,
  Database,
  LayoutDashboard,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

import type { MasterAddon } from '@/shared/api/types';

export type MasterCapabilityMode = 'core' | 'runtime_hidden' | 'disabled';

export const masterInitialAccess = {
  route: '/master/login',
  username: 'owner@master.local',
  password: 'Master@2026!',
};

export const masterNavigationItems = [
  { id: 'dashboard', label: 'المتابعة', to: '/master/dashboard', icon: LayoutDashboard },
  { id: 'clients', label: 'العملاء', to: '/master/clients', icon: CreditCard },
  { id: 'tenants', label: 'النسخ', to: '/master/tenants', icon: Database },
  { id: 'addons', label: 'الإضافات', to: '/master/addons', icon: Boxes },
] satisfies Array<{ id: string; label: string; to: string; icon: LucideIcon }>;

export const masterHighlights = [
  { label: 'النسخ المستقلة', value: 'كل مطعم يعمل ضمن نسخة مستقلة وقاعدة بيانات منفصلة.' },
  { label: 'النسخة الأساسية', value: 'تبدأ كل نسخة من العمليات والمنيو ثم تُفتح الأدوات بالترتيب.' },
  { label: 'الإضافات المرتبة', value: 'لا تفتح أداة أعلى قبل الأداة التي تسبقها.' },
  { label: 'ملكية العميل', value: 'ما يُفعّل يصبح جزءًا دائمًا من نسخة العميل.' },
];

export function getCapabilityModeLabel(mode: MasterCapabilityMode) {
  if (mode === 'core') return 'مفعّل';
  if (mode === 'runtime_hidden') return 'يعمل بصمت';
  return 'مغلق';
}

export function getCapabilityModeClass(mode: MasterCapabilityMode) {
  if (mode === 'core') return 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200';
  if (mode === 'runtime_hidden') return 'border-cyan-400/40 bg-cyan-500/10 text-cyan-200';
  return 'border-amber-400/40 bg-amber-500/10 text-amber-200';
}

export function getClientStatusLabel(status: 'active' | 'trial' | 'paused') {
  if (status === 'active') return 'نشط';
  if (status === 'trial') return 'تجريبي';
  return 'موقوف';
}

export function getClientStatusClass(status: 'active' | 'trial' | 'paused') {
  if (status === 'active') return 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200';
  if (status === 'trial') return 'border-cyan-400/40 bg-cyan-500/10 text-cyan-200';
  return 'border-rose-400/40 bg-rose-500/10 text-rose-200';
}

export function getTenantStateLabel(state: 'ready' | 'pending_activation' | 'suspended') {
  if (state === 'ready') return 'جاهزة';
  if (state === 'pending_activation') return 'بانتظار التفعيل';
  return 'موقوفة';
}

export function getTenantStateClass(state: 'ready' | 'pending_activation' | 'suspended') {
  if (state === 'ready') return 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200';
  if (state === 'pending_activation') return 'border-amber-400/40 bg-amber-500/10 text-amber-200';
  return 'border-rose-400/40 bg-rose-500/10 text-rose-200';
}

export function getMasterToneClasses(tone: 'emerald' | 'cyan' | 'amber' | 'violet') {
  if (tone === 'emerald') return 'from-emerald-500/18 to-emerald-400/6 text-emerald-100';
  if (tone === 'cyan') return 'from-cyan-500/18 to-cyan-400/6 text-cyan-100';
  if (tone === 'violet') return 'from-violet-500/18 to-violet-400/6 text-violet-100';
  return 'from-amber-500/18 to-amber-400/6 text-amber-100';
}

export function getMasterOverviewIcon(iconKey: string): LucideIcon {
  switch (iconKey) {
    case 'clients':
      return CreditCard;
    case 'tenants':
      return Database;
    case 'addons':
      return ShieldCheck;
    case 'disabled':
      return BellRing;
    default:
      return Sparkles;
  }
}

export function splitAddonCapabilities(addon: MasterAddon) {
  const visible = addon.capabilities.filter((capability) => capability.mode === 'core').map((capability) => capability.label);
  const hidden = addon.capabilities
    .filter((capability) => capability.mode === 'runtime_hidden')
    .map((capability) => capability.label);
  const disabled = addon.capabilities
    .filter((capability) => capability.mode === 'disabled')
    .map((capability) => capability.label);
  return { visible, hidden, disabled };
}
