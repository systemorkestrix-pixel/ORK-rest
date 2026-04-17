# تقرير تدقيق الوثائق والعقد المعمارية وخطاب الواجهة

تاريخ المراجعة: `2026-03-27`

هذه الوثيقة هي مرجع تدقيق مختصر وصارم يربط بين:

- حالة ملفات `Markdown` الحالية
- القرارات التي ما زالت صالحة
- القرارات التي تغيّر مسارها
- العقدة المعمارية الخاصة بـ `التوصيل / المطبخ / تعطيل الأنظمة`
- النصوص التي يجب أن تتحول إلى خطاب مباشر للمستخدم النهائي
- الملفات الكبيرة التي تحتاج تفكيكًا منظمًا

الهدف ليس فتح توسع جديد، بل تثبيت ما يجب اعتماده الآن، وما يجب تجميده، وما يمكن إغلاقه على النظام الحالي بدون كسر.

## 0. حدود هذه الوثيقة
- هذه الوثيقة هي مرجع `تدقيق` و`فرز` و`توحيد فهم`.
- دورها:
  - تحديد ما هو حي وما هو تاريخي في `docs`
  - كشف ما تغيّر مساره
  - تثبيت خطاب النصوص الموجهة للمستخدم النهائي
- لا تستخدم هذه الوثيقة كخطة تنفيذ رئيسية للتسليم.
- لا تستخدم هذه الوثيقة كمرجع تفصيلي وحيد لعقدة التوصيل أو تفكيك الملفات الكبيرة.
- المرجعان المكملان لها هما:
  - [final_delivery_maintenance_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/final_delivery_maintenance_plan.md)
  - [delivery_module_toggle_and_large_files_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_module_toggle_and_large_files_review.md)

---

## 1. الملخص التنفيذي

الحالة الحالية يمكن تلخيصها في 6 قرارات ثابتة:

1. داخل النظام يجب أن توجد دائمًا `جهة توصيل داخلية افتراضية`.
2. `شركة التوصيل` ليست سائقًا، وليست حساب `delivery` فرديًا.
3. `السائق` يجب أن يكون دائمًا تابعًا لجهة توصيل، سواء كانت داخلية أو خارجية.
4. تعطيل `التوصيل` أو `المطبخ` لا يجب أن يعتمد فقط على وجود مستخدمين نشطين.
5. الواجهة العامة يجب أن تخفي ما هو غير متاح وظيفيًا، لا أن تنكسر بسببه.
6. النصوص الظاهرة في النظام يجب أن تخاطب المستخدم النهائي أو الإداري التشغيلي مباشرة، لا المطور.

---

## 2. قراءة ملفات Markdown الحالية

## 2.1 ملفات ما زالت مرجعًا صالحًا

هذه الملفات ما زالت صالحة كمرجع عملي للنظام الحالي:

- [project_state_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/project_state_report.md)
- [operating_model_ui_map.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operating_model_ui_map.md)
- [operating_model_user_guide.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operating_model_user_guide.md)
- [operational_ui_principles.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operational_ui_principles.md)
- [final_delivery_maintenance_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/final_delivery_maintenance_plan.md)
- [delivery_manual_address_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_manual_address_plan.md)
- [delivery_module_toggle_and_large_files_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_module_toggle_and_large_files_review.md)
- [public_order_journey_execution_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/public_order_journey_execution_plan.md)
- [inventory_consumption_phase1_master_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/inventory_consumption_phase1_master_plan.md)

هذه الملفات تمثل اليوم:

- خريطة النظام
- مسارات التوصيل الحالية
- رحلة الواجهة العامة
- ربط المخزون والاستهلاك
- قواعد الواجهات التشغيلية

## 2.2 ملفات أصبحت انتقالية أو تاريخية

هذه الملفات لا يجب أن تمد العمل الجديد، لكنها تبقى كأرشيف قرار:

- [delivery_location_provider_strategy.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/delivery_location_provider_strategy.md)
  - السبب: المسار الاستراتيجي للمزود الخارجي أُلغي، واعتمدنا العناوين اليدوية بدلًا منه.
- [console_rebuild_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_plan.md)
- [console_rebuild_progress.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_progress.md)
- [console_rebuild_tasks.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_tasks.md)
- [ui_audit_execution_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/ui_audit_execution_plan.md)
- [ui_audit_execution_progress.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/ui_audit_execution_progress.md)

القاعدة:

- تبقى للرجوع التاريخي فقط
- لا تُستخدم كمرجع قرار جديد
- لا يُبنى عليها تطوير جديد إلا إذا نُقلت خلاصتها إلى ملف حيّ وصالح

## 2.3 ملف يحتاج اعتباره مرجعًا تشغيليًا مباشرًا الآن

الملف الأكثر ارتباطًا بالعقدة الحالية هو:

- [delivery_module_toggle_and_large_files_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_module_toggle_and_large_files_review.md)

لأنه يجمع:

- جهة التوصيل الداخلية الافتراضية
- فصل الجهة عن السائق
- تعطيل التوصيل والمطبخ
- مراجعة الملفات الكبيرة

---

## 3. الخطوات التي تغيّر مسارها

## 3.1 ما تغيّر نهائيًا

### أ. مزود المواقع الخارجي

المسار القديم:

- مزود خارجي لجلب الدول/المناطق/الأحياء

المسار المعتمد الآن:

- شجرة عناوين توصيل يدوية داخل النظام

القرار:

- لا يتم توسيع المسار الخارجي
- لا يتم بناء أي اعتماد إضافي عليه
- المرجع المعتمد هو:
  - [delivery_manual_address_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_manual_address_plan.md)

### ب. شركة التوصيل كمستخدم فردي

المسار غير الصحيح:

- التعامل مع شركة التوصيل كسائق
- أو كحساب `delivery` فردي

المسار الصحيح:

- الشركة = `جهة توصيل`
- السائق = `عنصر منفذ`
- الحساب = `وسيلة دخول`

### ج. الاعتماد على المستخدمين النشطين كبديل عن تعطيل الأنظمة

الوضع الحالي في الكود:

- `kitchen_enabled`
- `delivery_enabled`

يُشتقان اليوم من وجود مستخدمين نشطين في:

- [operational.py](/c:/Users/stormpc/Desktop/Restaurants/backend/application/operations_engine/domain/operational.py)

وهذا يصلح كـ:

- `جاهزية تشغيلية لحظية`

لكن لا يصلح كـ:

- `تمكين وظيفي مقصود للنظام`

---

## 4. الخطوات التي ما زال يمكن إغلاقها على النظام الحالي

هذه خطوات يمكن إغلاقها الآن بدون هدم البنية الحالية:

### 1. إضافة تمكين وظيفي مستقل

نضيف إعدادين مركزيين:

- `delivery_feature_enabled`
- `kitchen_feature_enabled`

مع الإبقاء على الجاهزية التشغيلية الحالية كمشتق runtime.

### 2. تعديل قدرات التشغيل العامة

المطلوب:

- `public bootstrap`
- `public operational capabilities`
- `public create order`

تقرأ مستويين:

- `feature enabled`
- `runtime available`

### 3. إخفاء التوصيل من الواجهة العامة عند تعطيله وظيفيًا

إذا كان `delivery_feature_enabled = false`:

- لا يظهر خيار التوصيل أصلًا
- تبقى:
  - `takeaway`
  - `dine-in`

### 4. عدم كسر الطلبات القديمة

عند تعطيل التوصيل:

- يمنع إنشاء طلبات توصيل جديدة
- لا تُكسر طلبات التوصيل القديمة
- تبقى قابلة للتسوية والمراجعة

### 5. فصل دورة المطبخ عن البيع العادي

إذا كان `kitchen_feature_enabled = false`:

- لا يجب أن يمنع هذا البيع العادي
- بل يجب أن ينتقل الطلب إلى `workflow profile` مبسط

وهذا يستلزم إلغاء الاعتماد الحالي في:

- [public.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/public.py)

حيث يتم اليوم منع إنشاء الطلب العام إذا كان المطبخ غير متاح.

### 6. تثبيت جهة التوصيل الداخلية الافتراضية

هذا القرار صالح ويمكن إغلاقه دون كسر النظام الحالي:

- كل سائق داخلي ينتمي إلى جهة داخلية افتراضية
- كل شركة خارجية تمثل جهة مستقلة
- السائقون يظلون في نفس لوحة التوصيل

---

## 5. منطق تعطيل التوصيل بدون كسر النظام

المنطق الصحيح المختصر:

### إذا كان التوصيل معطلًا وظيفيًا

- يختفي من الواجهة العامة
- يمنع في الخلفية عند إنشاء طلب جديد
- تبقى الطلبات القديمة
- تبقى قناة التوصيل متاحة للمراجعة إذا كانت هناك التزامات قائمة

### إذا كان التوصيل مفعّلًا لكن غير جاهز تشغيليًا

- يظهر كمغلق مؤقتًا
- مع رسالة قصيرة مباشرة
- لا يتعطل باقي النظام

### القرار

هذا أفضل من:

- كسر نموذج الطلب
- أو إخفاء كامل القناة الإدارية
- أو ربط التمكين بوجود مستخدم واحد فقط

---

## 6. منطق تعطيل المطبخ بدون كسر النظام

هذه العقدة هي الأهم، لأن المطبخ اليوم مرتبط مباشرة بحالة الطلب.

## 6.1 المشكلة الحالية

المنع الحالي في:

- [public.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/public.py)

يجعل غياب المطبخ يكسر إنشاء الطلب العام.

وهذا غير صحيح إذا كان المطلوب فقط:

- إيقاف لوحة المطبخ
- مع استمرار البيع اليدوي أو العام

## 6.2 الحل الصحيح

نفصل بين:

- `هل دورة المطبخ مفعلة`
- `هل البيع مفعّل`

## 6.3 المسار المبسط المقترح عند تعطيل المطبخ

### للطلبات العادية

- `CREATED`
- `CONFIRMED`
- `READY`

### لطلبات التوصيل

- `CREATED`
- `CONFIRMED`
- `READY`
- `OUT_FOR_DELIVERY`
- `DELIVERED / DELIVERY_FAILED`

## 6.4 أثر ذلك على التتبع العام

واجهة التتبع يجب ألا تفترض أن:

- `قيد التحضير`
- `أُرسل للمطبخ`

مراحل ثابتة دائمًا

بل تبني الخطوات حسب:

- `workflow profile`

وهذا قرار يمكن إغلاقه على النظام الحالي بدون كسر:

- حالات الطلب الأساسية تبقى
- فقط نغيّر ما الذي يمر عبره الطلب قبل `READY`

---

## 7. فصل الأنظمة داخل الكود بشكل منطقي

الهدف ليس فقط تمكين/تعطيل ميزة، بل جعل الفصل واضحًا داخل المعمارية.

## 7.1 ما يجب اعتباره Module فعليًا

### التوصيل

يجب أن يملك:

- `feature flag`
- `runtime availability`
- `provider model`
- `driver execution`

### المطبخ

يجب أن يملك:

- `feature flag`
- `runtime availability`
- `workflow profile`

### الواجهة العامة

يجب أن تقرأ هذه العقد من:

- `public bootstrap`
- أو عقدة capabilities موحدة

ولا تستنتجها محليًا

## 7.2 ما يجب ألا يحدث

- لا تضع منطق تعطيل الأنظمة داخل الواجهة فقط
- لا تربط التتبع العام دائمًا بمراحل المطبخ
- لا تجعل لوحة السائق تمثل شركة توصيل
- لا تجعل إعدادات التوصيل مصدر قرار المطبخ

---

## 8. مراجعة خطاب النصوص الظاهرة للمستخدم

المشكلة الحالية ليست في كل النصوص، لكنها ما زالت تظهر في عدة مناطق:

- وصف يشرح الفكرة للمطور بدل المستخدم
- نصوص طويلة جدًا في بطاقات الواجهات
- عبارات مثل:
  - "تشغيل مباشر"
  - "قناة"
  - "منظور تشغيلي"
  - "محرك"
  - "عقدة"
  - "النظام يستهلك"

هذه عبارات قد تكون مقبولة داخل الوثائق، لكنها ليست مناسبة دائمًا داخل الواجهة.

## 8.1 القاعدة الصارمة

كل نص ظاهر في الواجهة يجب أن يجيب على واحد فقط من هذه الأسئلة:

- ماذا أرى الآن؟
- ماذا يمكنني أن أفعل الآن؟
- ما الحالة الحالية؟

وما عدا ذلك يجب تقليصه أو حذفه.

## 8.2 النبرة المطلوبة حسب السياق

### الصفحات التشغيلية

مثل:

- الطلبات
- الطاولات
- التوصيل
- المطبخ

النبرة:

- مباشرة
- قصيرة
- فعلية

أمثلة:

- `طلبات جاهزة`
- `بانتظار التوزيع`
- `ابدأ التحضير`
- `أرسل للتوصيل`

### الصفحات الإدارية

مثل:

- الإعدادات
- المستخدمون
- سجل التدقيق
- شجرة العناوين

النبرة:

- إدارية
- واضحة
- بدون شرح تقني

أمثلة:

- `اسم الجهة`
- `متاح للعامة`
- `رسم التوصيل`
- `آخر تغيير`

### الواجهة العامة للعميل

النبرة:

- مختصرة جدًا
- موجهة للقرار
- خالية من المصطلحات الداخلية

أمثلة:

- `اختر طلبك`
- `أضف للسلة`
- `طريقة الاستلام`
- `تابع الطلب`

## 8.3 القنوات والواجهات التي تحتاج مراجعة نصية لاحقة

الأولوية الأعلى:

1. `Delivery settings / team / board`
2. `System hub / settings`
3. `Warehouse dashboard`
4. `Finance transactions`
5. `Reports / operational heart`
6. `Public tracking`

السبب:

- هذه المناطق فيها أعلى احتمال لاختلاط الخطاب التشغيلي بالشرح المفاهيمي

---

## 9. الملفات التي تجاوزت 1000 سطر

بعد استبعاد الملفات غير المصدرية وملفات `node_modules` و`.venv`:

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

## 10. خطة تقليص الملفات الكبيرة

## 10.1 أولوية أولى

### [OrdersPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/operations/orders/OrdersPage.tsx)

يفكك إلى:

- `hooks/useOrderFilters.ts`
- `hooks/useOrderActions.ts`
- `components/OrdersToolbar.tsx`
- `components/OrdersTable.tsx`
- `components/OrderDetailsModal.tsx`
- `components/OrderCreateModal.tsx`

### [manager.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/manager.py)

يفكك إلى:

- `manager_orders.py`
- `manager_delivery.py`
- `manager_finance.py`
- `manager_settings.py`
- `manager_users.py`
- `manager_audit.py`

### [schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py)

يفكك حسب النطاق:

- `schemas/orders.py`
- `schemas/delivery.py`
- `schemas/finance.py`
- `schemas/system.py`
- `schemas/warehouse.py`
- `schemas/public.py`

## 10.2 أولوية ثانية

### [FinancialPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/finance/transactions/FinancialPage.tsx)

يفكك حسب المشاهد:

- الملخص
- الصندوق
- القيود
- التسويات
- الإغلاقات

### [ProductsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/system/catalog/products/ProductsPage.tsx)

يفكك إلى:

- نموذج المنتج
- ربط المنتجات الثانوية
- مكونات الاستهلاك
- أدوات التصنيف
- الأرشفة

### [WarehousePage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/warehouse/dashboard/WarehousePage.tsx)

يفكك حسب الصفحات المدمجة داخله، لأن تقليص القناة لم يتبعه بعد تفكيك الملف نفسه.

## 10.3 أولوية ثالثة

- [ReportsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/intelligence/reports/ReportsPage.tsx)
- [types.ts](/c:/Users/stormpc/Desktop/Restaurants/src/shared/api/types.ts)
- [warehouse_services.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/warehouse_services.py)
- [operations_repository.py](/c:/Users/stormpc/Desktop/Restaurants/backend/infrastructure/repositories/operations_repository.py)

---

## 11. ما يجب تنفيذه لاحقًا وما يجب تجميده

## 11.1 خطوات يمكن إغلاقها على النظام الحالي

1. إضافة `feature flags` مستقلة للتوصيل والمطبخ
2. تعديل `public bootstrap` و`public create order`
3. جعل التتبع العام يعتمد `workflow profile`
4. إنشاء `جهة توصيل داخلية افتراضية`
5. ربط كل سائق بجهة توصيل
6. بدء تفكيك الملفات الكبيرة ذات الأولوية الأولى

## 11.2 خطوات يجب تجميدها الآن

1. استبدال `delivery_assignments`
2. إعادة بناء حالات الطلب من الصفر
3. تحويل شركة التوصيل إلى سائق أو مستخدم `delivery` عادي
4. ربط التلجرام مباشرة بحالات الطلب بدون طبقة توزيع واضحة
5. توسيع مسار المزود الخارجي للعناوين

---

## 12. القرار النهائي

المنطق الصحيح الذي يجب اعتماده من الآن:

- جهة توصيل داخلية افتراضية موجودة دائمًا
- شركة التوصيل كيان مستقل، لا سائق
- السائق يدار من لوحة التوصيل فقط
- تعطيل التوصيل يخفيه من الواجهة العامة ولا يكسر الطلبات الأخرى
- تعطيل المطبخ لا يجب أن يكسر البيع، بل يبدّل مسار الطلب إلى دورة مبسطة
- النصوص الظاهرة للمستخدم يجب أن تكون تنفيذية ومباشرة، لا تشرح النظام من الداخل
- الملفات الثقيلة يجب أن تفكك حسب المسؤولية، لا لمجرد تقليل السطور

هذا هو المسار الأقصر، والأكثر أمانًا، والأقل كلفة على النظام الحالي.
