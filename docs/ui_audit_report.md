# تقرير تدقيق الواجهة (UI Audit Report)

تاريخ التقرير: 2026-03-15

## 1) منهجية الفحص
- مراجعة مسارات الراوتر الفعالة للواجهات التشغيلية والإدارية.
- تدقيق تموضع العناصر الموحدة (العناوين، أزرار الإجراءات الأساسية، أدوات التصفية).
- تدقيق استخدام الأيقونات في العناوين والبطاقات والمؤشرات.
- تدقيق الجداول وخصوصًا عمود الحالة وتكرار التسميات.
- تدقيق التنظيم البنيوي للصفحات الكبيرة (تفكيك الأقسام).
- تدقيق التجاوب على الشاشات الصغيرة عبر `adaptive-table` و `data-label` و `min-w`.

## 2) نطاق الواجهات المفحوصة
- Manager Console: `/console/operations/*`, `/console/restaurant/*`, `/console/delivery/*`, `/console/warehouse/*`, `/console/finance/*`, `/console/intelligence/*`, `/console/system/*`.
- Kitchen Console: `/kitchen/console/monitor`, `/kitchen/console/prep-timeline`.
- Delivery Console: `/delivery/console`.
- Public: `/order`, `/menu`, `/public/tables`.

## 3) نتائج التدقيق — تموضع العناصر الموحدة
- `src/modules/intelligence/reports/ReportsPage.tsx`: لا يوجد عنوان صفحة واضح بعد إزالة Header العام؛ يحتاج عنوان رئيسي أعلى التبويبات.
- `src/modules/intelligence/audit/AuditLogsPage.tsx`: الأقسام الداخلية لديها عناوين فرعية فقط، بدون عنوان صفحة موحد.
- `src/modules/delivery/board/DeliveryBoardPage.tsx`: لا يستخدم قالب `admin-page` أو شريط أدوات موحد، والأزرار موزعة داخل بطاقات الطلب بشكل غير مطابق لنمط الإدارة.
- `src/modules/warehouse/dashboard/WarehousePage.tsx`: عدة جداول متتالية بدون فواصل معيارية واضحة أو شريط أدوات لكل قسم.
- `src/modules/finance/transactions/FinancialPage.tsx`: صفحة متعددة الجداول تحتاج شريط أدوات موحد يثبت مكان الأزرار الأساسية (تصدير، فلترة، بحث).

## 4) نتائج التدقيق — الأيقونات وتموضعها
- `src/modules/intelligence/reports/ReportsPage.tsx`: غياب أيقونة عنوان القسم أو شارات تعريفية للتابات.
- `src/modules/intelligence/audit/AuditLogsPage.tsx`: غياب أيقونة تعريف القسم؛ يظهر كسرد جداول فقط.
- `src/modules/warehouse/dashboard/WarehousePage.tsx`: عناوين الأقسام بدون أيقونات تمييزية؛ يفضّل استخدام أيقونات خفيفة لتسهيل المسح البصري.

## 5) نتائج التدقيق — التكرار في النصوص والجداول (خصوصًا الحالة)
- `src/modules/system/catalog/ProductsPage.tsx`: تكرار عمود "الحالة" عبر أكثر من جدول دون تمييز سياق (حالة المنتج، حالة الإضافة، حالة العنصر). يفضّل إعادة تسمية الأعمدة لتوضيح المعنى.
- `src/modules/finance/transactions/FinancialPage.tsx`: تكرار عمود "الحالة" في جداول متعددة (معاملات، إغلاقات، تسويات). يفضّل توحيد التسميات مع سياق واضح.
- `src/modules/delivery/drivers/DeliveryTeamPage.tsx`: وجود عمودين للحالة (حالة الطلب/حالة التشغيل) صحيح وظيفيًا لكنه يحتاج تمييزًا بصريًا مختلفًا لكل حالة.
- `src/modules/intelligence/dashboard/DashboardPage.tsx`: عمود "الحالة" في جدول أحدث الطلبات يحتاج التأكد من استخدام نفس معيار التلوين المركزي لضمان الاتساق.

## 6) نتائج التدقيق — التنظيم البنيوي وتبعثر الواجهات
- `src/modules/warehouse/dashboard/WarehousePage.tsx`: الصفحة تحتوي عدة جداول متتالية داخل ملف واحد؛ يوصى بتقسيمها إلى مكوّنات فرعية وتحسين الفصل البصري.
- `src/modules/system/catalog/ProductsPage.tsx`: صفحة كبيرة جدًا بثلاث جداول ونماذج متعددة؛ تحتاج تقسيم أقسام مع رؤوس ثابتة لكل قسم.
- `src/modules/finance/transactions/FinancialPage.tsx`: صفحة متعددة الأقسام والجداول؛ يفضّل فصلها إلى Sections واضحة مع عناوين ثابتة.

## 7) نتائج التدقيق — المقاسات والتجاوب
- `src/modules/delivery/board/DeliveryBoardPage.tsx`: جدول سجل العمليات لا يستخدم `data-label` للخلايا؛ التجربة على الهاتف ستكون ضعيفة.
- `src/modules/intelligence/reports/ReportsPage.tsx`: شريط التبويبات طويل على الهاتف؛ يفضّل تحويله إلى Dropdown أو استخدام لف/انزلاق أفقي مضبوط.
- `src/modules/warehouse/dashboard/WarehousePage.tsx`: كثافة أعمدة عالية؛ يفضّل إخفاء أعمدة ثانوية على الشاشات الصغيرة أو استخدام `truncate` ثابت.
- `src/modules/system/catalog/ProductsPage.tsx`: بعض الجداول واسعة جدًا؛ تحتاج أولويات أعمدة أو إخفاء أعمدة ثانوية على الهاتف.
- `src/modules/operations/orders/OrdersPage.tsx`: جدول كثيف؛ التأكد من سلوك `orders-table-modern-grid` في العرض الضيق مهم لضمان القراءة.

## 8) نقاط جيدة مثبتة
- `src/modules/operations/orders/OrdersPage.tsx`: أدوات فلترة واضحة وجداول موحدة.
- `src/modules/operations/tables/TablesPage.tsx`: فلترة وبحث ومعالجة حالة الطاولة منسقة.
- `src/modules/system/users/UsersPage.tsx`: هيكل الصفحة والجدول متسق مع نمط الإدارة.
- `src/modules/warehouse/suppliers/SuppliersPage.tsx`: دعم تصفية مع Row Tone للحالة.
- `src/modules/kitchen/monitor/KitchenMonitorPage.tsx`: يدعم فرز/بحث واضح مع جدول موحد.

## 9) توصيات تنفيذية مباشرة
- إضافة عنوان صفحة موحد لكل صفحة لا تملك عنوانًا بعد إزالة Header العام.
- توحيد شريط أدوات ثابت لكل صفحة تحتوي على أكثر من جدول.
- توحيد تسميات عمود الحالة عبر الأقسام مع سياق (حالة المنتج، حالة التسوية، حالة التشغيل).
- إلزام `data-label` في كل جدول يستخدم `table-unified` لضمان التجاوب.
- تفكيك الصفحات الثقيلة إلى مكوّنات فرعية لسهولة الصيانة.
