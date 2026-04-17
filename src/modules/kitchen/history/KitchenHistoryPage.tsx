import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Archive, Clock3 } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import { StatusBadge } from '@/shared/ui/StatusBadge';
import { TableControls } from '@/shared/ui/TableControls';
import { TablePagination } from '@/shared/ui/TablePagination';
import { parseApiDateMs } from '@/shared/utils/date';
import { formatOrderTrackingId, orderTypeLabel, resolveOrderDeliveryAddress } from '@/shared/utils/order';
import { adaptiveRefetchInterval } from '@/shared/utils/polling';

const HISTORY_PAGE_SIZE = 18;

type KitchenSort = 'created_at' | 'total' | 'status' | 'id';

function formatDateTime(value: string): string {
  return new Date(parseApiDateMs(value)).toLocaleString('ar-DZ-u-nu-latn');
}

function summarizeItems(items: Array<{ product_name: string; quantity: number }>): string {
  return items
    .slice(0, 3)
    .map((item) => `${item.product_name} × ${item.quantity}`)
    .join('، ');
}

export function KitchenHistoryPage() {
  const role = useAuthStore((state) => state.role);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<KitchenSort>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);

  const ordersQuery = useQuery({
    queryKey: ['kitchen-orders-paged', 'history', page, HISTORY_PAGE_SIZE, search, sortBy, sortDirection],
    queryFn: () =>
      api.kitchenOrdersPaged(role ?? 'kitchen', {
        page,
        pageSize: HISTORY_PAGE_SIZE,
        scope: 'history',
        search,
        sortBy,
        sortDirection,
      }),
    enabled: role === 'kitchen',
    refetchInterval: adaptiveRefetchInterval(10_000, { minimumMs: 10_000 }),
  });

  const totalRows = ordersQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalRows / HISTORY_PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  if (ordersQuery.isLoading && !ordersQuery.data) {
    return (
      <div className="rounded-3xl border border-[var(--console-border)] bg-[var(--surface-card)] p-6 text-sm font-semibold text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تحميل سجل المطبخ...
      </div>
    );
  }

  if (ordersQuery.isError) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm font-semibold text-rose-700">
        تعذر تحميل سجل الطلبات الآن.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="admin-card space-y-4 p-4 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-black tracking-[0.18em] text-[var(--text-muted)]">KITCHEN HISTORY</p>
            <h2 className="mt-2 text-xl font-black text-[var(--text-primary-strong)]">سجل الطلبات</h2>
            <p className="mt-1 text-sm font-semibold text-[var(--text-muted)]">
              كل الطلبات التي خرجت من شاشة التنفيذ المباشر تبقى هنا للمراجعة والمتابعة اللاحقة.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-4 py-3 text-sm font-black text-[var(--text-primary)]">
            <Archive className="h-4 w-4 text-[#b86d28]" />
            <span>إجمالي السجل: {totalRows}</span>
          </div>
        </div>
      </section>

      <TableControls
        search={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        sortBy={sortBy}
        onSortByChange={(value) => {
          setSortBy(value as KitchenSort);
          setPage(1);
        }}
        sortDirection={sortDirection}
        onSortDirectionChange={(value) => {
          setSortDirection(value);
          setPage(1);
        }}
        sortOptions={[
          { value: 'created_at', label: 'الترتيب حسب وقت الإنشاء' },
          { value: 'status', label: 'الترتيب حسب الحالة' },
          { value: 'total', label: 'الترتيب حسب المبلغ' },
          { value: 'id', label: 'الترتيب حسب رقم الطلب' },
        ]}
        searchPlaceholder="ابحث برقم الطلب أو الهاتف أو الحالة..."
      />

      <section className="admin-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--console-border)] text-sm">
            <thead className="bg-[var(--surface-card-soft)]">
              <tr className="text-[var(--text-secondary)]">
                <th className="px-4 py-3 text-right font-black">الطلب</th>
                <th className="px-4 py-3 text-right font-black">النوع/الوصول</th>
                <th className="px-4 py-3 text-right font-black">العناصر</th>
                <th className="px-4 py-3 text-right font-black">الحالة</th>
                <th className="px-4 py-3 text-right font-black">آخر وقت</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--console-border)]">
              {(ordersQuery.data?.items ?? []).length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm font-semibold text-[var(--text-muted)]">
                    لا توجد طلبات محفوظة في السجل حتى الآن.
                  </td>
                </tr>
              ) : null}

              {(ordersQuery.data?.items ?? []).map((order) => (
                <tr key={order.id} className="align-top">
                  <td className="px-4 py-4">
                    <div className="space-y-1">
                      <p className="text-base font-black text-[var(--text-primary-strong)]">
                        {formatOrderTrackingId(order.id)}
                      </p>
                      <p className="text-xs font-semibold text-[var(--text-muted)]">{formatDateTime(order.created_at)}</p>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="space-y-1">
                      <p className="font-black text-[var(--text-primary)]">{orderTypeLabel(order.type)}</p>
                      <p className="text-xs font-semibold text-[var(--text-muted)]">
                        {order.table_id
                          ? `طاولة ${order.table_id}`
                          : order.phone
                            ? `هاتف ${order.phone}`
                            : order.type === 'delivery'
                              ? resolveOrderDeliveryAddress(order) !== '-'
                                ? resolveOrderDeliveryAddress(order)
                                : 'توصيل'
                              : 'استلام من المطعم'}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="space-y-2">
                      <p className="font-black text-[var(--text-primary)]">{summarizeItems(order.items)}</p>
                      {order.items.length > 3 ? (
                        <p className="text-xs font-semibold text-[var(--text-muted)]">
                          + {order.items.length - 3} عناصر إضافية
                        </p>
                      ) : null}
                      {order.notes?.trim() ? (
                        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                          {order.notes.trim()}
                        </div>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge
                      status={order.status}
                      orderType={order.type}
                      paymentStatus={order.payment_status ?? null}
                    />
                  </td>
                  <td className="px-4 py-4">
                    <div className="inline-flex items-center gap-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-2 text-xs font-bold text-[var(--text-secondary)]">
                      <Clock3 className="h-3.5 w-3.5" />
                      <span>{formatDateTime(order.sent_to_kitchen_at ?? order.created_at)}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <TablePagination page={page} totalPages={totalPages} totalRows={totalRows} onPageChange={setPage} />
      </section>
    </div>
  );
}
