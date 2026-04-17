# مراجعة عقدة التوصيل وتعطيل الأنظمة وتقليص الملفات الكبيرة

## حدود هذه الوثيقة
- هذه الوثيقة هي المرجع التفصيلي لعقدة:
  - `جهة التوصيل / السائق / الشركة`
  - `تعطيل التوصيل والمطبخ بدون كسر النظام`
  - `الملفات التي تجاوزت 1000 سطر وخطة تفكيكها`
- هذه الوثيقة لا تدير خطة التسليم العامة للنظام كله.
- هذه الوثيقة لا تحل محل:
  - [final_delivery_maintenance_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/final_delivery_maintenance_plan.md)
  - [markdown_status_and_system_toggle_audit.md](/c:/Users/stormpc/Desktop/Restaurants/docs/markdown_status_and_system_toggle_audit.md)
- إذا كان السؤال:
  - "ما الذي يجب تسليمه وإغلاقه قبل الإطلاق؟" فالمرجع هو `final_delivery_maintenance_plan`
  - "ما هو التصميم التفصيلي لهذه العقدة؟" فالمرجع هو هذه الوثيقة
  - "ما وضع الوثائق والخطاب النصي؟" فالمرجع هو `markdown_status_and_system_toggle_audit`

## الهدف
- تثبيت منطق واضح للتوصيل يتيح:
  - جهة توصيل داخلية افتراضية
  - شركة توصيل خارجية
  - سائق منفرد
- تمكين تعطيل `التوصيل` أو `المطبخ` بدون كسر الطلبات أو الواجهة العامة
- تحديد الملفات الكبيرة التي تحتاج تفكيكًا معماريًا

## الحالة الحالية

### 1. التوصيل
- النظام الحالي يعتمد على:
  - `orders.delivery_team_notified_at`
  - `orders.delivery_team_notified_by`
  - `delivery_assignments`
  - `delivery_drivers`
- مسار التنفيذ الفردي موجود في:
  - [delivery.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/delivery.py)
- إدارة السائقين موجودة في:
  - [manager.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/manager.py)
  - [DeliveryTeamPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/delivery/drivers/DeliveryTeamPage.tsx)

### 2. التفعيل والتعطيل
- التفعيل الحالي للمطبخ والتوصيل يعتمد على وجود مستخدمين نشطين:
  - [operational.py](/c:/Users/stormpc/Desktop/Restaurants/backend/application/operations_engine/domain/operational.py)
- هذا يعني أن:
  - `kitchen_enabled` = وجود مستخدم مطبخ نشط
  - `delivery_enabled` = وجود عنصر توصيل نشط
- هذا مناسب كـ `جاهزية تشغيلية لحظية`
- لكنه غير كافٍ كـ `تعطيل وظيفي مقصود للنظام`

### 3. الواجهة العامة
- عند إنشاء طلب عام، النظام يمنع الإنشاء إذا كان المطبخ غير متاح:
  - [public.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/public.py)
- والواجهة العامة تقرأ حالة التوصيل لتخفي/تعطل خيار التوصيل:
  - [PublicOrderPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/PublicOrderPage.tsx)

## القرار المعماري المعتمد

## أولا: جهة توصيل داخلية افتراضية
- يجب أن يوجد داخل النظام دائمًا `مزود توصيل داخلي افتراضي`
- هذا يحل مشكلة السائق الداخلي بدون فتح مسار خاص منفصل له
- كل سائق داخل النظام يجب أن ينتمي إلى `جهة توصيل`
  - إما الجهة الداخلية الافتراضية
  - أو شركة توصيل

## ثانيا: الفصل بين 3 مستويات

### 1. جهة التوصيل `DeliveryProvider`
- تمثل:
  - فريقًا داخليًا
  - أو شركة توصيل

### 2. السائق `Courier / Driver`
- هو المنفذ الفعلي
- يكون دائمًا تابعًا لجهة توصيل

### 3. حساب الدخول
- ليس بالضرورة أن يكون السائق نفسه
- شركة التوصيل يمكن أن تملك `حساب مشرف جهة`
- السائق يمكن أن يملك `حساب سائق`
- لاحقًا يمكن أن يعمل عبر `Telegram Bot` بدل الدخول المباشر

## ما الذي لا يجب فعله
- لا يجب أن نعامل `شركة التوصيل` كسائق
- لا يجب أن نعامل `شركة التوصيل` كمستخدم `delivery` فردي عادي
- لا يجب أن نربط التلجرام مباشرة بحالات الطلب بدون المرور بمنطق النظام

## منطق الإضافة الصحيح

### من اللوحة الإدارية الرئيسية
- إنشاء:
  - جهة توصيل داخلية افتراضية
  - شركات التوصيل
  - حساب مشرف جهة عند الحاجة

### من لوحة التوصيل
- إضافة السائقين
- تعديلهم
- ربطهم بجهة التوصيل
- متابعة الجاهزية والتوزيع

### من لوحة السائق / تلجرام
- قبول الطلب
- رفض الطلب
- بدء التوصيل
- إتمام التسليم
- تسجيل الفشل

## النتيجة
- تسلسل موحد:
  - الإدارة تنشئ الجهة
  - لوحة التوصيل تدير السائقين
  - السائق ينفذ

---

## عقدة تعطيل التوصيل والمطبخ بدون كسر النظام

## المشكلة الحالية
- التوصيل والمطبخ مربوطان الآن بـ `وجود المستخدمين النشطين`
- هذا يخلط بين:
  - `هل هذه القناة موجودة في النظام؟`
  - `هل يوجد طاقم نشط الآن؟`

## المطلوب الصحيح
نفصل بين مستويين:

### 1. التمكين الوظيفي `feature flag`
- هل النظام يدعم التوصيل أصلًا؟
- هل النظام يدعم دورة المطبخ أصلًا؟

### 2. الجاهزية التشغيلية `runtime availability`
- هل يوجد الآن طاقم متاح؟
- هل يوجد سائقون أو مستخدمو مطبخ نشطون؟

## التوصية المعمارية

### إعدادات مركزية جديدة
- `delivery_feature_enabled`
- `kitchen_feature_enabled`

### مشتقات تشغيلية تبقى كما هي
- `delivery_enabled_runtime`
- `kitchen_enabled_runtime`

## القاعدة النهائية

### إذا كان التوصيل معطّلًا وظيفيًا
- يختفي نوع `delivery` من الواجهة العامة
- يبقى:
  - `dine-in`
  - `takeaway`
- تمنع الخلفية إنشاء طلبات توصيل جديدة
- الطلبات القديمة تبقى قابلة للمراجعة والتسوية

### إذا كان التوصيل مفعّلًا وظيفيًا لكن غير جاهز تشغيليًا
- يمكن إظهار نوع التوصيل كمغلق مؤقتًا
- مع رسالة مباشرة للعميل
- ولا ينكسر باقي النظام

### إذا كان المطبخ معطّلًا وظيفيًا
- لا تظهر قناة المطبخ ولا مسارها التشغيلي
- لا تمر الطلبات عبر:
  - `SENT_TO_KITCHEN`
  - `IN_PREPARATION`
- بل تنتقل مباشرة إلى مسار مبسط

## مسار الطلب المبسط عند تعطيل المطبخ

### للمبيعات العادية
- `CREATED`
- `CONFIRMED`
- `READY`

### للتوصيل
- `CREATED`
- `CONFIRMED`
- `READY`
- `OUT_FOR_DELIVERY`
- `DELIVERED / DELIVERY_FAILED`

## أثر ذلك على التتبع العام
- واجهة التتبع لا يجب أن تفترض وجود مراحل المطبخ دائمًا
- بل تبني الخطوات حسب `profile`

### أمثلة
- `kitchen workflow on`
  - تم الاستلام
  - قيد التحضير
  - جاهز
  - خرج للتوصيل
  - تم التسليم

- `kitchen workflow off`
  - تم الاستلام
  - جاهز
  - خرج للتوصيل
  - تم التسليم

## هذا هو الحل المختصر والصحيح
- لا نكسر البيع
- لا نكسر التتبع
- لا نكسر الطلبات
- فقط نغيّر `بروفايل الدورة`

---

## الترتيب المنطقي للأنظمة بعد الفصل

## قناة التوصيل
- `التوزيع`
- `الفريق`
- `الإعدادات`
- `التسويات`

## لوحة السائق
- صفحة تنفيذ فردية فقط
- ليست لوحة شركة

## الجهة الخارجية
- تدخل إلى لوحة توصيل مخصّصة بفلترة على جهتها
- لا تدخل على لوحة السائق الفردي

---

## تأثير ذلك على النظام الحالي بدون كسر

## ما يبقى كما هو
- `delivery_team_notified_at`
- `delivery_assignments`
- `delivery_settlement`
- حالات الطلب الحالية

## ما يضاف لاحقًا
- `delivery_providers`
- `provider admin accounts`
- `dispatch layer`

## القاعدة الصارمة
- لا نكسر `assignment`
- لا نستبدل `notification`
- نضيف قبل `assignment` طبقة توزيع فقط

---

## مراجعة الملفات التي تجاوزت 1000 سطر

هذه الملفات من المشروع نفسه، بعد استبعاد `.venv` و`node_modules`:

1. [OrdersPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/operations/orders/OrdersPage.tsx) — 1867
2. [manager.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/manager.py) — 1821
3. [FinancialPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/finance/transactions/FinancialPage.tsx) — 1367
4. [ProductsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/system/catalog/products/ProductsPage.tsx) — 1298
5. [schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py) — 1236
6. [warehouse_services.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/warehouse_services.py) — 1206
7. [ReportsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/intelligence/reports/ReportsPage.tsx) — 1036
8. [types.ts](/c:/Users/stormpc/Desktop/Restaurants/src/shared/api/types.ts) — 1017
9. [WarehousePage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/warehouse/dashboard/WarehousePage.tsx) — 1010
10. [operations_repository.py](/c:/Users/stormpc/Desktop/Restaurants/backend/infrastructure/repositories/operations_repository.py) — 1007

---

## خطة تقليص الملفات الكبيرة

## أولوية أولى

### [OrdersPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/operations/orders/OrdersPage.tsx)
يجب تقسيمه إلى:
- `hooks/useOrderFilters.ts`
- `hooks/useOrderActions.ts`
- `components/OrdersToolbar.tsx`
- `components/OrdersTable.tsx`
- `components/OrderDetailsModal.tsx`
- `components/OrderCreateModal.tsx`

### [manager.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/manager.py)
يجب تقسيمه إلى routers فرعية:
- `manager_orders.py`
- `manager_delivery.py`
- `manager_finance.py`
- `manager_settings.py`
- `manager_users.py`
- `manager_audit.py`

### [schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py)
يجب تقسيمه حسب النطاق:
- `schemas/orders.py`
- `schemas/delivery.py`
- `schemas/finance.py`
- `schemas/system.py`
- `schemas/warehouse.py`
- `schemas/public.py`

## أولوية ثانية

### [FinancialPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/finance/transactions/FinancialPage.tsx)
تقسيم حسب الأقسام الحالية:
- overview
- cashbox
- settlements
- entries
- closures

### [ProductsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/system/catalog/products/ProductsPage.tsx)
تقسيم إلى:
- product form
- secondary links editor
- consumption components editor
- category controls
- archive controls

### [WarehousePage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/warehouse/dashboard/WarehousePage.tsx)
رغم أنه جرى تقليص القناة، الملف نفسه ما زال بحاجة إلى تفكيك لكل صفحة مدمجة.

## أولوية ثالثة
- [ReportsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/intelligence/reports/ReportsPage.tsx)
- [types.ts](/c:/Users/stormpc/Desktop/Restaurants/src/shared/api/types.ts)
- [warehouse_services.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/warehouse_services.py)
- [operations_repository.py](/c:/Users/stormpc/Desktop/Restaurants/backend/infrastructure/repositories/operations_repository.py)

---

## قواعد التفكيك المعماري

### 1. لا نفكك لمجرد تقليل السطور
- نفكك حسب المسؤولية

### 2. كل ملف جديد يجب أن يملك غرضًا واحدًا
- واجهة
- hook
- mapper
- use case
- router
- repository adapter

### 3. لا ننقل منطق الدومين إلى الواجهة
- الواجهة تنسق فقط
- الدومين يقرر

### 4. النصوص الموجهة للمستخدم النهائي
- تمنع أي لغة تشرح للمطور
- تمنع أي وصف تقني غير لازم
- تركز على:
  - ما الذي يراه المستخدم
  - ما الذي يمكنه فعله الآن

---

## الخطوات القابلة للإغلاق على النظام الحالي

1. إضافة `feature flags` مستقلة للتوصيل والمطبخ
2. تعديل `public bootstrap` و`public create order` لتقرأ:
   - التمكين الوظيفي
   - الجاهزية التشغيلية
3. جعل التتبع العام يعتمد `workflow profile`
4. إنشاء `Delivery Provider` داخلي افتراضي
5. نقل منطق `DeliveryDriver` ليصبح دائمًا تابعًا لجهة
6. بدء تفكيك الملفات الكبيرة حسب الأولوية

## ما لا يجب تغييره مباشرة
- `delivery_assignments`
- `delivery_settlement`
- دورة الدفع الحالية
- إشعارات التوصيل الحالية

هذا يحافظ على النظام الحالي ويمنع الانكسار أثناء التطوير.
