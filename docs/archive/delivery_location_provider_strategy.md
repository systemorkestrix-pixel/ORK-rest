# Delivery Location Provider Strategy

## Status

This document is no longer the strategic source of truth.

As of `2026-03-22`, the approved direction has changed to the manual address model documented in:

- `docs/delivery_manual_address_plan.md`

The provider-based approach remains documented here only as a reviewed transitional path.

## Goal

إعادة بناء نظام التوصيل ليعتمد على اختيار موقع من قوائم تحديدية بدل إدخال عنوان حر، مع تسعير التوصيل حسب الموقع المختار، وبنموذج عالمي صالح لكل الدول.

## Global Field Model

الترتيب العالمي المعتمد من الآن:

1. `country_code`
2. `country_name`
3. `admin_area_level_1_code`
4. `admin_area_level_1_name`
5. `admin_area_level_2_code`
6. `admin_area_level_2_name`
7. `locality_code`
8. `locality_name`
9. `sublocality_code`
10. `sublocality_name`
11. `postal_code`
12. `location_display_name`

### Semantic Meaning

- `country`: الدولة
- `admin_area_level_1`: الولاية / المحافظة / الإقليم / الولاية الفيدرالية
- `admin_area_level_2`: البلدية / المقاطعة / الدائرة / القضاء
- `locality`: المدينة / البلدة / التجمع الحضري الرئيسي
- `sublocality`: الحي / المنطقة / القطاع / الضاحية

هذه التسمية يجب أن تكون هي التسمية التقنية الموحدة داخل النظام، بينما تبقى العناوين العربية في الواجهة حسب الدولة والسياق.

## Provider Decision

### Accepted Primary Provider

المزود الخارجي المعتمد كخيار أول:

- `GeoNames`

### Why GeoNames

- عالمي ويغطي جميع الدول.
- يقدم hierarchy واضحًا للبلدان والتقسيمات الإدارية.
- يملك Web Services مجانية.
- يتيح JSON endpoints مناسبة للتكامل.
- يمكن البناء فوقه بدون ربط النظام بمزود تجاري مغلق من البداية.

### Official Constraints Verified

بحسب التوثيق الرسمي:

- الخدمات المجانية تتطلب `username` خاصًا بالتطبيق.
- الحد المجاني يقارب `10,000` credits يوميًا و`1,000` في الساعة لكل تطبيق.
- البيانات مجانية مع إسناد المصدر `CC BY`.

## Important Limitation

لا يوجد مزود مجاني خارجي واحد يمكن اعتباره حلًا مثاليًا ونهائيًا للأحياء الدقيقة لكل دول العالم بنفس الجودة.

لذلك القرار المعتمد ليس:

- `provider hard dependency`

بل:

- `provider abstraction + cache + normalized hierarchy`

## Rejected As Primary Public Provider

### Public Nominatim

تم رفض الاعتماد على `public Nominatim` كمزود رئيسي مباشر للإنتاج للأسباب التالية:

- السياسة الرسمية تمنع الاستخدام الثقيل.
- الحد العام منخفض جدًا.
- الخدمة العامة قد تسحب أو تغيّر شروطها.
- لا تصلح كقاعدة تشغيلية أساسية لنظام تجاري يعتمد على اختيارات متعددة ومتكررة.

يمكن استعمال Nominatim لاحقًا فقط كخيار ثانوي أو كمصدر مساعد إذا استُضيف ذاتيًا أو عُزل خلف proxy/cache خاص.

## Implementation Principle

النظام الجديد يجب أن يعمل بهذه القاعدة:

1. اختيار الدولة
2. جلب `admin_area_level_1`
3. جلب `admin_area_level_2`
4. جلب `locality`
5. جلب `sublocality`
6. مطابقة الموقع المختار مع جدول `delivery zone pricing`
7. تطبيق رسوم التوصيل الخاصة بالموقع

## Pricing Principle

التسعير لا يعتمد بعد الآن على:

- `delivery_fee` ثابت عام

بل على:

- `delivery price per location node`

ويكون الحد الأدنى للتوصيل قابلًا لأن يبقى عامًا أو يصبح أيضًا حسب المنطقة في مرحلة لاحقة.

## Architecture Rule

حتى لا نعيد فتح النظام بالترقيع:

- لا يجوز ربط الواجهة مباشرة بمزود خارجي.
- الخلفية هي المسؤولة عن استدعاء المزود.
- يجب وجود طبقة `provider adapter`.
- يجب وجود cache محلي لنتائج المواقع.
- يجب حفظ نسخة normalized من الموقع المختار داخل الطلب.

## Scope Impact

هذا التحديث سيؤثر لاحقًا على:

- `public order journey`
- `delivery settings`
- `order creation`
- `delivery boards`
- `orders tables`
- `tracking`
- `financial delivery revenue`
- `reports and alerts`

## Locked Decision

القرار المعتمد الآن:

- الحقول الدولية التقنية ستبنى على:
  - `country`
  - `admin_area_level_1`
  - `admin_area_level_2`
  - `locality`
  - `sublocality`
- المزود الخارجي الأساسي الأول:
  - `GeoNames`
- عدم اعتماد `public Nominatim` كمصدر إنتاج رئيسي.

## Phase 1 Closure

تم إغلاق المرحلة الأولى برمجيًا بتاريخ `2026-03-22`.

ما أُنجز في هذه المرحلة:

- إنشاء طبقة `provider adapter` للمواقع في الخلفية مع اعتماد `GeoNames`.
- إضافة جدول cache محلي `delivery_location_cache`.
- إضافة عقود backend الجديدة للمواقع الهرمية وإعدادات المزود.
- إضافة مسارات عامة وإدارية لقراءة الدول والعُقد الفرعية.
- إضافة إعدادات النظام الخاصة بالمزود واسم المستخدم ومدة cache.
- تنفيذ migration وتطبيقه على قاعدة التطوير الحالية.

المرحلة تعتبر مغلقة الآن، وأي انتقال لاحق يجب أن يبدأ فقط من:

- إدارة مناطق وأسعار التوصيل حسب العقدة.
- ربط رحلة الطلب العامة بالاختيار الهرمي للموقع.
