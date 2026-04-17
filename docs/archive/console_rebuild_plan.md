# الخطة المصححة: فصل تطبيقات التشغيل داخل النظام

هذه الخطة تعيد ضبط المعمارية بعد اكتشاف خلط بين طبقات مختلفة. الهدف هو الفصل الصارم بين لوحات التشغيل (Applications) وأقسام الإدارة (Sections) مع الحفاظ على التصميم البصري الحالي للـ Console.

## 1) المبادئ الثابتة
- عدم تغيير التصميم البصري الحالي للـ Manager Console.
- بقاء التنقل SPA بدون إعادة تحميل.
- كل وظيفة لها صفحة مالكة واحدة.
- أي شيء إداري (إعدادات/سياسات/إدارة مستخدمين) يبقى داخل Manager Console.
- أي شيء تشغيلي (تنفيذ/تشغيل/استلام/تسليم) يكون داخل لوحات التشغيل الخاصة بها.

## 2) الطبقات الصحيحة للنظام
- Channel (قناة تشغيل): تصنيف داخل Manager Console.
- Console Section (قسم): صفحة أو مجموعة صفحات إدارية داخل Manager Console.
- User Application (تطبيق): لوحة تشغيل مستقلة (Kitchen / Delivery).

## 3) التطبيقات الأربعة داخل المشروع
- Manager Console: المسار الأساسي `/console/*`، الهدف الإدارة المركزية فقط، الأقسام الإدارية Operations, Restaurant, Delivery, Warehouse, Finance, Intelligence, System.
- Kitchen Console: المسارات `/kitchen/login`, `/kitchen/console`، الهدف تشغيل المطبخ فقط، الصفحات Kitchen Monitor, Prep Timeline.
- Delivery Console: المسارات `/delivery/login`, `/delivery/console`، الهدف تشغيل التوصيل فقط، الصفحات التشغيلية Available Orders, My Deliveries, Delivery Status, Settlement.
- Public Interface: المسارات `/order`, `/menu`, `/public/tables`، الهدف واجهات الزائر/العميل.

## 4) الهيكل المقترح للمشروع

```
src
  app
    router
    layout
    providers

  apps
    manager-console
    kitchen-console
    delivery-console
    public

  modules
    operations
    restaurant
    delivery-admin
    warehouse
    finance
    intelligence
    system

  entities
  tools
  shared
```

## 5) Manager Console (الأقسام الإدارية)

Operations
- `/console/operations/overview`
- `/console/operations/orders`
- `/console/operations/tables`
- `/console/operations/alerts`

Restaurant
- `/console/restaurant/menu`

Delivery (Admin)
- `/console/delivery/drivers`
- `/console/delivery/history`
- لاحقًا: fees, zones, policies

Warehouse
- `/console/warehouse/stock-ledger`
- `/console/warehouse/vouchers`
- `/console/warehouse/suppliers`

Finance
- `/console/finance/dashboard`
- `/console/finance/transactions`
- `/console/finance/expenses`
- `/console/finance/cash-shift`

Intelligence
- `/console/intelligence/operational-heart`
- `/console/intelligence/reports`

System
- `/console/system/users`
- `/console/system/roles`
- `/console/system/settings`
- `/console/system/audit-log`

## 6) Kitchen Console (تشغيل)
- `/kitchen/console/monitor`
- `/kitchen/console/prep-timeline`

## 7) Delivery Console (تشغيل)
- `/delivery/console`
- محتوى الشاشة التشغيلية: Available Orders, My Deliveries, Delivery History, Settlement

## 8) القاعدة التي تمنع الخلط
- أي شيء يحتوي configuration أو settings أو management يبقى داخل Manager Console.
- أي شيء يحتوي execute أو process أو work يذهب إلى اللوحات التشغيلية (Kitchen/Delivery).

## 9) Router الصحيح
- `/console/*` → Manager Console
- `/kitchen/*` → Kitchen Console
- `/delivery/*` → Delivery Console
- `/public/*` + `/order` + `/menu` → Public

## 10) العلاقة مع الخلفية

Application
↓
Section/Page
↓
Entity
↓
API
↓
Backend Engine

مثال:
Operations Orders (Manager)
↓
entities/order
↓
/api/manager/orders
↓
operations_engine

مثال:
Kitchen Monitor
↓
entities/order
↓
/api/kitchen/orders
↓
kitchen_engine

مثال:
Delivery Console
↓
entities/order
↓
/api/delivery/orders
↓
delivery_engine

## 11) ما لن يتغير
- التصميم الحالي للـ Manager Console.
- شريط القنوات الأفقي.
- سرعة التنقل وتجربة المستخدم.

## 12) ما سيتغير
- فصل التطبيقات التشغيلية عن لوحة الإدارة.
- تنظيم الأقسام الإدارية داخل Manager Console.
- إصلاح المسارات والروابط الداخلية.
- تحديث وثائق البناء والتنفيذ على القاعدة الصحيحة.
