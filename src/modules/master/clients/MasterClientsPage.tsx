import { useQuery } from '@tanstack/react-query';

import { api } from '@/shared/api/client';
import { getClientStatusClass, getClientStatusLabel } from '../data/masterReadModel';

export function MasterClientsPage() {
  const clientsQuery = useQuery({
    queryKey: ['master-clients'],
    queryFn: api.masterClients,
  });

  if (clientsQuery.isLoading) {
    return <div className="rounded-3xl border border-[#e6edf5] bg-[#f8fbff] p-5 text-sm font-bold text-[#607080]">جارٍ تحميل العملاء...</div>;
  }

  if (clientsQuery.isError || !clientsQuery.data) {
    const message = clientsQuery.error instanceof Error ? clientsQuery.error.message : 'تعذر تحميل العملاء الآن.';
    return <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-sm font-bold text-rose-700">{message}</div>;
  }

  return (
    <div className="space-y-5">
      <section className="rounded-[28px] border border-[#e6edf5] bg-white p-5 shadow-sm">
        <div className="space-y-1">
          <p className="text-xs font-black tracking-[0.18em] text-[#6a7a8c]">العملاء</p>
          <h3 className="text-lg font-black text-[#1b2430]">سجل العملاء</h3>
        </div>

        {clientsQuery.data.length === 0 ? (
          <div className="mt-5 rounded-[24px] border border-dashed border-[#d9e3ef] bg-[#f8fbff] p-6 text-center">
            <p className="text-base font-black text-[#1b2430]">لا يوجد عملاء بعد</p>
            <p className="mt-2 text-sm font-semibold text-[#607080]">سيظهر أول عميل هنا مباشرة بعد إنشاء النسخة الأولى.</p>
          </div>
        ) : (
          <div className="mt-5 overflow-hidden rounded-[24px] border border-[#e6edf5]">
            <div className="overflow-x-auto">
              <table className="min-w-full text-right">
                <thead className="bg-[#f8fbff] text-[#405060]">
                  <tr>
                    <th className="px-4 py-3 text-sm font-black">العميل</th>
                    <th className="px-4 py-3 text-sm font-black">العلامة</th>
                    <th className="px-4 py-3 text-sm font-black">المدينة</th>
                    <th className="px-4 py-3 text-sm font-black">آخر أداة مفعلة</th>
                    <th className="px-4 py-3 text-sm font-black">الحالة</th>
                    <th className="px-4 py-3 text-sm font-black">الفاتورة القادمة</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#edf2f7] bg-white">
                  {clientsQuery.data.map((client) => (
                    <tr key={client.id} className="align-top text-[#1b2430]">
                      <td className="px-4 py-4">
                        <p className="text-sm font-black">{client.owner_name}</p>
                        <p className="mt-1 text-xs font-semibold text-[#607080]" dir="ltr">
                          {client.phone}
                        </p>
                      </td>
                      <td className="px-4 py-4 text-sm font-bold">{client.brand_name}</td>
                      <td className="px-4 py-4 text-sm font-semibold text-[#607080]">{client.city}</td>
                      <td className="px-4 py-4">
                        <p className="text-sm font-black">{client.current_stage_name}</p>
                        <p className="mt-1 text-xs font-semibold text-[#607080]" dir="ltr">
                          {client.current_stage_id}
                        </p>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-black ${getClientStatusClass(client.subscription_state)}`}>
                          {getClientStatusLabel(client.subscription_state)}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm font-semibold text-[#607080]">{client.next_billing_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
