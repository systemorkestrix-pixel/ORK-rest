# التقرير القطعي الجامع لملفات Docs

تاريخ التثبيت: `2026-03-28`

هذا الملف هو المرجع الجامع الأعلى لمجلد `docs`.

وظيفته:

- جمع الخطط والمراحل والقرارات الحية في مكان واحد
- تحديد ما هو مرجع فعلي وما هو تاريخي أو انتقالي
- منع ضياع خطوة أو قرار أو مسار ما زال مطلوبًا
- تمهيد تنظيف مجلد `docs` بدون حذف شيء ما زال يؤثر على النظام

القاعدة من الآن:

- أي قرار حي أو مسار تنفيذ حالي يجب أن يكون له أثر واضح داخل هذا الملف
- أي ملف خارج هذا المرجع يقيّم على أنه:
  - `مرجع حي`
  - `مرجع مساعد`
  - `مرجع تاريخي`
  - `مرشح للأرشفة`

---

## 1. الحالة العامة

لا، قبل هذه الخطوة لم تكن جميع الخطط والمراحل مجمعة في ملف واحد قطعي.

الوضع السابق كان كالتالي:

- لدينا ملفات قوية وصحيحة
- لكن القرارات موزعة على أكثر من وثيقة
- وبعض الملفات أصبحت تاريخية أو انتقالية
- وبعضها ما زال يحتوي أجزاء صالحة لكن ليس هو المرجع الأعلى

لهذا أصبح من الضروري اعتماد هذا الملف كمرجع جمع نهائي.

---

## 2. تصنيف ملفات Docs الحالية

## 2.1 مراجع حية مباشرة

هذه الملفات ما زالت فعالة ويجب الحفاظ عليها:

1. [project_state_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/project_state_report.md)
   - يحدد حالة المشروع العامة ونظافته

2. [operating_model_ui_map.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operating_model_ui_map.md)
   - يحدد ملكية اللوحات والمسارات

3. [operating_model_user_guide.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operating_model_user_guide.md)
   - يشرح التشغيل للمستخدم النهائي

4. [operational_ui_principles.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operational_ui_principles.md)
   - القواعد البصرية والخطابية الموحدة

5. [public_order_journey_execution_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/public_order_journey_execution_plan.md)
   - مرجع رحلة الطلب العامة

6. [delivery_manual_address_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_manual_address_plan.md)
   - مرجع شجرة عناوين التوصيل اليدوية

7. [delivery_module_toggle_and_large_files_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_module_toggle_and_large_files_review.md)
   - مرجع عقدة التوصيل/المطبخ وتعطيل الأنظمة وتقليص الملفات الكبيرة

8. [inventory_consumption_phase1_master_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/inventory_consumption_phase1_master_plan.md)
   - مرجع الاستهلاك النظري وربط المنتجات بالمخزون

9. [final_delivery_maintenance_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/final_delivery_maintenance_plan.md)
   - مرجع إغلاق وصيانة النظام قبل التسليم

10. [markdown_status_and_system_toggle_audit.md](/c:/Users/stormpc/Desktop/Restaurants/docs/markdown_status_and_system_toggle_audit.md)
   - مرجع تدقيق الوثائق الحالية وعقدة تعطيل الأنظمة وخطاب الواجهة

11. [system_refinement_and_distribution_readiness_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/system_refinement_and_distribution_readiness_plan.md)
   - مرجع مرحلة الصقل الاحترافي وجاهزية توزيع النظام ولوحة التحكم الأم

## 2.2 مراجع مساعدة

هذه الملفات ما زالت مفيدة، لكن دورها داعم لا قطعي:

1. [ui_audit_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/ui_audit_report.md)
2. [ui_logic_audit_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/ui_logic_audit_report.md)
3. [stats_cards_audit_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/stats_cards_audit_report.md)

دورها:

- استخراج تحسينات واجهة
- ضبط ملكية الأدوات
- تقليل بطاقات الإحصاءات

لكنها لا يجب أن تكون مصدر القرار الأعلى وحدها.

## 2.3 مراجع تاريخية أو انتقالية

هذه الملفات لا تمد أي تنفيذ جديد مباشرة:

1. [delivery_location_provider_strategy.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/delivery_location_provider_strategy.md)
   - مسار ملغى استراتيجيًا

2. [console_rebuild_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_plan.md)
3. [console_rebuild_progress.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_progress.md)
4. [console_rebuild_tasks.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/console_rebuild_tasks.md)

5. [ui_audit_execution_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/ui_audit_execution_plan.md)
6. [ui_audit_execution_progress.md](/c:/Users/stormpc/Desktop/Restaurants/docs/archive/ui_audit_execution_progress.md)

هذه الملفات نُقلت فعليًا إلى:

- `docs/archive/`

وهي الآن محفوظة كأرشيف قرار لا كمرجع تنفيذي حي.

---

## 3. الخطوط التنفيذية الحية المجمعة

## 3.1 الواجهة العامة

المصدر الحي:

- [public_order_journey_execution_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/public_order_journey_execution_plan.md)

المسار الحي:

- رحلة طلب مرحلية
- مكملات المنتجات
- اختيار طريقة الاستلام
- تتبع الطلب
- هوية الواجهة العامة من الإعدادات

الحالة:

- حي ومطلوب استكماله وتحسينه

## 3.2 التوصيل

المصادر الحية:

- [delivery_manual_address_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_manual_address_plan.md)
- [delivery_module_toggle_and_large_files_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_module_toggle_and_large_files_review.md)
- [final_delivery_maintenance_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/final_delivery_maintenance_plan.md)

المسار الحي:

- عناوين توصيل يدوية
- تسعير حسب العقد
- جهة توصيل داخلية افتراضية
- فصل الشركة عن السائق
- تعطيل التوصيل بدون كسر الطلبات

الحالة:

- حي ومهم جدًا

## 3.3 المطبخ وتعطيل الأنظمة

المصدر الحي:

- [delivery_module_toggle_and_large_files_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_module_toggle_and_large_files_review.md)
- [markdown_status_and_system_toggle_audit.md](/c:/Users/stormpc/Desktop/Restaurants/docs/markdown_status_and_system_toggle_audit.md)

المسار الحي:

- إضافة `feature flags`
- فصل `runtime availability` عن `feature enablement`
- منع كسر البيع عند تعطيل المطبخ
- جعل التتبع يعتمد `workflow profile`

الحالة:

- لم يغلق برمجيًا بعد
- ويجب أن يكون من أولويات التنفيذ القادمة

## 3.4 المخزون والاستهلاك

المصدر الحي:

- [inventory_consumption_phase1_master_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/inventory_consumption_phase1_master_plan.md)

المسار الحي:

- `primary / secondary`
- ربط المنتج بالمخزون
- استهلاك نظري يومي
- صرف مخزني مشتق
- أثر مالي مشتق

الحالة:

- حي وممتد على مراحل

## 3.5 تنظيم اللوحات والمسارات

المصادر الحية:

- [project_state_report.md](/c:/Users/stormpc/Desktop/Restaurants/docs/project_state_report.md)
- [operating_model_ui_map.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operating_model_ui_map.md)
- [final_delivery_maintenance_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/final_delivery_maintenance_plan.md)

المسار الحي:

- فصل الإعدادات والتنبيهات ومركز النظام عن الشريط الثانوي
- تثبيت ملكية الصفحات
- منع خلط الإدارة بالتنفيذ

الحالة:

- جزء كبير منه منجز
- وما تبقى هو التنظيف النهائي والضبط البصري والخطابي

## 3.6 الصقل الاحترافي وجاهزية التوزيع

المصدر الحي:

- [system_refinement_and_distribution_readiness_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/system_refinement_and_distribution_readiness_plan.md)

المسار الحي:

- إعادة ترتيب الجداول بناءً على الأسئلة المتوقعة للمستخدم
- تثبيت قاعدة: كل عمود يقدم جوابًا واضحًا لا معنى مكررًا
- ضبط النوافذ والنماذج حسب القرار التالي لا حسب كثافة البيانات
- صقل الواجهات الثقيلة قبل التوزيع الحقيقي
- تثبيت `لوحة التحكم الأم` كهدف استراتيجي لاحق لتوزيع النسخ على المطاعم

الحالة:

- حي ومفتوح
- ويعد المرحلة الضبطية التي تسبق التوزيع الفعلي للنظام

---

## 4. الخطوات التي تغيّر مسارها نهائيًا

هذه القرارات تغيّرت ولا يجب أن يعود النظام إليها:

1. الاعتماد على مزود خارجي للعناوين
2. اعتبار شركة التوصيل سائقًا
3. اعتبار وجود مستخدم نشط بديلًا عن تمكين الوظيفة نفسها
4. إظهار نصوص داخل الواجهة تشرح النظام للمطور بدل المستخدم
5. الإبقاء على ملفات `docs` التنفيذية القديمة كمرجع أعلى

---

## 5. الخطوات التي ما زال يمكن إغلاقها على النظام الحالي

هذه الخطوات ما زالت قابلة للإغلاق بدون هدم كبير:

1. `feature flags` للمطبخ والتوصيل
2. `workflow profile` للتتبع والطلب العام
3. `Delivery Provider` داخلي افتراضي
4. ربط جميع السائقين بجهة توصيل
5. تنظيف خطاب الواجهة في القنوات الثقيلة
6. تفكيك الملفات التي تجاوزت 1000 سطر حسب الأولوية

---

## 6. الملفات الكبيرة التي تتطلب اختصارًا معماريًا

المرجع الكامل موجود في:

- [delivery_module_toggle_and_large_files_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/delivery_module_toggle_and_large_files_review.md)

الأولوية الأولى:

1. [OrdersPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/operations/orders/OrdersPage.tsx)
2. [manager.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/manager.py)
3. [schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py)

الأولوية الثانية:

4. [FinancialPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/finance/transactions/FinancialPage.tsx)
5. [ProductsPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/system/catalog/products/ProductsPage.tsx)
6. [WarehousePage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/warehouse/dashboard/WarehousePage.tsx)

---

## 7. الخطاب النصي داخل الواجهات

القاعدة النهائية:

- أي نص داخل الواجهة يجب أن يخاطب المستخدم النهائي أو الإداري المباشر
- لا يشرح الفكرة التقنية
- لا يصف “المعمارية”
- لا يستخدم مفردات داخلية إلا إذا كانت ضرورية جدًا

الأولوية الأعلى للمراجعة النصية:

1. التوصيل
2. الإعدادات
3. المستودع
4. المالية
5. التتبع العام
6. التقارير

---

## 8. خطة تنظيف مجلد Docs

لا يجب تنظيف المجلد دفعة واحدة.

الترتيب الصحيح:

### المرحلة 1

تثبيت هذا الملف + ملف التقدم الموحد.

### المرحلة 2

نقل الملفات التاريخية إلى:

- `docs/archive/`

### المرحلة 3

الإبقاء فقط على:

- المراجع الحية
- المراجع المساعدة
- الأرشيف

### المرحلة 4

تحديث `README` أو ملف فهرس لاحقًا ليشير إلى:

- المرجع الجامع
- ملف التقدم

---

## 9. القرار النهائي

من الآن:

- هذا الملف هو المرجع الجامع
- وملف التقدم الموحد هو مرجع التنفيذ
- وأي ملف `docs` آخر يقيّم نسبةً إلى هذين المرجعين

وبهذا يمكن تنظيف مجلد `docs` لاحقًا بدون خوف من فقد قرار أو مرحلة أو عنصر أساسي.

---

## 10. الحسم التنفيذي النهائي قبل بدء التنفيذ

هذه هي القواعد النهائية التي نعتمدها قبل الدخول في التنفيذ المباشر.

## 10.1 قاعدة الواجهة: فهم النظام خلال 10 ثوان

أي واجهة سنبقيها أو نعيد بناؤها يجب أن تحقق الآتي:

- يعرف المستخدم أين هو الآن
- يعرف ما الذي يمكنه فعله الآن
- يعرف ما الحالة أو الرقم الذي يحتاج متابعته الآن

وما عدا ذلك:

- يحذف
- أو ينقل إلى مستوى ثانوي
- أو يختصر

هذا يعني:

- لا شروحات مطولة داخل الواجهة
- لا نصوص تشرح المعمارية
- لا بطاقات كثيرة بدون قرار مباشر
- لا خلط بين التنفيذ والإدارة

## 10.2 قاعدة فصل الأنظمة

من الآن النظام يقسم منطقيًا إلى وحدات مستقلة يمكن تشغيلها أو تعطيلها:

1. `orders`
2. `tables`
3. `kitchen`
4. `delivery`
5. `warehouse`
6. `finance`
7. `public_ordering`
8. `alerts`
9. `reports`
10. `system_admin`

كل وحدة يجب أن تملك لاحقًا:

- `feature flag`
- `runtime availability`
- حدودًا واضحة في الواجهة
- حدودًا واضحة في الخلفية

## 10.3 قاعدة الإصدارات المتفاوتة للعملاء

نعم، هذا المسار يجب أن يدعم تسليم نسخ متفاوتة التقدم.

لكن الحسم المعماري هنا هو:

- لا نبني الآن `multi-tenant platform` كاملة
- ولا نبني الآن `subscription system`
- بل نبني أولًا `طبقة تمكين وحدات`

النسخ المتفاوتة في المرحلة الحالية تكون عبر:

- تمكين/تعطيل الوحدات
- لا عبر فصل قاعدة بيانات أو بنية مستقلة لكل عميل

### النسخ المقترحة

#### نسخة أساسية

- الطلبات
- الطاولات
- الواجهة العامة
- المستخدمون الأساسيون

#### نسخة تشغيل موسعة

- النسخة الأساسية
- المطبخ
- التوصيل
- التنبيهات

#### نسخة تشغيل كاملة

- النسخة الموسعة
- المخزون
- المالية
- التقارير

هذا هو التدرج الصحيح حاليًا.

## 10.4 بند لوحة تقديم النظام للعملاء والتحكم في صلاحيات كل مطعم

هذا البند صحيح استراتيجيًا، لكنه لا يدخل في نفس المرحلة التنفيذية الحالية مباشرة.

### القرار

نقسم هذا البند إلى طبقتين:

#### الطبقة الأولى: قابلة للتنفيذ على النظام الحالي

`Product Control Center`

هدفها:

- التحكم في تفعيل الوحدات
- تحديد شكل النسخة المسلمة
- ضبط ما يظهر وما يختفي في الواجهة

لكن داخل نظام واحد وفي سياق تشغيل واحد.

هذه الطبقة يمكن بناؤها فوق:

- `system settings`
- `feature flags`
- `capabilities`

#### الطبقة الثانية: مؤجلة لما بعد تثبيت الفصل

`Restaurant-by-Restaurant Control`

هذه تتطلب لاحقًا:

- `restaurant entity` حقيقي يملك هوية مستقلة
- ربط الإعدادات والتمكين به
- طبقة صلاحيات على مستوى كل مطعم
- وربما لاحقًا طبقة عميل/عقد/خطة

### الحسم الصارم

لا نخلط بين:

- `فصل الأنظمة`
- و`منصة متعددة المطاعم`

الأول ندخله الآن
والثاني نؤجله إلى ما بعد تثبيت الأول

## 10.5 ماذا يعني هذا على مستوى التنفيذ المباشر

المرحلة التالية لا تكون:

- شركة توصيل
- أو منصة عملاء
- أو لوحة مالك النظام

بل تكون:

1. `feature flags` للمطبخ والتوصيل
2. تعديل `public bootstrap` و`public create order`
3. `workflow profile` للتتبع والطلب
4. تثبيت `delivery provider الداخلي`
5. ربط السائقين بجهة توصيل

ثم فقط بعد ذلك:

6. `Product Control Center`

## 10.6 تعريف Product Control Center

إذا دخلناه لاحقًا، فوظيفته تكون:

- تمكين/تعطيل الوحدات
- اختيار النسخة المسلمة
- مراقبة ما هو مفعل في النظام
- إظهار أثر التمكين على:
  - القنوات
  - الواجهة العامة
  - لوحات التنفيذ

ولا تكون وظيفته في مرحلته الأولى:

- إدارة اشتراكات
- فوترة العملاء
- إنشاء مطاعم متعددة
- إدارة عقود تجارية

## 10.7 القرار التنفيذي النهائي

للدخول في التنفيذ بدون تشتيت نعتمد الآتي:

### أ. الواجهة

- مختصرة
- مباشرة
- تفهم خلال 10 ثوان

### ب. المعمارية

- الأنظمة تفصل إلى وحدات قابلة للتمكين
- لا تعتمد على وجود المستخدمين فقط

### ج. التسليم للعملاء

- يبدأ عبر `module-based editions`
- لا عبر منصة متعددة المطاعم من البداية

### د. لوحة التحكم المستقبلية

- تدخل بعد تثبيت فصل الوحدات
- لا قبل ذلك
