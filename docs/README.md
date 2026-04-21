# دليل docs

هذا المجلد لم يعد مسارًا مفتوحًا لتجميع ملاحظات الصيانة بشكل عشوائي. من الآن:

## الوثائق الحاكمة

- `release_readiness_recovery_2026_04_18.md`
- `launch_control_and_render_checklist_2026_04_18.md`
- `maintenance_path_progress_tracker.md`
- `master_control_plane_architecture.md`
- `master_control_plane_execution_plan.md`
- `addon_activation_and_unlock_policy.md`
- `passive_backoffice_tools_policy.md`
- `system_refinement_and_distribution_readiness_plan.md`
- `tenant_isolation_audit_2026_04_09.md`

## كيف نضيف وثيقة جديدة

- إذا كانت الوثيقة تحكم قرارًا معماريًا مستمرًا، تبقى في جذر `docs/`.
- إذا كانت الوثيقة تدقيقًا مرحليًا أو تقرير صيانة أو مرجعًا تم تجاوزه، تنقل إلى `docs/archive/`.

## قاعدة الصيانة

لا تُنشأ وثيقة جديدة إذا كان القرار يمكن إضافته إلى إحدى الوثائق الحاكمة أعلاه.
