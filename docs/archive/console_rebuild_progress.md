# ملف التقدم: إعادة بناء الواجهات من A إلى Z

الحالة العامة: قيد التنفيذ وفق الخطة المصححة.
مرجع المهام: `docs/archive/console_rebuild_tasks.md`.

A) ضبط المعمارية الأساسية
الحالة: مكتمل
المخرجات: فصل التطبيقات `/console`, `/kitchen`, `/delivery`, `/public`.

B) Router Separation
الحالة: مكتمل
المخرجات: توجيه Manager Console و Kitchen Console و Delivery Console كلٌ في مساره.

C) Manager Console Sections
الحالة: مكتمل
المخرجات: ChannelBar + ConsolePage + Manager Sections على `/console/*`.

D) Internal Links Audit
الحالة: قيد التنفيذ
المخرجات: تحديث الروابط الداخلية إلى `/console/*` وعدم الخلط مع لوحات التشغيل.

E) Kitchen Console Isolation
الحالة: مكتمل
المخرجات: `/kitchen/console` يعمل كلوحة تشغيل مستقلة.

F) Delivery Console Isolation
الحالة: مكتمل
المخرجات: `/delivery/console` يعمل كلوحة تشغيل مستقلة.

G) Tools Unification
الحالة: لم يبدأ
المخرجات: توحيد الأدوات المشتركة في `src/tools`.

H) Entities Alignment
الحالة: لم يبدأ
المخرجات: نقل API calls إلى `src/entities` حسب الخطة.

I) Backend Mapping
الحالة: قيد التنفيذ
المخرجات: مصفوفة ربط Application → Page → Entity → API → Engine.

J) Documentation Update
الحالة: مكتمل
المخرجات: تحديث خطة البناء والمهام وسجل التقدم.

K) QA Regression
الحالة: لم يبدأ
المخرجات: تحقق تنقل SPA وثبات التصميم.

L) Performance Check
الحالة: لم يبدأ
المخرجات: قياس الأداء بعد الفصل.

M) UI Polish
الحالة: مؤجل
المخرجات: تحسينات طفيفة بدون تغيير الهوية.

N) Closure
الحالة: لاحق
المخرجات: إغلاق رسمي للتحديث.

R) قاعدة تلوين الصفوف
الحالة: مكتمل
المخرجات: اعتماد معيار مركزي لتلوين صفوف الجداول حسب الحالة (نجاح=أخضر، تحذير=أصفر، خطر=أحمر). يطبّق فقط على الجداول ذات الحالة التشغيلية أو التفعيل/التعطيل، بينما الجداول التحليلية والتجميعية تبقى بدون تلوين صفوف لتفادي إيحاءات حالة غير موجودة.

S) UI Audit Report
الحالة: مكتمل
المخرجات: تقرير تدقيق شامل للواجهات مع ملاحظات الاتساق والتنظيم.

T) Final Cleanup: Routes + Commission Removal
الحالة: مكتمل
المخرجات: إزالة صفحات غير مستخدمة (`src/pages/kitchen/monitor/KitchenMonitorPage.tsx` و `src/modules/kitchen/monitor/KitchenMonitorPage.tsx`)، مراجعة `AppRouter` للتأكد من عدم وجود مسارات متكررة مع الإبقاء على إعادة توجيه المسارات القديمة للتوافق، وإزالة نظام العمولة من الواجهة والـ API والمنطق الخلفي مع إضافة migration لحذف العمود نهائيًا (`backend/alembic/versions/b4c2d7e9f0a1_p4_2_drop_delivery_commission_rate.py`) وتحديث النموذج.
