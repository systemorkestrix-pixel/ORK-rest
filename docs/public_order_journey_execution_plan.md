# وثيقة التنفيذ التقنية النهائية: الواجهة العامة المرحلية للطلبات

## الحالة الحالية

- الرحلة العامة مغلقة وظيفيًا في `2026-03-29`
- المراحل المكتملة: `1, 2, 3, 4, 5, 6`
- أي تحسينات لاحقة على هذه الواجهة تعتبر صقل تجربة، لا إغلاق بنية أساسية

هذه الوثيقة هي المرجع التنفيذي لبناء واجهة طلب عامة تعمل بمنطق المراحل، وتغلق كل سيناريو طلب بشكل واضح للمستخدم النهائي، مع الاعتماد على المحركات الحالية دون إنشاء نظام موازٍ.

## 1. الهدف التنفيذي

بناء واجهة عامة تجارية تقود العميل عبر رحلة طلب واضحة:

1. اختيار المنتج الأساسي.
2. اختيار المكملات المرتبطة به عند الحاجة.
3. اختيار طريقة الاستلام بعد تكوّن السلة.
4. إدخال البيانات المطلوبة فقط حسب نوع الطلب.
5. مراجعة نهائية واضحة.
6. إرسال الطلب ثم الانتقال إلى حالة تتبع مفهومة.

الهدف ليس مجرد تحسين الشكل، بل رفع القيمة العملية:

- تقليل التشتت.
- رفع وضوح القرار.
- تقليل الأخطاء في الإدخال.
- ربط الواجهة بالعقد الجديد `primary / secondary`.
- الإبقاء على بنية الطلب الخلفية الحالية بدون تعقيد زائد.

---

## 2. القرار المعماري

### 2.1 ما الذي سنبقيه كما هو

- `operations_engine` يبقى محرك الرحلة العامة.
- `CreateOrderInput.items` تبقى مسطحة كما هي.
- `POST /public/orders` يبقى نقطة الاعتماد النهائية لإنشاء الطلب.
- `inventory_engine` لا يدخل مباشرة في رحلة العميل العامة، بل يؤثر عبر `available`.
- `delivery_engine` يبقى مصدر قدرات التوصيل وحالته التشغيلية.
- `core_engine` يبقى مصدر رسوم التوصيل والسياسات العامة.

### 2.2 ما الذي سنضيفه

سنضيف عقدة قراءة واحدة للرحلة العامة:

- `GET /public/order-journey/bootstrap`

وظيفتها جمع البيانات التي تحتاجها الواجهة في أول تحميل، بدل توزيعها على عدة نداءات مستقلة غير مترابطة.

### 2.3 ما الذي لن نقوم به

- لن ننشئ `commerce_engine` جديدًا.
- لن نغيّر هيكل إنشاء الطلب إلى `modifiers payload`.
- لن نضيف `parent_order_item_id`.
- لن نعيد فصل نظام خاص بالمكملات خارج المنتجات.
- لن نخلط مسارات العميل المختلفة في شاشة واحدة مزدحمة.

---

## 3. الوضع الحالي الذي ننطلق منه

### الواجهة الحالية

الواجهة العامة الحالية في:

- [PublicOrderPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/PublicOrderPage.tsx)

وتعتمد على:

- `api.publicProducts()`
- `api.publicTables()`
- `api.publicOperationalCapabilities()`
- `api.publicDeliverySettings()`
- `api.publicTableSession()`
- `api.createPublicOrder()`

### الخلفية الحالية

المسارات العامة الحالية في:

- [public.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/public.py)

والعقود الحالية في:

- [schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py)

والتجميع الحالي للمنتجات العامة في:

- [operations_repository.py](/c:/Users/stormpc/Desktop/Restaurants/backend/infrastructure/repositories/operations_repository.py)

ومنطق الإنشاء الفعلي في:

- [orders.py](/c:/Users/stormpc/Desktop/Restaurants/backend/application/operations_engine/domain/orders.py)

---

## 4. المشكلة الحالية

الواجهة الحالية تعمل، لكنها ليست رحلة شراء مغلقة:

- نوع الطلب يظهر مبكرًا جدًا.
- المكملات غير مضمنة في التجربة العامة.
- الشروط الحرجة مثل الحد الأدنى للتوصيل لا تظهر مبكرًا بما يكفي.
- البيانات موزعة على عدة استعلامات بدل عقدة رحلة واحدة.
- نفس الشاشة تحمل كتالوجًا + سلة + نموذجًا + تتبعًا.

النتيجة:

- ارتفاع الحمل الذهني.
- ضعف وضوح الخطوة التالية.
- تجربة أقل تجارية وأقل مباشرة للعميل.

---

## 5. تجربة الاستخدام المستهدفة

## المرحلة A: ابدأ بطلبك

تعرض:

- عنوان بسيط.
- رسالة قصيرة: "اختر ما تريد أولًا، وسنرشدك بعد ذلك إلى طريقة الاستلام المناسبة."
- كتالوج المنتجات الأساسية فقط.

لا تعرض:

- نوع الطلب.
- الهاتف.
- العنوان.
- الطاولة.

## المرحلة B: اختر المكملات

عند اختيار منتج أساسي:

- تظهر نافذة جانبية أو سفلية بالمكملات المرتبطة به فقط.
- كل مكمل يعرض:
  - الاسم
  - السعر
  - هل هو افتراضي
  - الحد الأعلى للكمية

الهدف:

- ألا يرى العميل "كل شيء في كل وقت".
- بل يرى فقط الخيارات المرتبطة بقراره الحالي.

## المرحلة C: اختر طريقة الاستلام

بعد أن تصبح السلة غير فارغة:

- تظهر بطاقات قرار:
  - `استلام من المطعم`
  - `توصيل للمنزل`
  - `طلب من الطاولة`

كل بطاقة تعرض:

- هل هذا السيناريو متاح الآن.
- وصفًا قصيرًا.
- الرسوم إن وجدت.
- الحد الأدنى إن وجد.
- سبب الإغلاق إن كان غير متاح.

## المرحلة D: أكمل البيانات المطلوبة فقط

### الاستلام

- الهاتف فقط.

### التوصيل

- الهاتف
- العنوان
- إظهار رسوم التوصيل والحد الأدنى بوضوح

### الطاولة

- إذا كان الدخول عبر QR:
  - يعتمد على `table_id` من الرابط
  - لا يطلب طريقة الطلب
  - إذا كانت هناك جلسة نشطة، تعرض أولًا مع زر `إضافة طلب جديد`
- إذا لم يكن عبر QR:
  - يطلب رقم الطاولة فقط إذا كان هذا المسار مفعلًا

## المرحلة E: راجع الطلب

تعرض:

- المنتجات الأساسية
- المكملات تحت كل منتج أو كمجموعة واضحة
- رسوم التوصيل إن وجدت
- الإجمالي النهائي
- الملاحظات

## المرحلة F: تم إرسال الطلب

تعرض:

- رقم الطلب
- الحالة الحالية
- وقت الإنشاء
- الإجراء التالي

---

## 6. السيناريوهات المغلقة

## 6.1 سيناريو الاستلام من المطعم

الرحلة:

1. اختيار المنتجات
2. اختيار المكملات
3. اختيار `استلام من المطعم`
4. إدخال الهاتف
5. مراجعة
6. إرسال
7. تتبع

شروط الإغلاق:

- لا عنوان
- لا اختيار طاولة
- لا ظهور خيارات توصيل

## 6.2 سيناريو التوصيل

الرحلة:

1. اختيار المنتجات
2. اختيار المكملات
3. اختيار `توصيل`
4. إظهار الرسوم + الحد الأدنى
5. إدخال الهاتف والعنوان
6. مراجعة
7. إرسال
8. تتبع

شروط الإغلاق:

- إذا التوصيل غير متاح، لا يسمح بالدخول
- إذا لم يتحقق الحد الأدنى، لا يسمح بالاستمرار

## 6.3 سيناريو الطاولة عبر QR

الرحلة:

1. قراءة `table_id` من الرابط
2. فحص الجلسة الحالية للطاولة
3. إذا توجد جلسة:
   - عرض الجلسة
   - زر `إضافة طلب جديد`
4. اختيار المنتجات
5. اختيار المكملات
6. مراجعة
7. إرسال
8. الرجوع إلى تتبع جلسة الطاولة

شروط الإغلاق:

- لا اختيار نوع الطلب
- لا رقم هاتف
- لا عنوان

## 6.4 سيناريو الطاولة بدون QR

هذا ليس السيناريو التجاري الرئيسي.

يبقى فقط إذا كان المشروع يحتاجه فعليًا.

إن بقي:

1. اختيار المنتجات
2. اختيار `طلب من الطاولة`
3. اختيار الطاولة
4. مراجعة
5. إرسال

---

## 7. العقد الخلفي المقترح

## 7.1 المسار الجديد

`GET /public/order-journey/bootstrap`

المدخلات:

- `table_id?: number`

## 7.2 الاستجابة المقترحة

```json
{
  "meta": {
    "journey_version": "v1",
    "generated_at": "2026-03-20T20:00:00Z"
  },
  "catalog": {
    "categories": [
      {
        "name": "الوجبات",
        "products": [
          {
            "id": 10,
            "name": "بيتزا دجاج",
            "description": "بيتزا دجاج كبيرة",
            "price": 1200,
            "image_path": "/static/products/10.webp",
            "secondary_options": [
              {
                "product_id": 44,
                "name": "سلطة خضراء",
                "price": 250,
                "image_path": null,
                "sort_order": 0,
                "is_default": false,
                "max_quantity": 2
              }
            ]
          }
        ]
      }
    ]
  },
  "capabilities": {
    "kitchen_enabled": true,
    "delivery_enabled": true,
    "kitchen_block_reason": null,
    "delivery_block_reason": null
  },
  "delivery": {
    "delivery_fee": 150,
    "min_order_amount": 800
  },
  "table_context": {
    "table_id": 7,
    "has_table_context": true,
    "has_active_session": true,
    "active_orders_count": 2,
    "unsettled_orders_count": 1,
    "unpaid_total": 2100
  },
  "journey_rules": {
    "allowed_order_types": ["takeaway", "delivery", "dine-in"],
    "default_order_type": "takeaway",
    "require_phone_for_takeaway": true,
    "require_phone_for_delivery": true,
    "require_address_for_delivery": true,
    "allow_manual_table_selection": false
  }
}
```

## 7.3 نماذج الخرج الجديدة

في [schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py) نضيف:

- `PublicSecondaryOptionOut`
- `PublicJourneyProductOut`
- `PublicJourneyCategoryOut`
- `PublicJourneyCatalogOut`
- `PublicJourneyDeliveryOut`
- `PublicJourneyTableContextOut`
- `PublicJourneyRulesOut`
- `PublicOrderJourneyBootstrapOut`

## 7.4 لماذا هذا العقد صحيح

- يجمع بيانات الواجهة في استجابة واحدة.
- لا يغيّر بنية الطلب.
- يستعمل المنتج الأساسي والمكملات من العقد الجديد.
- يخرج قواعد السيناريو صراحة بدل توزيعها داخل الواجهة.
- يبقي القرار التجاري في `operations_engine`.

---

## 8. التغييرات الخلفية المطلوبة ملفًا بملف

## 8.1 العقود

### الملف

- [backend/app/schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py)

### المطلوب

- إضافة نماذج الخرج المذكورة أعلاه.
- توسيع `PublicProductOut` أو الإبقاء عليه كما هو إذا أردنا فصل العقد القديم عن الجديد.

القرار الأفضل:

- الإبقاء على `PublicProductOut` كما هو لتجنب كسر أي مستهلك قديم.
- وإضافة `PublicOrderJourneyBootstrapOut` كعقد مستقل.

## 8.2 الراوتر العام

### الملف

- [backend/app/routers/public.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/public.py)

### المطلوب

- إضافة:
  - `GET /public/order-journey/bootstrap`

يبقى:

- `/public/products`
- `/public/orders`
- `/public/tables`
- `/public/tables/{table_id}/session`
- `/public/delivery/settings`
- `/public/operational-capabilities`

لكن الواجهة الجديدة ستعتمد أولًا على الـ bootstrap.

## 8.3 use case جديد

### ملف جديد

- `backend/application/operations_engine/use_cases/get_public_order_journey_bootstrap.py`

### المسؤولية

- استدعاء مستودع العمليات
- جمع:
  - الكتالوج العام
  - القدرات التشغيلية
  - رسوم التوصيل
  - سياسات التوصيل
  - حالة الطاولة إن وجدت
- إرجاعها في مخرج واحد

## 8.4 repository contract

### الملف

- [backend/infrastructure/repositories/operations_repository.py](/c:/Users/stormpc/Desktop/Restaurants/backend/infrastructure/repositories/operations_repository.py)

### المطلوب

- إضافة دالة:
  - `get_public_order_journey_bootstrap(table_id: int | None = None)`

### التنفيذ

- تحميل المنتجات الأساسية مع:
  - `selectinload(Product.secondary_links).selectinload(ProductSecondaryLink.secondary_product)`
- تصفية المكملات:
  - `available = true`
  - `is_archived = false`
  - `kind = secondary`
- تحميل:
  - `app_get_operational_capabilities`
  - `app_get_delivery_fee_setting`
  - `app_get_delivery_policy_settings`
  - `app_get_table_session_snapshot` عند وجود `table_id`

## 8.5 الdomain

### الملف

- [backend/application/operations_engine/domain/orders.py](/c:/Users/stormpc/Desktop/Restaurants/backend/application/operations_engine/domain/orders.py)

### المطلوب

لا يحتاج تغييرًا جوهريًا في المرحلة الأولى من هذه الرحلة.

لكن يفضّل لاحقًا:

- استخراج validator مساعد يطابق بعض قواعد `CreateOrderInput`
- أو إضافة use case preview للتسعير قبل الإرسال

## 8.6 خيار موصى به وليس إلزاميًا

### ملف جديد

- `backend/application/operations_engine/use_cases/preview_public_order.py`

### الوظيفة

- يأخذ سلة العميل قبل الإرسال
- يرجع:
  - subtotal
  - delivery_fee
  - total
  - validation issues

هذا ليس إلزاميًا للمرحلة الأولى، لكنه خطوة ذكية إذا أردنا أن تصبح الواجهة التجارية شديدة الثبات مع القواعد.

---

## 9. التغييرات الأمامية المطلوبة ملفًا بملف

## 9.1 أنواع الـ API

### الملف

- [src/shared/api/types.ts](/c:/Users\\stormpc\\Desktop\\Restaurants\\src\\shared\\api\\types.ts)

### المطلوب

- إضافة:
  - `PublicSecondaryOption`
  - `PublicJourneyProduct`
  - `PublicJourneyCategory`
  - `PublicOrderJourneyBootstrap`
  - `PublicJourneyRules`
  - `PublicJourneyTableContext`

## 9.2 عميل الـ API

### الملف

- [src/shared/api/client.ts](/c:/Users\\stormpc\\Desktop\\Restaurants\\src\\shared\\api\\client.ts)

### المطلوب

- إضافة:
  - `publicOrderJourneyBootstrap(tableId?: number)`

مع الإبقاء على المسارات القديمة في هذه المرحلة حتى لا ينكسر أي استهلاك آخر.

## 9.3 الواجهة العامة

### الملف

- [src/modules/orders/public/PublicOrderPage.tsx](/c:/Users\\stormpc\\Desktop\\Restaurants\\src\\modules\\orders\\public\\PublicOrderPage.tsx)

### المطلوب

إعادة البناء من شاشة واحدة إلى رحلة مراحل:

- `step = 'catalog' | 'fulfillment' | 'details' | 'review' | 'tracking'`

### حالة الواجهة المقترحة

- `selectedOrderType`
- `cart`
- `selectedPrimaryProductForComposer`
- `selectedSecondaryItems`
- `step`
- `journeyBootstrap`

### السلوك الجديد

- تحميل `bootstrap` بدل خمسة استعلامات متفرقة في البداية.
- عرض الكتالوج من `bootstrap.catalog`.
- عند اختيار المنتج الأساسي:
  - فتح composer للمكملات
- بعد وجود عناصر في السلة:
  - السماح بالانتقال إلى `طريقة الاستلام`
- بعد اختيار الطريقة:
  - الانتقال إلى `البيانات`
- ثم `المراجعة`
- ثم `التتبع`

## 9.4 مكونات جديدة يفضّل إنشاؤها

### ملفات جديدة مقترحة

- `src/modules/orders/public/components/PublicJourneyShell.tsx`
- `src/modules/orders/public/components/PublicCatalogStep.tsx`
- `src/modules/orders/public/components/PublicProductComposer.tsx`
- `src/modules/orders/public/components/PublicFulfillmentStep.tsx`
- `src/modules/orders/public/components/PublicOrderDetailsStep.tsx`
- `src/modules/orders/public/components/PublicReviewStep.tsx`
- `src/modules/orders/public/components/PublicTrackingCard.tsx`

### السبب

- تقليل ضخامة الملف الرئيسي
- جعل كل مرحلة مسؤولة عن قرار واحد فقط
- تسهيل الاختبار والتعديل لاحقًا

## 9.5 قواعد التباعد والعرض

تلتزم الواجهة الجديدة بقواعد:

- [operational_ui_principles.md](/c:/Users\\stormpc\\Desktop\\Restaurants\\docs\\operational_ui_principles.md)

لكن مع توجيه إضافي خاص بالواجهة التجارية:

- لا تظهر السلة والنموذج والاختيارات كلها دفعة واحدة.
- كل مرحلة لها عنوان واضح وخطوة مفهومة.
- زر الانتقال التالي لا يظهر إلا إذا اكتملت متطلبات المرحلة الحالية.

---

## 10. بناء السلة في الواجهة الجديدة

## 10.1 النموذج الداخلي المقترح

```ts
interface PublicCartEntry {
  primary_product_id: number;
  primary_quantity: number;
  secondary_items: Array<{
    product_id: number;
    quantity: number;
  }>;
}
```

## 10.2 لماذا هذا النموذج مناسب

- يعبّر عن التجربة التجارية بشكل صحيح في الواجهة.
- لا يفرض تغييرًا على الخلفية.

## 10.3 التحويل قبل الإرسال

قبل إرسال `POST /public/orders`:

- نحول السلة إلى `items[]` مسطحة:

```ts
[
  { product_id: primaryId, quantity: primaryQty },
  { product_id: secondaryId, quantity: secondaryQty }
]
```

وبهذا:

- تبقى الخلفية بسيطة.
- تبقى الواجهة التجارية غنية.

---

## 11. قواعد السيناريو في الواجهة

## 11.1 قواعد عامة

- لا دخول إلى `fulfillment` إذا كانت السلة فارغة.
- لا دخول إلى `details` قبل اختيار طريقة الطلب.
- لا دخول إلى `review` قبل اكتمال البيانات المطلوبة.

## 11.2 قواعد التوصيل

- تعطيل بطاقة التوصيل إذا:
  - `delivery_enabled = false`
- إظهار السبب من:
  - `delivery_block_reason`
- إذا `subtotal < min_order_amount`
  - لا نمنع اختيار التوصيل فورًا
  - لكن نظهر بوضوح ما ينقص للوصول إلى الحد الأدنى
  - ونمنع الإرسال النهائي حتى يتحقق الشرط

## 11.3 قواعد الطاولة

- إذا `table_id` موجود:
  - لا تعرض بطاقات نوع الطلب أصلًا
  - ثبّت السيناريو على `dine-in`
- إذا الجلسة نشطة:
  - تعرض واجهة مختصرة:
    - حالة الجلسة
    - طلبات نشطة
    - غير المسدد
    - زر `إضافة طلب جديد`

---

## 12. خطاب المستخدم النهائي

يجب أن يكون الخطاب:

- مباشرًا
- مطمئنًا
- إرشاديًا
- غير إداري

أمثلة:

- بدل `نوع الطلب`:
  - `كيف تريد استلام طلبك؟`
- بدل `إرسال الطلب`:
  - `تأكيد الطلب`
- بدل `عنوان التوصيل مطلوب`:
  - `أضف عنوان التوصيل حتى نتمكن من الوصول إليك بدقة.`
- بدل `الحد الأدنى لطلبات التوصيل`:
  - `أضف بقيمة X د.ج ليصبح التوصيل متاحًا لهذا الطلب.`

---

## 13. خطة التنفيذ المرحلية

## المرحلة 1: العقد الخلفي

### backend

- [backend/app/schemas.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/schemas.py)
- [backend/app/routers/public.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/public.py)
- [backend/application/operations_engine/use_cases/get_public_order_journey_bootstrap.py](/c:/Users/stormpc/Desktop/Restaurants/backend/application/operations_engine/use_cases/get_public_order_journey_bootstrap.py)
- [backend/infrastructure/repositories/operations_repository.py](/c:/Users/stormpc/Desktop/Restaurants/backend/infrastructure/repositories/operations_repository.py)

### الحالة

- مكتملة في `2026-03-21`

### ما تم تنفيذه

- إضافة عقدة `GET /public/order-journey/bootstrap`
- إضافة عقود الاستجابة الخاصة بالرحلة العامة
- تجميع المنتجات الأساسية مع المكملات المرتبطة بها
- تضمين قدرات التشغيل ورسوم التوصيل والحد الأدنى
- تضمين سياق الطاولة عند وجود `table_id`

### التحقق

- `backend/scripts/typecheck_backend.py`
- `backend/scripts/lint_backend.py`
- `npm run build`
- smoke test بدون `table_id`
- smoke test مع `table_id=1`

### معيار الإغلاق

- الـ bootstrap يعيد:
  - المنتجات الأساسية
  - المكملات
  - الرسوم
  - الحد الأدنى
  - قدرات التشغيل
  - حالة الطاولة

## المرحلة 2: أنواع الـ frontend وطبقة API

### frontend

- [src/shared/api/types.ts](/c:/Users/stormpc/Desktop/Restaurants/src/shared/api/types.ts)
- [src/shared/api/client.ts](/c:/Users/stormpc/Desktop/Restaurants/src/shared/api/client.ts)
- [src/modules/orders/public/PublicOrderPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/PublicOrderPage.tsx)

### الحالة

- مكتملة في `2026-03-21`

### ما تم تنفيذه

- إضافة أنواع `bootstrap` في طبقة الـ API
- إضافة عميل `publicOrderJourneyBootstrap`
- تحويل الواجهة العامة لتقرأ رحلة الطلب من `bootstrap` بدل تجميع الاستعلامات الأساسية المتفرقة
- إعادة تنظيم التجربة إلى: هبوط > تعبئة السلة > نافذة اختيار المسار > اعتماد الطلب > نافذة نجاح واضحة
- إضافة نافذة نجاح تتضمن رقم الطلب وخيار النسخ والطباعة

### التحقق

- `npm run build`

### معيار الإغلاق

- واجهة الواجهة قادرة على قراءة bootstrap بالكامل.

## المرحلة 3: composer المنتجات

### frontend

- [src/modules/orders/public/PublicOrderPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/PublicOrderPage.tsx)
- [src/modules/orders/public/components/PublicProductsCatalog.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicProductsCatalog.tsx)
- [src/modules/orders/public/components/PublicProductComposer.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicProductComposer.tsx)

### الحالة

- مكتملة في `2026-03-29`

### ما تم تنفيذه

- تحويل بطاقات الكتالوج من تعديل مباشر داخل البطاقة إلى فتح composer مستقل لكل منتج
- فصل اختيار المنتج الأساسي عن اختيار المكملات المرتبطة به داخل نافذة واحدة واضحة
- إبقاء السلة الحالية وآلية إرسال الطلب كما هي بدون تغيير في payload الخلفي
- دعم تعديل المنتج الموجود في السلة أو إزالته من نفس composer بدل تشتيت القرار بين البطاقة والسلة
- إبقاء خطوة `fulfillment` و`review` الحالية كما هي تمهيدًا للمرحلتين 4 و5

### التحقق

- `npm run build`
- `python backend/scripts/typecheck_backend.py` مع تعطيل كتابة `pyc`
- `python backend/scripts/lint_backend.py`

### معيار الإغلاق

- يمكن إضافة منتج أساسي مع مكملاته إلى السلة.

## المرحلة 4: مرحلة طريقة الاستلام

### frontend

- [src/modules/orders/public/components/PublicCheckoutModal.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicCheckoutModal.tsx)
- [src/modules/orders/public/components/PublicDeliveryAddressSelector.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicDeliveryAddressSelector.tsx)
- [src/modules/orders/public/components/PublicLandingHero.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicLandingHero.tsx)
- [src/modules/orders/public/components/PublicCartSummaryBar.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicCartSummaryBar.tsx)

### الحالة

- مكتملة في `2026-03-29`

### ما تم تنفيذه

- تثبيت قرار طريقة الاستلام كمرحلة واضحة ومستقلة قبل إدخال البيانات
- تحويل شاشة المتابعة إلى panel نهاري مناسب للجوال بدل نافذة داكنة خانقة
- توضيح مسارات: الاستلام، التوصيل، الطاولة كبطاقات قرار مباشرة
- تحديث عرض عنوان التوصيل والتسعير إلى مظهر أخف وأوضح للمستخدم النهائي
- تثبيت أساس بصري نهاري موحد على الواجهة العامة: الهيدر، الهبوط، السلة، composer، وخطوة المتابعة

### التحقق

- `npm run build`
- `python backend/scripts/typecheck_backend.py` مع تعطيل كتابة `pyc`
- `python backend/scripts/lint_backend.py`

### معيار الإغلاق

- كل بطاقة طريقة طلب تعرض حالتها وشروطها بوضوح.

## المرحلة 5: البيانات والمراجعة

### frontend

- [src/modules/orders/public/components/PublicCheckoutModal.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicCheckoutModal.tsx)

### الحالة

- مكتملة في `2026-03-29`

### ما تم تنفيذه

- جعل الحقول المطلوبة مشروطة بالكامل بنوع الطلب بدل عرض نموذج واحد للجميع
- إضافة شريط واضح يوضح للمستخدم ما هو المطلوب فقط في هذا المسار
- تحويل الملاحظات إلى خيار إضافي غير مزاحم بدل حقل دائم
- تثبيت مراجعة نهائية مختصرة تعرض:
  - طريقة الاستلام
  - البيانات الأساسية الخاصة بهذا المسار
  - محتوى السلة
  - الإجمالي النهائي

### التحقق

- `npm run build`
- `python backend/scripts/typecheck_backend.py` مع تعطيل كتابة `pyc`
- `python backend/scripts/lint_backend.py`

### معيار الإغلاق

- العميل لا يرى إلا الحقول التي تخص السيناريو المختار.

## المرحلة 6: التتبع النهائي والتنظيف

### frontend

- [src/modules/orders/public/components/PublicTrackingCard.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/components/PublicTrackingCard.tsx)
- [src/modules/orders/public/PublicOrderPage.tsx](/c:/Users/stormpc/Desktop/Restaurants/src/modules/orders/public/PublicOrderPage.tsx)

### backend

- [backend/app/tracking.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/tracking.py)
- [backend/app/routers/public.py](/c:/Users/stormpc/Desktop/Restaurants/backend/app/routers/public.py)
- [backend/application/operations_engine/use_cases/get_public_order_tracking.py](/c:/Users/stormpc/Desktop/Restaurants/backend/application/operations_engine/use_cases/get_public_order_tracking.py)
- [backend/infrastructure/repositories/operations_repository.py](/c:/Users/stormpc/Desktop/Restaurants/backend/infrastructure/repositories/operations_repository.py)

### الحالة

- مكتملة في `2026-03-21`

### ما تم تنفيذه

- إضافة كود تتبع عام مشتق من مفتاح النظام بدل الاعتماد على رقم الطلب الخام فقط
- إضافة عقدة `GET /public/orders/track`
- تمرير `tracking_code` مع استجابة إنشاء الطلب
- إضافة لوحة تتبع عامة داخل صفحة الطلب نفسها
- ربط نافذة النجاح مباشرة بكود التتبع والنسخ والطباعة

### التحقق

- `backend/scripts/typecheck_backend.py`
- `backend/scripts/lint_backend.py`
- `npm run build`
- smoke test بكود تتبع صالح
- smoke test بكود تتبع غير صالح

### معيار الإغلاق

- التجربة كلها تعمل كسيناريو متكامل بلا تكرار بصري ولا تضارب قرار.

---

## 14. المخاطر وكيف نغلقها

## خطر 1: تضخم الاستجابة العامة

الحل:

- إرجاع المنتجات الأساسية فقط.
- إرجاع المكملات المرتبطة فقط لكل منتج.
- عدم إدخال تفاصيل تشغيلية لا يحتاجها العميل.

## خطر 2: تعقيد مفرط في السلة

الحل:

- تمثيل السلة داخليًا بمجموعات بسيطة.
- إبقاء payload النهائي مسطحًا.

## خطر 3: تضارب التحقق بين الواجهة والخلفية

الحل:

- الواجهة توجه.
- الخلفية تعتمد نهائيًا.
- يفضّل إضافة preview لاحقًا إذا ظهرت فجوة فعلية.

## خطر 4: تكرار المعنى بصريًا

الحل:

- عدم عرض:
  - نوع الطلب
  - السلة
  - النموذج
  - التتبع
  داخل نفس المساحة في الوقت نفسه.

---

## 15. القرار التنفيذي النهائي

أفضل طريق تنفيذ هو:

- توسيع `operations_engine` بعقدة `bootstrap` عامة.
- إعادة بناء `PublicOrderPage` إلى رحلة مراحل.
- تمثيل المكملات في الواجهة فقط كسياق للمنتج الأساسي.
- إبقاء `POST /public/orders` وبنية `items[]` كما هي.

هذا يحقق:

- واجهة تجارية أوضح.
- تكامل كامل مع الخلفية الحالية.
- أقل كلفة تغيير.
- أقل خطر معماري.

## 16. الترتيب الموصى به للبدء

إذا بدأ التنفيذ بعد هذه الوثيقة، فالترتيب الصحيح هو:

1. `backend bootstrap contract`
2. `frontend API/types`
3. `catalog + composer`
4. `fulfillment step`
5. `details + review`
6. `tracking + cleanup`

هذا هو المسار الأقصر للوصول إلى واجهة عامة احترافية ومغلقة السيناريو.
