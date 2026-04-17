import { Building2, ExternalLink, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';

export function TenantScopeRequiredPage() {
  return (
    <div
      dir="rtl"
      className="min-h-screen bg-[radial-gradient(circle_at_top_right,rgba(214,149,80,0.16),transparent_28%),linear-gradient(180deg,#fffdf9_0%,#f6efe3_100%)] px-4 py-10 text-[#2f2218]"
    >
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-3xl items-center justify-center">
        <section className="w-full rounded-[32px] border border-[#ead9bf] bg-white/88 p-6 shadow-[0_24px_60px_rgba(70,45,20,0.14)] backdrop-blur md:p-8">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[24px] border border-[#ead9bf] bg-[#fff1dd] text-[#c67a2a] shadow-[0_18px_34px_rgba(198,122,42,0.16)]">
            <Building2 className="h-7 w-7" />
          </div>

          <div className="mt-5 text-center">
            <p className="text-xs font-black tracking-[0.26em] text-[#9a7f62]">TENANT SCOPED ENTRY</p>
            <h1 className="mt-3 text-2xl font-black text-[#2f2218] md:text-3xl">هذه الواجهة مرتبطة بمطعم محدد</h1>
            <p className="mt-3 text-sm font-semibold leading-7 text-[#6b5644] md:text-base">
              لكل مطعم رابط عام مستقل. للوصول إلى الطلب أو التتبع أو المنيو، افتح الرابط المباشر الذي تم تسليمه من نفس
              المطعم.
            </p>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <article className="rounded-[24px] border border-[#ead9bf] bg-[#fff8ee] p-4">
              <div className="flex items-center gap-2 text-[#8a5b2a]">
                <ShieldCheck className="h-4 w-4" />
                <span className="text-sm font-black">سبب الإغلاق</span>
              </div>
              <p className="mt-3 text-sm font-semibold leading-7 text-[#6b5644]">
                تم إيقاف المسارات العامة المشتركة حتى لا تظهر بيانات مطعم داخل واجهة مطعم آخر.
              </p>
            </article>

            <article className="rounded-[24px] border border-[#ead9bf] bg-[#fff8ee] p-4">
              <div className="flex items-center gap-2 text-[#8a5b2a]">
                <ExternalLink className="h-4 w-4" />
                <span className="text-sm font-black">المسار الصحيح</span>
              </div>
              <p className="mt-3 text-sm font-semibold leading-7 text-[#6b5644]">
                استخدم رابطًا من نوع <span dir="ltr" className="font-black text-[#2f2218]">/t/tenant-code/order</span>
              </p>
            </article>
          </div>

          <div className="mt-6 flex justify-center">
            <Link
              to="/manager/login"
              className="inline-flex min-h-[46px] items-center justify-center rounded-2xl border border-[#d9b488] bg-[#fff1dd] px-5 text-sm font-black text-[#8a531c] transition hover:bg-[#ffe7c7]"
            >
              دخول لوحة الإدارة
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
