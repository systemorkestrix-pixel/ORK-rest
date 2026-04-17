import { KitchenUsersPanel } from '@/modules/restaurant/settings/components/KitchenUsersPanel';

export function UsersPage() {
  return (
    <div className="admin-page space-y-4">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
        راجع الحسابات الحالية من هنا. إنشاء مستخدمي المطبخ سيتبع قناة المطبخ المستقلة بعد إغلاق هذه المرحلة.
      </div>

      <KitchenUsersPanel
        allowCreate={false}
        title="الحسابات الحالية"
        description="راجع الحسابات الحالية وعدّل صلاحياتها عند الحاجة."
      />
    </div>
  );
}
