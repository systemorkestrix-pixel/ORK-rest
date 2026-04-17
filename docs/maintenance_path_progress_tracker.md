# متتبع مسار الصيانة

آخر تحديث: `2026-04-16`

الحالة العامة: `المسار أعيد تعريفه من الخطط إلى النسخة الأساسية + الأدوات الإضافية`

---

## 1. المسار الحاكم الجديد

1. `إغلاق النسخة الأساسية`
2. `تثبيت نموذج النسخة الأساسية + الأدوات الإضافية`
3. `Master Control Plane كلوحة استحقاق وتفعيل أدوات`
4. `Kitchen كأول أداة إضافية`
5. `Delivery كثاني أداة إضافية`
6. `Warehouse`
7. `Finance`
8. `Intelligence`
9. `Reports`

الحكم هنا:

- لم يعد المسار يقوم على `خطط أعلى`
- بل على `نسخة أساسية واحدة` ثم `أنظمة وأدوات مرتبة`

---

## 2. تحديث 2026-04-08

- اعتماد `نظام التذكرة اليدوية` كبديل تشغيلي داخل `Operations` للنسخة الأساسية
- تثبيت حدوده مقابل `Kitchen Module` في:
  - `docs/manual_ticketing_operating_policy.md`
- تنفيذ النسخة الأولى مباشرة داخل صفحة الطلبات:
  - طباعة تذكرة يدوية مختصرة
  - إعادة الطباعة من نافذة الطلب
- بدون إيقاف التشغيل عند تعذر الطباعة

## 3. تحديث 2026-04-09

- إغلاق المسارات العامة المشتركة غير المقيدة بالنسخة:
  - `/order`
  - `/menu`
  - `/track`
  - `/public/tables`
- فرض أن كل واجهة عامة تعمل فقط عبر `/t/<tenant_code>/...`
- تشديد `/api/public/*` حتى لا يقرأ أي مطعم من قاعدة عامة أو من cookie نسخة أخرى
- تثبيت تدقيق الفصل في:
  - `docs/tenant_isolation_audit_2026_04_09.md`

## 4. تحديث 2026-04-14

- اعتماد مرجع حاكم جديد للبيع والتفعيل:
  - `docs/addon_activation_and_unlock_policy.md`
- اعتماد تدقيق إغلاق النسخة الأولى قبل فتح الأدوات الأعلى:
  - `docs/phase_one_closure_and_addon_transition_audit.md`
- تثبيت أن `Kitchen` و`Delivery` مفصولان تشغيليًا، لكن طبقة البيع الحالية لا تزال قديمة
- اعتماد أن صفحة الخطط داخل المطعم ستتحول لاحقًا إلى صفحة `الإضافات`
- اعتماد أن `plan_id` الحالي يصبح طبقة انتقالية داخلية فقط، لا المرجع التجاري النهائي

## 5. تحديث 2026-04-16

- اعتماد مرجع حاكم جديد للأدوات الخلفية الصامتة والإيقاف مع الاحتفاظ بالبيانات:
  - `docs/passive_backoffice_tools_policy.md`
- تثبيت أن:
  - `Finance / Intelligence / Reports`
    - ليست قنوات ظاهرة داخل النسخة الأساسية
    - لكن محركاتها الخلفية الصامتة يجب أن تبدأ استقبال البيانات من أول يوم
- تثبيت أن:
  - `Kitchen / Delivery / Warehouse`
    - تبقى أدوات تشغيلية مغلقة بالكامل حتى فتحها
- اعتماد حالات أداة أوضح:
  - `locked`
  - `passive`
  - `active`
  - `paused`
- اعتماد أن الإيقاف التجاري الصحيح لا يحذف البيانات، بل يوقف:
  - الواجهة
  - التحرير
  - الاستحقاق
  مع الاحتفاظ بالسجل التاريخي

---

## 6. المراحل المكتملة

### 5.1 العمليات

الحالة: `مغلقة مرجعيًا كأساس النسخة الأساسية`

المرجع المعتمد:

- [operations_channel_ui_reference.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operations_channel_ui_reference.md)

### 5.2 الغلاف العام للجوال

الحالة: `مغلق مرجعيًا`

المرجع المعتمد:

- [mobile_shell_ui_reference.md](/c:/Users/stormpc/Desktop/Restaurants/docs/mobile_shell_ui_reference.md)

### 5.3 عزل الواجهة العامة بين المطاعم

الحالة: `مغلق مرجعيًا`

المرجع المعتمد:

- [tenant_isolation_audit_2026_04_09.md](/c:/Users/stormpc/Desktop/Restaurants/docs/tenant_isolation_audit_2026_04_09.md)

---

## 7. المرحلة النشطة الآن

### إغلاق النسخة الأساسية قبل الأدوات الأعلى

الحالة: `هي المسار التنفيذي النشط`

القرار المعتمد:

- لا نفتح `Kitchen` ولا `Delivery` بعد كمرحلة ثانية مباشرة
- نغلق النسخة الأساسية أولًا
- نثبت لغة البيع والتفعيل على أساس الأدوات
- نمنع أي بناء جديد على مفهوم `الخطة الأعلى`

ما يجب إغلاقه في هذه المرحلة:

- التنبيهات
- العزل بين النسخ
- خطاب الواجهة
- مواضع الإشارات إلى الأنظمة غير المفتوحة
- صفحة الموظفين
- الإعدادات المحلية
- صفحة الخطط داخل المطعم وتحويلها لاحقًا إلى `الإضافات`

---

## 8. المرحلة التالية بعدها

### تحديث Master وواجهة المطعم إلى نموذج الأدوات

الحالة: `هي الخطوة الحاكمة التالية`

القرار المعتمد:

- `Master` لا توزع خططًا تجارية، بل تفعّل أدوات مرتبة
- واجهة المطعم لا تعرض `خطط`, بل `الإضافات`
- الأداة التالية فقط هي التي تكون قابلة للطلب
- لا يجوز القفز فوق ترتيب الفتح

النقطة الأولى المطلوبة:

- تحويل طبقة الحوكمة الحالية من `Plan Assignment` إلى `Add-on Entitlement`

---

## 9. مرحلة ما بعد ذلك

### Kitchen

الحالة: `لا تُفتح إلا بعد إغلاق النسخة الأساسية وتحديث الحوكمة`

### Delivery

الحالة: `تأتي بعد Kitchen كأداة مستقلة`

### Warehouse / Finance / Intelligence / Reports

الحالة: `مؤجلة حسب ترتيب الأدوات`

---

## 10. نقطة الرجوع المباشرة

إذا أغلق هذا التحديث التوثيقي بنجاح، فإن نقطة الرجوع التالية تكون:

- `النسخة الأساسية`
- ثم `تحويل الخطط إلى إضافات`
- وليس `فتح المطبخ أو التوصيل مباشرة`

---

## 11. سجل الخروج الاضطراري

### 2026-04-14

الحالة: `لا يوجد خروج اضطراري مفتوح`

الحكم:

- لا يُفتح أي نظام أعلى الآن إلا إذا كان خللًا تشغيليًا قاطعًا داخل النسخة الأساسية

---

## 12. مراجع حاكمة

- [strict_maintenance_guardrails.md](/c:/Users/stormpc/Desktop/Restaurants/docs/strict_maintenance_guardrails.md)
- [operations_channel_ui_reference.md](/c:/Users/stormpc/Desktop/Restaurants/docs/operations_channel_ui_reference.md)
- [mobile_shell_ui_reference.md](/c:/Users/stormpc/Desktop/Restaurants/docs/mobile_shell_ui_reference.md)
- [restaurant_channel_operational_vs_settings_split_review.md](/c:/Users/stormpc/Desktop/Restaurants/docs/restaurant_channel_operational_vs_settings_split_review.md)
- [kitchen_channel_independence_plan.md](/c:/Users/stormpc/Desktop/Restaurants/docs/kitchen_channel_independence_plan.md)
- [master_control_plane_architecture.md](/c:/Users/stormpc/Desktop/Restaurants/docs/master_control_plane_architecture.md)
- [master_control_plane_v1_governance.md](/c:/Users/stormpc/Desktop/Restaurants/docs/master_control_plane_v1_governance.md)
- [addon_activation_and_unlock_policy.md](/c:/Users/stormpc/Desktop/Restaurants/docs/addon_activation_and_unlock_policy.md)
- [phase_one_closure_and_addon_transition_audit.md](/c:/Users/stormpc/Desktop/Restaurants/docs/phase_one_closure_and_addon_transition_audit.md)
- [passive_backoffice_tools_policy.md](/c:/Users/stormpc/Desktop/Restaurants/docs/passive_backoffice_tools_policy.md)
