# تقرير الاستعادة والاستعداد للنشر

تاريخ التقرير: 2026-04-18

## 1. أين حدث الكسر فعليًا

### 1.1 ازدواجية قاعدة البيانات

لدينا في المشروع نوعان من قواعد البيانات، ويجب الفصل بينهما ذهنيًا وتشغيليًا:

- قاعدة مركزية رئيسية:
  - `backend/local.sqlite3` محليًا
  - أو `/var/data/restaurant.db` على Render
- قواعد نسخ المطاعم:
  - `backend/tenants/*.sqlite3`

هذا الفصل مقصود معماريًا. الخطأ لم يكن وجود قاعدتين، بل حدث في موضعين:

1. كان `Alembic` يفسر `DATABASE_PATH=backend/local.sqlite3` بطريقة تؤدي أحيانًا إلى مسار مزدوج:
   - `backend/backend/local.sqlite3`
2. كانت المحادثة والتطوير يتحركان أحيانًا بلغة "Tenant isolation" دون تثبيت واضح لما هو:
   - قاعدة مركزية
   - قاعدة نسخة
   - وقاعدة ناتجة عن خطأ مسار

النتيجة:

- تعدد ملفات SQLite أعطى انطباعًا بكسر معماري.
- بينما الكسر الحقيقي كان:
  - `env.py`
  - تفسير المسار
  - وضع التشغيل المختلط بين محلي وRender

### 1.2 فوضى مسارات الدخول

النظام تحرك بين:

- دخول موحد للمدير
- دخول مرتبط بالنسخة
- دخول مطبخ/توصيل عام
- دخول مطبخ/توصيل scoped

النتيجة:

- تضخم في عدد المسارات
- ظهور إشارات داخلية لا يحتاجها المستخدم النهائي
- صعوبة في الحكم هل الرابط تجاري أم داخلي أم انتقالي

### 1.3 إدخال منطق الأدوات قبل إغلاق النسخة الأساسية

تم إدخال:

- الخطط
- الإضافات
- حالات الأدوات
- التفعيل التجاري

قبل إغلاق النسخة الأساسية بالكامل. هذا جعل بعض واجهات المطعم تعرض:

- أدوات غير متاحة
- إشارات إلى التوسع
- نصوص توحي ببنية النظام الداخلية

### 1.4 تشتت docs

مجلد `docs/` يحتوي الآن على عدد كبير من الملفات المتقاربة جدًا في الموضوع:

- تقارير صيانة
- تدقيقات UI
- تدقيقات منطقية
- خطط تفعيل
- خطط فصل قنوات
- وثائق تشغيل

المشكلة ليست في كثرة التوثيق، بل في غياب "الخط الرئيسي" الذي يحسم:

- ما الوثيقة الحاكمة
- ما الوثيقة الأرشيفية
- ما الذي ما زال صالحًا
- ما الذي أصبح من مرحلة صيانة قديمة

### 1.5 تركز المسؤوليات داخل ملفات ضخمة

الملفات الكبيرة تؤكد أن الكسر المقبل لن يكون feature bug فقط، بل صيانة معمارية:

- `src/modules/operations/orders/OrdersPage.tsx` 2981
- `backend/app/routers/manager.py` 2507
- `src/modules/system/catalog/products/ProductsPage.tsx` 2132
- `backend/app/schemas.py` 2046
- `backend/infrastructure/repositories/delivery_repository.py` 1827
- `src/modules/finance/transactions/FinancialPage.tsx` 1476
- `src/shared/api/types.ts` 1468
- `backend/app/warehouse_services.py` 1323
- `src/shared/api/client.ts` 1224
- `backend/app/orchestration/service_bridge.py` 1151
- `backend/infrastructure/repositories/operations_repository.py` 1129
- `src/modules/intelligence/reports/ReportsPage.tsx` 1087
- `src/modules/console/ConsolePage.tsx` 1079
- `src/modules/warehouse/dashboard/WarehousePage.tsx` 1060
- `backend/app/seed.py` 1045
- `backend/alembic/versions/9851b583f4d7_baseline_schema.py` 1042
- `backend/application/bot_engine/domain/telegram_delivery_bot.py` 1035
- `src/modules/operations/tables/TablesPage.tsx` 1024
- `backend/app/models.py` 1013

`package-lock.json` فوق 3000 سطر لكنه لا يدخل ضمن خطة التجزئة المعمارية.

## 2. الحكم الصحيح على ازدواجية قاعدة البيانات

### ما يجب الحفاظ عليه

- قاعدة مركزية واحدة فقط للنظام الأم
- قاعدة مستقلة لكل مطعم

### ما يجب منعه

- أي قاعدة ثالثة ناتجة عن تفسير مسار خاطئ
- أي تشغيل محلي يستخدم قاعدة تختلف عن قاعدة Alembic دون قصد
- أي نشر على Render يهاجر قاعدة ويشغل التطبيق على قاعدة أخرى

### القرار الحاكم

في كل بيئة يجب أن يكون لدينا مصدر واحد نهائي لقاعدة التشغيل:

- محليًا:
  - `DATABASE_PATH` أو `DATABASE_URL`
  - وليس الاثنين معًا بمدخلات متناقضة
- على Render:
  - يفضّل `DATABASE_PATH=/var/data/restaurant.db` في هذه المرحلة
  - أو الانتقال لاحقًا إلى Postgres عند فتح متطلبات أعلى

## 3. ما الذي حدث في Render

من سجلات Render الأخيرة:

- الترحيلات وصلت إلى النهاية بنجاح
- الخدمة بدأت
- لكن:
  - `GET /` كان يرجع `404`
  - وظهرت طلبات إلى:
    - `/api/public/products`
    - `/api/public/tables`
    - `/api/public/operational-capabilities`
    - وكلها `404`

### التفسير الصحيح

#### الجذر `/`

هذا كان خطأ فعليًا في التطبيق:

- لم يكن لدينا route على `/`
- وتم إصلاحه الآن بإرجاع استجابة جاهزة بدل `404`

#### مسارات `/api/public/*`

هذه المسارات موجودة في الكود، لذا ظهور `404` لها لا يعني غيابها بالضرورة. الأقرب منطقيًا أحد ثلاثة أسباب:

1. الواجهة الثابتة كانت تطلب المسارات العامة بدون `tenant scope`
2. تم فتح الموقع من مسار عام بدل `/t/<tenant>/...`
3. كانت هناك نسخة منشورة غير متزامنة مؤقتًا بين frontend وbackend أثناء الإقلاع

### النتيجة

مشكلة Render لم تكن "الخدمة لا تعمل"، بل:

- readiness غير محكمة
- جذر غير معرّف
- دخول عام إلى endpoints تتطلب سياق مطعم

## 4. المسار الصحيح للخروج من وضع الصيانة إلى البناء الحقيقي على Render

### المرحلة A: تثبيت تشغيل النسخة الأساسية

- لا خطط داخل لوحة المطعم
- لا أدوات ظاهرة للمدير في النسخة الأساسية
- لا نصوص مطورين أو صيانة في الواجهات
- صفحة دخول موحدة وواضحة للمدير
- روابط عامة scoped فقط

### المرحلة B: تثبيت الدخول والروابط

- `/manager/login` هو دخول المدير الموحد
- `/t/:tenantCode/manager/login` يبقى دعمًا مباشرًا للرابط الخاص عند الحاجة
- روابط الواجهة العامة:
  - `/t/:tenantCode/order`
  - `/t/:tenantCode/track`
  - `/t/:tenantCode/public/tables`

### المرحلة C: تثبيت readiness وhealth

- `GET /` يجب أن يرجع `200`
- `GET /health` يجب أن يرجع `200`
- `render.yaml` يبقى على:
  - `healthCheckPath: /health`

### المرحلة D: قفل مصدر قاعدة البيانات

- لا تشغيل محلي بقاعدة غير التي تهاجرها Alembic
- لا مسارات نسبية مزدوجة
- لا مزج بين `DATABASE_PATH` و`DATABASE_URL` بلا سبب

### المرحلة E: فحص النشر الحقيقي

1. `./build.sh`
2. `backend/.venv/Scripts/python -m alembic upgrade head`
3. `npm run build`
4. تشغيل محلي production-like
5. ثم نشر Render

## 5. قرار تنظيف docs

من الآن يجب اعتبار هذه الوثائق فقط هي الخط الرئيسي:

- `docs/release_readiness_recovery_2026_04_18.md`
- `docs/maintenance_path_progress_tracker.md`
- `docs/master_control_plane_architecture.md`
- `docs/master_control_plane_execution_plan.md`
- `docs/addon_activation_and_unlock_policy.md`
- `docs/passive_backoffice_tools_policy.md`
- `docs/system_refinement_and_distribution_readiness_plan.md`
- `docs/tenant_isolation_audit_2026_04_09.md`

وما عداها يدخل في أحد وضعين:

- مرجع تفصيلي فرعي
- أو وثيقة أرشيف

### التوصية الصارمة

في الجولة التالية يجب نقل الملفات التالية إلى `docs/archive/` أو دمجها ثم أرشفتها:

- `ui_audit_report.md`
- `ui_logic_audit_report.md`
- `stats_cards_audit_report.md`
- `control_plane_inventory_extraction.md`
- `control_plane_plan_one_transition.md`
- `markdown_status_and_system_toggle_audit.md`
- `delivery_module_toggle_and_large_files_review.md`
- `restaurant_channel_operational_vs_settings_split_review.md`
- `delivery_channel_operational_vs_settings_split_plan.md`
- `operating_model_internal.md`
- `operating_model_ui_map.md`
- `operating_model_user_guide.md`

السبب:

- هذه ملفات صيانة انتقالية
- وليست مسار تشغيل رئيسي للنشر

## 6. خطة تجزئة الملفات الكبيرة

### أولوية أولى

- `OrdersPage.tsx`
  - فصل:
    - الجدول
    - نافذة العرض
    - منطق الإجراءات
    - الطباعة
    - فلاتر الصفحة
- `backend/app/routers/manager.py`
  - فصل routers حسب المجال:
    - operations
    - settings
    - staff
    - warehouse
    - finance
- `ProductsPage.tsx`
  - فصل:
    - الجدول
    - الفورم
    - secondary products
    - consumption mapping
- `backend/app/schemas.py`
  - تقسيم schemas حسب المجال

### أولوية ثانية

- `src/shared/api/types.ts`
  - تقسيم إلى:
    - auth
    - master
    - operations
    - public
    - warehouse
    - finance
- `src/shared/api/client.ts`
  - تقسيم حسب domain clients
- `ConsolePage.tsx`
  - فصل:
    - shell
    - routing state
    - header actions
    - section rendering

### أولوية ثالثة

- `WarehousePage.tsx`
- `FinancialPage.tsx`
- `ReportsPage.tsx`
- `backend/app/models.py`
- `backend/app/seed.py`

## 7. ما تم إغلاقه في هذه الجولة

- تعطيل صفحة الأدوات من نسخة المطعم وتحويل `/console/plans` إلى `/console`
- إزالة أزرار وروابط الأدوات من `Console`
- تنظيف صفحة دخول المطعم من بقايا التطوير
- تثبيت صفحة دخول موحدة وواضحة للمدير
- تنظيف صفحة الوصول العام وإزالة الخطاب الداخلي
- إعادة تصميم اللوحة الأم إلى واجهة بيضاء أبسط وأكثر مهنية
- إضافة route صالح على `/` لتفادي `404` في الجذر أثناء النشر

## 8. ما الذي ما زال مفتوحًا قبل إعلان الجاهزية الكاملة

- تنظيف TypeScript بالكامل عبر `npm run typecheck`
- تفكيك الملفات الحرجة الكبيرة
- نقل وثائق الصيانة القديمة إلى archive
- مراجعة نصوص Arabic mojibake داخل بعض الملفات القديمة في backend
- فحص النشر النهائي على Render بعد redeploy نظيف

## 9. القرار التنفيذي التالي

لا نفتح أي أداة جديدة قبل إنجاز هذه الأربعة:

1. `typecheck` نظيف
2. docs mainline واضح
3. دخول ونشر Render مستقران
4. النسخة الأساسية لا تعرض أي أثر لأدوات غير متاحة
