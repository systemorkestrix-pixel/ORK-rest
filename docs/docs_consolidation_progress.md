# ملف التقدم الموحد لمجلد Docs

تاريخ البدء: `2026-03-28`

هذا الملف يتتبع فقط:

- ما تم تثبيته داخل `docs`
- ما تم جمعه في المرجع الجامع
- ما تبقى من ملفات حية
- ما يمكن أرشفته

المرجع الأعلى المرتبط به:

- [docs_consolidation_master_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/docs_consolidation_master_report.md)

---

## 1. الحالة العامة

الحالة الحالية: `قيد التنظيم النهائي`

النتيجة الحالية:

- تم إنشاء مرجع جامع
- تم فصل الملفات إلى:
  - حية
  - مساعدة
  - تاريخية
- لم تتم الأرشفة النهائية بعد

---

## 2. جدول التقدم

### المرحلة A: جمع الملفات وتحديد حالتها

الحالة: `مغلق`

المنجز:

- إحصاء جميع ملفات `docs`
- تصنيفها إلى:
  - مراجع حية
  - مراجع مساعدة
  - مراجع تاريخية

### المرحلة B: إنشاء المرجع الجامع

الحالة: `مغلق`

المنجز:

- إنشاء [docs_consolidation_master_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/docs_consolidation_master_report.md)

### المرحلة C: إنشاء ملف التقدم الموحد

الحالة: `مغلق`

المنجز:

- إنشاء هذا الملف وربطه بالمرجع الجامع

### المرحلة D: نقل الملفات التاريخية إلى الأرشيف

الحالة: `مغلق`

العناصر المرشحة:

- [delivery_location_provider_strategy.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/delivery_location_provider_strategy.md)
- [console_rebuild_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_plan.md)
- [console_rebuild_progress.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_progress.md)
- [console_rebuild_tasks.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_tasks.md)
- [ui_audit_execution_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/ui_audit_execution_plan.md)
- [ui_audit_execution_progress.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/ui_audit_execution_progress.md)

شرط الإغلاق:

- التأكد أن لا قرار حي يعتمد عليها وحدها

النتيجة:

- تم إنشاء `docs/archive/`
- تم نقل الملفات التاريخية إليه
- بقيت الملفات الحية والمساعدة فقط في جذر `docs`

### المرحلة E: توحيد المراجع الحية وتقليل التكرار

الحالة: `مغلق`

المطلوب:

- مراجعة التداخل بين:
  - `final_delivery_maintenance_plan`
  - `delivery_module_toggle_and_large_files_review`
  - `markdown_status_and_system_toggle_audit`
- إبقاء كل ملف له غرض واحد فقط

النتيجة:

- تم تثبيت حدود كل وثيقة داخلها نفسها
- أصبح التقسيم كالتالي:
  - `final_delivery_maintenance_plan` = مرجع الإغلاق والتسليم
  - `delivery_module_toggle_and_large_files_review` = مرجع العقدة المعمارية للتوصيل/المطبخ/الملفات الكبيرة
  - `markdown_status_and_system_toggle_audit` = مرجع تدقيق الوثائق والخطاب النصي
- لم يعد هناك تداخل وظيفي غير محسوم بين هذه الملفات الثلاثة

### المرحلة F: إنشاء فهرس نهائي لمجلد Docs

الحالة: `مؤجل قريب`

المطلوب:

- ملف فهرسة مختصر يوجه مباشرة إلى:
  - المرجع الجامع
  - ملف التقدم
  - أهم المراجع الحية

### المرحلة G: تثبيت الحسم التنفيذي النهائي

الحالة: `مغلق`

المنجز:

- تثبيت قاعدة الواجهة المختصرة: فهم النظام خلال 10 ثوان
- تثبيت أن فصل الأنظمة يسبق أي منصة متعددة المطاعم
- تثبيت أن النسخ المتفاوتة للعملاء ستبنى عبر `module-based editions`
- تثبيت أن `Product Control Center` مؤجل إلى ما بعد feature flags وفصل الوحدات

الأثر:

- لم يعد هناك تردد بين:
  - التنفيذ الحالي
  - والتحكم المستقبلي في النسخ
  - وطبقة تعدد المطاعم

### المرحلة H: تثبيت مرحلة الصقل الاحترافي وجاهزية التوزيع

الحالة: `مغلق`

المنجز:

- إنشاء [system_refinement_and_distribution_readiness_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/system_refinement_and_distribution_readiness_plan.md)
- تثبيت الصقل كمرحلة ضبط تشغيلية لا كتجميل بصري فقط
- تثبيت قاعدة أن كل واجهة وكل جدول يجب أن يجيب عن السؤال المتوقع للمستخدم مباشرة
- تثبيت `لوحة التحكم الأم` كهدف استراتيجي لاحق لتوزيع النسخ على المطاعم

الأثر:

- لم يعد الصقل يُعامل كتعديلات متفرقة
- بل صار مسارًا رسميًا موجّهًا لما قبل التوزيع الحقيقي للنظام

### المرحلة I: تثبيت فصل قناة التوصيل بين التشغيل والإعدادات

الحالة: `مغلق`

المنجز:

- إنشاء [delivery_channel_operational_vs_settings_split_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_channel_operational_vs_settings_split_plan.md)
- تثبيت أن قناة التوصيل تحتاج 3 أسطح منفصلة:
  - تشغيل إداري
  - إعدادات وتحكم
  - لوحة جهة خاصة
- تثبيت أن استمرار صقل الجداول داخل صفحة فريق التوصيل قبل هذا الفصل سيبقي الخلط قائمًا مهما تحسنت الجداول نفسها
- تنفيذ الفصل فعليًا داخل الواجهة بين:
  - [DeliveryTeamPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/delivery/drivers/DeliveryTeamPage.tsx)
  - [DeliverySettingsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/delivery/settings/DeliverySettingsPage.tsx)

---

## 3. العناصر الحية التي لا يجب نسيانها

1. رحلة الواجهة العامة
2. شجرة عناوين التوصيل اليدوية
3. تعطيل التوصيل والمطبخ بدون كسر النظام
4. جهة التوصيل الداخلية الافتراضية
5. ربط المنتجات بالمخزون والاستهلاك النظري
6. تنظيم اللوحات والمسارات
7. تفكيك الملفات الكبيرة
8. ضبط خطاب النصوص للمستخدم النهائي
9. الصقل الاحترافي وجاهزية التوزيع

---

## 4. العناصر التي لم تغلق برمجيًا بعد

1. `delivery_feature_enabled`
2. `kitchen_feature_enabled`
3. `workflow profile` في التتبع العام والطلب العام
4. `Delivery Provider` ككيان فعلي في البيانات
5. ربط جميع السائقين بجهة توصيل
6. تفكيك الملفات الكبيرة ذات الأولوية الأولى
7. تنفيذ مرحلة الصقل الاحترافي على القنوات الثقيلة:
   - المطعم
   - العمليات
   - المخزون
   - المالية
8. التحضير لمرحلة `Product Control Center` بعد تثبيت وضوح الوحدات والواجهات

---

## 5. قاعدة التحديث

من الآن:

- أي خطة جديدة لا تنشأ مباشرة كملف منفصل إلا إذا كان لها سبب واضح
- يجب أولًا تسجيلها هنا وفي المرجع الجامع
- إذا كانت مجرد امتداد لخطة حية، فتضاف إلى المرجع القائم بدل إنشاء ملف جديد

---

## 6. القرار الحالي

مجلد `docs` لم يعد يحتاج إلى جمع إضافي عشوائي.

الخطوة الصحيحة التالية هي:

1. اعتماد هذين الملفين كمرجعين أعلى
2. ثم مراجعة التداخل بين الملفات الحية قبل أي حذف نهائي
3. ثم إنشاء فهرس مختصر لمجلد `docs`
