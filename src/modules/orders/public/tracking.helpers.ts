import { Bike, CheckCircle2, ChefHat, Clock3, PackageCheck, XCircle } from 'lucide-react';

import type {
  OrderPaymentStatus,
  OrderStatus,
  OrderType,
  PublicWorkflowProfile,
} from '@/shared/api/types';
import {
  resolveCustomerFacingOrderStatusLabel,
  resolveCustomerTrackingStage,
} from '@/shared/utils/orderStatusPresentation';

export const trackingTimeFormatter = new Intl.DateTimeFormat('ar-DZ-u-nu-latn', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

export const autoRefreshMs = 5000;

export type TrackingTone = 'success' | 'warning' | 'info' | 'danger';

export type TrackingPresentation = {
  label: string;
  title: string;
  description: string;
  hint: string;
  tone: TrackingTone;
  Icon: typeof Clock3;
};

export type TrackingStepKey = 'received' | 'confirmed' | 'preparing' | 'ready' | 'out' | 'done';
export type TrackingStepStatus = 'completed' | 'current' | 'upcoming';

export type TrackingStep = {
  key: TrackingStepKey;
  label: string;
  status: TrackingStepStatus;
};

export const heroToneClasses: Record<TrackingTone, string> = {
  success:
    'border-[color:var(--brand-green)] bg-[linear-gradient(135deg,var(--brand-green-soft),rgba(0,0,0,0.52))] text-emerald-50',
  warning:
    'border-[color:var(--brand-gold)] bg-[linear-gradient(135deg,var(--brand-gold-soft),rgba(0,0,0,0.52))] text-amber-50',
  info:
    'border-[color:var(--brand-blue)] bg-[linear-gradient(135deg,var(--brand-blue-soft),rgba(0,0,0,0.52))] text-sky-50',
  danger:
    'border-[color:var(--brand-red)] bg-[linear-gradient(135deg,var(--brand-red-soft),rgba(0,0,0,0.52))] text-rose-50',
};

export const statusCardToneClasses: Record<TrackingTone, string> = {
  success:
    'border-[color:var(--brand-green)] bg-[linear-gradient(135deg,var(--brand-green-soft),rgba(0,0,0,0.44))] text-emerald-50 shadow-[0_20px_45px_rgba(34,197,94,0.16)]',
  warning:
    'border-[color:var(--brand-gold)] bg-[linear-gradient(135deg,var(--brand-gold-soft),rgba(0,0,0,0.44))] text-amber-50 shadow-[0_20px_45px_rgba(227,160,86,0.16)]',
  info:
    'border-[color:var(--brand-blue)] bg-[linear-gradient(135deg,var(--brand-blue-soft),rgba(0,0,0,0.44))] text-sky-50 shadow-[0_20px_45px_rgba(24,160,251,0.16)]',
  danger:
    'border-[color:var(--brand-red)] bg-[linear-gradient(135deg,var(--brand-red-soft),rgba(0,0,0,0.44))] text-rose-50 shadow-[0_20px_45px_rgba(255,61,31,0.16)]',
};

export const descriptionFrameToneClasses: Record<TrackingTone, string> = {
  success: 'border-[color:rgba(34,197,94,0.28)] bg-[#17110d] text-stone-200',
  warning: 'border-[color:rgba(227,160,86,0.28)] bg-[#17110d] text-stone-200',
  info: 'border-[color:rgba(24,160,251,0.28)] bg-[#17110d] text-stone-200',
  danger: 'border-[color:rgba(255,61,31,0.28)] bg-[#17110d] text-stone-200',
};

export function resolveTrackingPresentation(
  status: OrderStatus,
  type: OrderType,
  paymentStatus?: OrderPaymentStatus | null,
  workflowProfile: PublicWorkflowProfile = 'kitchen_managed',
): TrackingPresentation {
  const directWorkflow = workflowProfile !== 'kitchen_managed';
  const customerLabel = resolveCustomerFacingOrderStatusLabel(status, type, paymentStatus);

  if (status === 'DELIVERED') {
    const dineInSettled = type === 'dine-in' && paymentStatus === 'paid';

    return {
      label:
        type === 'delivery'
          ? 'تم التسليم'
          : dineInSettled
            ? 'تمت التسوية'
            : type === 'dine-in'
              ? 'تم التقديم'
              : 'تم الاستلام',
      title:
        type === 'delivery'
          ? 'وصل طلبك بنجاح'
          : dineInSettled
            ? 'تمت تسوية الطلب'
            : 'اكتمل طلبك بنجاح',
      description: dineInSettled
        ? 'تم تقديم الطلب وإغلاق التسوية بنجاح.'
        : 'اكتملت جميع خطوات الطلب ويمكنك الاحتفاظ بكود التتبع لأي مراجعة لاحقة.',
      hint: dineInSettled
        ? 'الحالة الحالية نهائية لهذا الطلب.'
        : 'إذا احتجت إلى المساعدة لاحقًا، يكفي أن تذكر كود التتبع نفسه.',
      tone: 'success',
      Icon: CheckCircle2,
    };
  }

  if (status === 'OUT_FOR_DELIVERY') {
    return {
      label: customerLabel,
      title: 'الطلب في الطريق إليك',
      description: directWorkflow
        ? 'تم اعتماد الطلب وتسليمه مباشرة للتوصيل.'
        : 'تم إنهاء التحضير وتسليم الطلب لعنصر التوصيل.',
      hint: 'يفضل إبقاء الهاتف قريبًا منك حتى وصول الطلب.',
      tone: 'info',
      Icon: Bike,
    };
  }

  if (status === 'READY') {
    return {
      label: customerLabel,
      title: type === 'delivery' ? 'طلبك جاهز وينتظر الانطلاق' : 'طلبك أصبح جاهزًا',
      description:
        type === 'delivery'
          ? 'أصبح الطلب جاهزًا لبدء مرحلة التوصيل.'
          : type === 'dine-in'
            ? 'أصبح الطلب جاهزًا للتقديم داخل المطعم.'
            : 'أصبح الطلب جاهزًا للاستلام.',
      hint:
        type === 'delivery'
          ? 'ستتغير الحالة إلى خرج للتوصيل بمجرد انطلاق السائق.'
          : 'يمكنك الاعتماد على هذه الحالة لمعرفة أن الطلب أصبح جاهزًا.',
      tone: 'success',
      Icon: PackageCheck,
    };
  }

  if (status === 'IN_PREPARATION') {
    return {
      label: customerLabel,
      title: 'نعمل على تجهيز طلبك الآن',
      description: 'وصل الطلب إلى مرحلة التنفيذ ويجري تحضيره الآن.',
      hint: 'تتجدد هذه الشاشة تلقائيًا دون الحاجة إلى تحديث الصفحة.',
      tone: 'warning',
      Icon: ChefHat,
    };
  }

  if (status === 'CONFIRMED' || status === 'SENT_TO_KITCHEN') {
    return {
      label: customerLabel,
      title: 'تم تأكيد الطلبية',
      description: directWorkflow
        ? 'تم اعتماد الطلب وسينتقل مباشرة إلى مرحلته التالية حسب نوع التنفيذ.'
        : 'تم اعتماد الطلب وهو الآن بانتظار بدء التنفيذ الفعلي.',
      hint: directWorkflow
        ? 'ستظهر هنا المرحلة التالية فور تجهيز الطلب أو بدء التنفيذ.'
        : 'ستظهر مرحلة التحضير هنا فور بدء تنفيذ الطلب داخل المطبخ.',
      tone: 'info',
      Icon: Clock3,
    };
  }

  if (status === 'CREATED') {
    return {
      label: customerLabel,
      title: 'استلمنا طلبك وبدأنا معالجته',
      description: directWorkflow
        ? 'تم تسجيل الطلب بنجاح ويجري نقله مباشرة إلى المرحلة التالية.'
        : 'تم تسجيل الطلب بنجاح داخل النظام.',
      hint: directWorkflow
        ? 'ستظهر الحالة التالية هنا فور اعتماد الطلب أو تجهيزه.'
        : 'ستظهر مرحلة التحضير هنا فور بدء التنفيذ.',
      tone: 'info',
      Icon: Clock3,
    };
  }

  if (status === 'DELIVERY_FAILED') {
    return {
      label: customerLabel,
      title: 'الطلب يحتاج إلى مراجعة سريعة',
      description: 'حدث تعذر في مرحلة التوصيل وقد يحتاج الفريق إلى إعادة تنسيق.',
      hint: 'عند التواصل مع المطعم، اذكر كود التتبع لتسريع المراجعة.',
      tone: 'danger',
      Icon: XCircle,
    };
  }

  return {
    label: 'الطلب ملغى',
    title: 'تم إلغاء الطلب',
    description: 'تم إيقاف هذا الطلب ولن يتابع النظام تنفيذه بعد الآن.',
    hint: 'يمكنك إنشاء طلب جديد إذا رغبت في إعادة المحاولة.',
    tone: 'danger',
    Icon: XCircle,
  };
}

export function buildTrackingSteps(
  type: OrderType,
  status: OrderStatus,
  paymentStatus?: OrderPaymentStatus | null,
  workflowProfile: PublicWorkflowProfile = 'kitchen_managed',
): TrackingStep[] {
  const activeKeys = resolveStepSequence(type, workflowProfile);
  const currentKey = resolveStepKey(type, status, workflowProfile);
  const currentIndex = Math.max(activeKeys.indexOf(currentKey), 0);

  return activeKeys.map((key, index) => ({
    key,
    label: stepLabel(type, key, paymentStatus),
    status: index < currentIndex ? 'completed' : index === currentIndex ? 'current' : 'upcoming',
  }));
}

function resolveStepSequence(type: OrderType, workflowProfile: PublicWorkflowProfile): TrackingStepKey[] {
  if (workflowProfile === 'direct_delivery') {
    return ['received', 'confirmed', 'ready', 'out', 'done'];
  }

  if (workflowProfile === 'direct_fulfillment') {
    return ['received', 'confirmed', 'ready', 'done'];
  }

  return type === 'delivery'
    ? ['received', 'confirmed', 'preparing', 'ready', 'out', 'done']
    : ['received', 'confirmed', 'preparing', 'ready', 'done'];
}

function resolveStepKey(
  type: OrderType,
  status: OrderStatus,
  workflowProfile: PublicWorkflowProfile,
): TrackingStepKey {
  const stage = resolveCustomerTrackingStage(status, workflowProfile);

  if (stage === 'received' || stage === 'canceled') {
    return 'received';
  }
  if (stage === 'confirmed') {
    return 'confirmed';
  }
  if (stage === 'preparing') {
    return 'preparing';
  }
  if (stage === 'ready') {
    return 'ready';
  }
  if (stage === 'out' || stage === 'failed') {
    return type === 'delivery' ? 'out' : 'ready';
  }
  return 'done';
}

function stepLabel(
  type: OrderType,
  key: TrackingStepKey,
  paymentStatus?: OrderPaymentStatus | null,
): string {
  if (key === 'received') {
    return 'تم استلام الطلب';
  }
  if (key === 'confirmed') {
    return 'تم تأكيد الطلبية';
  }
  if (key === 'preparing') {
    return 'قيد التحضير';
  }
  if (key === 'ready') {
    return type === 'delivery'
      ? 'جاهز للخروج'
      : type === 'dine-in'
        ? 'جاهز للتقديم'
        : 'جاهز للاستلام';
  }
  if (key === 'out') {
    return 'خرج للتوصيل';
  }
  return type === 'delivery'
    ? 'تم التسليم'
    : type === 'dine-in'
      ? paymentStatus === 'paid'
        ? 'تمت التسوية'
        : 'تم التقديم'
      : 'تم الاستلام';
}

export function formatTrackingMoney(value: number): string {
  return `${value.toFixed(2)} د.ج`;
}
