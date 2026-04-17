import { useQuery } from '@tanstack/react-query';

import { api } from '@/shared/api/client';
import { getClientStatusClass, getClientStatusLabel } from '../data/masterReadModel';

export function MasterClientsPage() {
  const clientsQuery = useQuery({
    queryKey: ['master-clients'],
    queryFn: api.masterClients,
  });

  if (clientsQuery.isLoading) {
    return <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-sm font-bold text-slate-300">جارٍ تحميل العملاء...</div>;
  }

  if (clientsQuery.isError || !clientsQuery.data) {
    const message = clientsQuery.error instanceof Error ? clientsQuery.error.message : 'تعذر تحميل العملاء الآن.';
    return <div className="rounded-3xl border border-rose-400/30 bg-rose-500/10 p-5 text-sm font-bold text-rose-100">{message}</div>;
  }

  return (
    <div className="space-y-5">
      <section className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5">
        <div className="space-y-1">
          <p className="text-xs font-black tracking-[0.18em] text-cyan-200">العملاء</p>
          <h3 className="text-lg font-black text-white">سجل العملاء</h3>
        </div>

        {clientsQuery.data.length === 0 ? (
          <div className="mt-5 rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] p-6 text-center">
            <p className="text-base font-black text-white">لا يوجد عملاء بعد</p>
            <p className="mt-2 text-sm font-semibold text-slate-400">سيظهر العميل هنا مباشرة بعد إنشاء أول Tenant.</p>
          </div>
        ) : (
          <div className="mt-5 overflow-hidden rounded-[24px] border border-white/10">
            <table className="min-w-full divide-y divide-white/10 text-right">
              <thead className="bg-white/[0.04] text-slate-200">
                <tr>
                  <th className="px-4 py-3 text-sm font-black">العميل</th>
                  <th className="px-4 py-3 text-sm font-black">العلامة</th>
                  <th className="px-4 py-3 text-sm font-black">المدينة</th>
                  <th className="px-4 py-3 text-sm font-black">آخر أداة مفعلة</th>
                  <th className="px-4 py-3 text-sm font-black">الحالة</th>
                  <th className="px-4 py-3 text-sm font-black">الفوترة القادمة</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 bg-slate-950/35">
                {clientsQuery.data.map((client) => (
                  <tr key={client.id} className="align-top text-slate-100">
                    <td className="px-4 py-4">
                      <p className="text-sm font-black">{client.owner_name}</p>
                      <p className="mt-1 text-xs font-semibold text-slate-400" dir="ltr">
                        {client.phone}
                      </p>
                    </td>
                    <td className="px-4 py-4 text-sm font-bold">{client.brand_name}</td>
                    <td className="px-4 py-4 text-sm font-semibold text-slate-300">{client.city}</td>
                    <td className="px-4 py-4">
                      <p className="text-sm font-black">{client.current_stage_name}</p>
                      <p className="mt-1 text-xs font-semibold text-slate-400" dir="ltr">
                        {client.current_stage_id}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-black ${getClientStatusClass(client.subscription_state)}`}>
                        {getClientStatusLabel(client.subscription_state)}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm font-semibold text-slate-300">{client.next_billing_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
