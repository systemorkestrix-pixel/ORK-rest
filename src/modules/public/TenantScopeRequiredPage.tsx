import { Building2, LogIn, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

export function TenantScopeRequiredPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const tenantTargetPath = useMemo(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    const tenantCode = window.sessionStorage.getItem('active_tenant_code')?.trim();
    if (!tenantCode) {
      return null;
    }

    const rawPath = location.pathname;
    const suffix =
      rawPath === '/menu'
        ? 'menu'
        : rawPath === '/track' || rawPath === '/tracking'
          ? 'track'
          : rawPath === '/public/tables'
            ? 'public/tables'
            : 'order';

    return `/t/${encodeURIComponent(tenantCode)}/${suffix}`;
  }, [location.pathname]);

  useEffect(() => {
    if (!tenantTargetPath) {
      return;
    }
    navigate(tenantTargetPath, { replace: true });
  }, [navigate, tenantTargetPath]);

  return (
    <div
      dir="rtl"
      className="min-h-screen bg-transparent px-4 py-10 text-[var(--app-text)]"
    >
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-3xl items-center justify-center">
        <section className="w-full rounded-[32px] border border-[#ead9bf] bg-white/90 p-6 shadow-[0_24px_60px_rgba(70,45,20,0.14)] backdrop-blur md:p-8">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[24px] border border-[#ead9bf] bg-[#fff1dd] text-[#c67a2a] shadow-[0_18px_34px_rgba(198,122,42,0.16)]">
            <Building2 className="h-7 w-7" />
          </div>

          <div className="mt-5 text-center">
            <p className="text-xs font-black tracking-[0.26em] text-[#9a7f62]">الوصول العام</p>
            <h1 className="mt-3 text-2xl font-black text-[#2f2218] md:text-3xl">هذه الصفحة تحتاج رابط المطعم الصحيح</h1>
            <p className="mt-3 text-sm font-semibold leading-7 text-[#6b5644] md:text-base">
              الواجهة العامة لا تعمل من رابط مشترك. افتح الرابط الذي استلمته من المطعم نفسه حتى تظهر القائمة أو التتبع أو خدمة الطاولات بشكل صحيح.
            </p>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <article className="rounded-[24px] border border-[#ead9bf] bg-[#fff8ee] p-4">
              <div className="flex items-center gap-2 text-[#8a5b2a]">
                <ShieldCheck className="h-4 w-4" />
                <span className="text-sm font-black">لماذا تم الإغلاق</span>
              </div>
              <p className="mt-3 text-sm font-semibold leading-7 text-[#6b5644]">
                تم إيقاف المسارات العامة المشتركة حتى لا تظهر بيانات مطعم داخل واجهة مطعم آخر.
              </p>
            </article>

            <article className="rounded-[24px] border border-[#ead9bf] bg-[#fff8ee] p-4">
              <div className="flex items-center gap-2 text-[#8a5b2a]">
                <Building2 className="h-4 w-4" />
                <span className="text-sm font-black">الشكل الصحيح للرابط</span>
              </div>
              <p className="mt-3 text-sm font-semibold leading-7 text-[#6b5644]">
                يبدأ الرابط عادة بهذا الشكل <span dir="ltr" className="font-black text-[#2f2218]">/t/restaurant-code/order</span>
              </p>
            </article>
          </div>

          <div className="mt-6 flex justify-center">
            <Link
              to="/manager/login"
              className="inline-flex min-h-[46px] items-center justify-center gap-2 rounded-2xl border border-[#d9b488] bg-[#fff1dd] px-5 text-sm font-black text-[#8a531c] transition hover:bg-[#ffe7c7]"
            >
              <LogIn className="h-4 w-4" />
              <span>دخول الإدارة</span>
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
