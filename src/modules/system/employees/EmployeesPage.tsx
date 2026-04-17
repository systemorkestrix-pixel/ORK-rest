import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BadgeDollarSign, BriefcaseBusiness, Pencil, Plus, Power, Search, Trash2, UserRoundCog, Users } from 'lucide-react';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type {
  RestaurantEmployee,
  RestaurantEmployeeCompensationCycle,
  RestaurantEmployeePayload,
  RestaurantEmployeeType,
} from '@/shared/api/types';
import { Modal } from '@/shared/ui/Modal';
import { PageHeaderCard } from '@/shared/ui/PageHeaderCard';
import { PageShell } from '@/shared/ui/PageShell';
import { TABLE_ACTION_BUTTON_BASE, TABLE_STATUS_CHIP_BASE } from '@/shared/ui/tableAppearance';

const EMPLOYEE_TYPE_OPTIONS: Array<{ value: RestaurantEmployeeType; label: string }> = [
  { value: 'cook', label: 'طباخ' },
  { value: 'kitchen_assistant', label: 'مساعد مطبخ' },
  { value: 'delivery_staff', label: 'موظف توزيع' },
  { value: 'courier', label: 'مندوب' },
  { value: 'warehouse_keeper', label: 'أمين مخزن' },
  { value: 'cashier', label: 'كاشير' },
  { value: 'service_staff', label: 'خدمة وصالة' },
  { value: 'admin_staff', label: 'إداري' },
];

const COMPENSATION_OPTIONS: Array<{ value: RestaurantEmployeeCompensationCycle; label: string }> = [
  { value: 'monthly', label: 'شهري' },
  { value: 'weekly', label: 'أسبوعي' },
  { value: 'daily', label: 'يومي' },
  { value: 'hourly', label: 'بالساعة' },
];

const emptyEmployeeForm: RestaurantEmployeePayload = {
  name: '',
  employee_type: 'cook',
  phone: '',
  compensation_cycle: 'monthly',
  compensation_amount: 0,
  work_schedule: '',
  notes: '',
  active: true,
};

function employeeTypeLabel(value: RestaurantEmployeeType): string {
  return EMPLOYEE_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function compensationCycleLabel(value: RestaurantEmployeeCompensationCycle): string {
  return COMPENSATION_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function formatCompensation(employee: RestaurantEmployee): string {
  return `${employee.compensation_amount.toFixed(2)} دج / ${compensationCycleLabel(employee.compensation_cycle)}`;
}

export function EmployeesPage() {
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | RestaurantEmployeeType>('all');
  const [activeOnly, setActiveOnly] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<RestaurantEmployee | null>(null);
  const [employeeForm, setEmployeeForm] = useState<RestaurantEmployeePayload>(emptyEmployeeForm);
  const [submitError, setSubmitError] = useState('');

  const tenantContextQuery = useQuery({
    queryKey: ['manager-tenant-context'],
    queryFn: () => api.managerTenantContext(role ?? 'manager'),
    enabled: role === 'manager',
    staleTime: 30_000,
  });
  const tenantScopeKey = tenantContextQuery.data?.tenant_id ?? 'tenant-unknown';

  const employeesQuery = useQuery({
    queryKey: ['manager-restaurant-employees', tenantScopeKey, search, typeFilter, activeOnly],
    queryFn: () =>
      api.managerRestaurantEmployees(role ?? 'manager', {
        search,
        employeeType: typeFilter === 'all' ? undefined : typeFilter,
        activeOnly,
      }),
    enabled: role === 'manager' && tenantContextQuery.isSuccess,
  });

  const employees = employeesQuery.data ?? [];

  const activeEmployees = useMemo(() => employees.filter((employee) => employee.active), [employees]);
  const totalCompensation = useMemo(
    () =>
      activeEmployees
        .filter((employee) => employee.compensation_cycle === 'monthly')
        .reduce((sum, employee) => sum + employee.compensation_amount, 0),
    [activeEmployees]
  );

  const refreshEmployees = () => {
    queryClient.invalidateQueries({ queryKey: ['manager-restaurant-employees', tenantScopeKey] });
  };

  const createEmployeeMutation = useMutation({
    mutationFn: (payload: RestaurantEmployeePayload) => api.managerCreateRestaurantEmployee(role ?? 'manager', payload),
    onSuccess: () => {
      refreshEmployees();
      closeEmployeeModal();
    },
  });

  const updateEmployeeMutation = useMutation({
    mutationFn: ({ employeeId, payload }: { employeeId: number; payload: RestaurantEmployeePayload }) =>
      api.managerUpdateRestaurantEmployee(role ?? 'manager', employeeId, payload),
    onSuccess: () => {
      refreshEmployees();
      closeEmployeeModal();
    },
  });

  const deleteEmployeeMutation = useMutation({
    mutationFn: (employeeId: number) => api.managerDeleteRestaurantEmployee(role ?? 'manager', employeeId),
    onSuccess: refreshEmployees,
  });

  const openCreateModal = () => {
    setEditingEmployee(null);
    setEmployeeForm(emptyEmployeeForm);
    setSubmitError('');
    setIsModalOpen(true);
  };

  const openEditModal = (employee: RestaurantEmployee) => {
    setEditingEmployee(employee);
    setEmployeeForm({
      name: employee.name,
      employee_type: employee.employee_type,
      phone: employee.phone ?? '',
      compensation_cycle: employee.compensation_cycle,
      compensation_amount: employee.compensation_amount,
      work_schedule: employee.work_schedule ?? '',
      notes: employee.notes ?? '',
      active: employee.active,
    });
    setSubmitError('');
    setIsModalOpen(true);
  };

  const closeEmployeeModal = () => {
    setIsModalOpen(false);
    setEditingEmployee(null);
    setEmployeeForm(emptyEmployeeForm);
    setSubmitError('');
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError('');

    try {
      const payload: RestaurantEmployeePayload = {
        ...employeeForm,
        name: employeeForm.name.trim(),
        phone: employeeForm.phone?.trim() || null,
        work_schedule: employeeForm.work_schedule?.trim() || null,
        notes: employeeForm.notes?.trim() || null,
      };

      if (editingEmployee) {
        await updateEmployeeMutation.mutateAsync({ employeeId: editingEmployee.id, payload });
        return;
      }
      await createEmployeeMutation.mutateAsync(payload);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'تعذر حفظ الموظف الآن.');
    }
  };

  const handleToggleActive = async (employee: RestaurantEmployee) => {
    try {
      await updateEmployeeMutation.mutateAsync({
        employeeId: employee.id,
        payload: {
          name: employee.name,
          employee_type: employee.employee_type,
          phone: employee.phone,
          compensation_cycle: employee.compensation_cycle,
          compensation_amount: employee.compensation_amount,
          work_schedule: employee.work_schedule,
          notes: employee.notes,
          active: !employee.active,
        },
      });
    } catch {
      // Errors are surfaced by react-query state through the existing table context.
    }
  };

  const handleDelete = async (employee: RestaurantEmployee) => {
    const confirmed = window.confirm(`سيتم حذف ${employee.name} من سجل الموظفين. هل تريد المتابعة؟`);
    if (!confirmed) {
      return;
    }

    try {
      await deleteEmployeeMutation.mutateAsync(employee.id);
    } catch {
      // keep current page state
    }
  };

  const isSubmitting = createEmployeeMutation.isPending || updateEmployeeMutation.isPending;

  return (
    <PageShell
      className="admin-page"
      header={
        <PageHeaderCard
          title="إدارة الموظفين"
          description="سجل مباشر لموظفي المطعم ورواتبهم وهواتفهم ووقت العمل."
          icon={<Users className="h-5 w-5" />}
          actions={
            <button type="button" onClick={openCreateModal} className="btn-primary ui-size-sm">
              <Plus className="h-4 w-4" />
              <span>إضافة موظف</span>
            </button>
          }
          metrics={[
            { label: 'إجمالي الموظفين', value: employees.length, tone: 'info' },
            { label: 'الموظفون النشطون', value: activeEmployees.length, tone: 'success' },
            { label: 'أجور شهرية مباشرة', value: `${totalCompensation.toFixed(0)} دج`, tone: 'default' },
          ]}
        />
      }
      workspaceClassName="space-y-4"
    >
      <section className="grid gap-3 md:grid-cols-3">
        <article className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[#c7935f]">
            <BriefcaseBusiness className="h-5 w-5" />
          </span>
          <h3 className="mt-3 text-sm font-black text-[var(--text-primary)]">أنواع العمل</h3>
          <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">طباخ، توزيع، مندوب، أمين مخزن، وكامل فريق التشغيل اليومي.</p>
        </article>

        <article className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[#c7935f]">
            <BadgeDollarSign className="h-5 w-5" />
          </span>
          <h3 className="mt-3 text-sm font-black text-[var(--text-primary)]">الأجور</h3>
          <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">الأجر يحفظ حسب الدورة التي تختارها: شهري، أسبوعي، يومي أو بالساعة.</p>
        </article>

        <article className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-4">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[#c7935f]">
            <UserRoundCog className="h-5 w-5" />
          </span>
          <h3 className="mt-3 text-sm font-black text-[var(--text-primary)]">وقت العمل</h3>
          <p className="mt-1 text-xs font-semibold text-[var(--text-muted)]">دوّن التقسيم العملي كما يديره المطعم: صباح، مساء، أو نظام مفصل.</p>
        </article>
      </section>

      <section className="admin-card space-y-4 p-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_160px_auto]">
          <label className="space-y-1">
            <span className="form-label">بحث</span>
            <div className="relative">
              <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    setSearch(searchDraft.trim());
                  }
                }}
                className="form-input pr-10"
                placeholder="ابحث بالاسم أو الهاتف أو وقت العمل"
              />
            </div>
          </label>

          <label className="space-y-1">
            <span className="form-label">النوع</span>
            <select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value as 'all' | RestaurantEmployeeType)}
              className="form-select"
            >
              <option value="all">كل الموظفين</option>
              {EMPLOYEE_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1">
            <span className="form-label">الحالة</span>
            <button
              type="button"
              onClick={() => setActiveOnly((current) => !current)}
              className={`form-input flex items-center justify-between ${activeOnly ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : ''}`}
            >
              <span>{activeOnly ? 'النشطون فقط' : 'كل الحالات'}</span>
              <Power className="h-4 w-4" />
            </button>
          </label>

          <div className="flex items-end">
            <button type="button" onClick={() => setSearch(searchDraft.trim())} className="btn-primary ui-size-sm w-full">
              <Search className="h-4 w-4" />
              <span>بحث</span>
            </button>
          </div>
        </div>
      </section>

      <section className="admin-table-shell">
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-brand-50 text-gray-700">
              <tr>
                <th className="px-4 py-3 font-bold">#</th>
                <th className="px-4 py-3 font-bold">الموظف</th>
                <th className="px-4 py-3 font-bold">النوع</th>
                <th className="px-4 py-3 font-bold">الهاتف</th>
                <th className="px-4 py-3 font-bold">الأجر</th>
                <th className="px-4 py-3 font-bold">وقت العمل</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {employeesQuery.isLoading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    جارٍ تحميل سجل الموظفين...
                  </td>
                </tr>
              ) : null}

              {employeesQuery.isError ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-rose-700">
                    {employeesQuery.error instanceof Error ? employeesQuery.error.message : 'تعذر تحميل سجل الموظفين الآن.'}
                  </td>
                </tr>
              ) : null}

              {!employeesQuery.isLoading && !employeesQuery.isError && employees.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    لا يوجد موظفون ضمن هذا الفلتر الآن.
                  </td>
                </tr>
              ) : null}

              {!employeesQuery.isLoading &&
                !employeesQuery.isError &&
                employees.map((employee) => (
                  <tr key={employee.id} className="border-t border-gray-100">
                    <td data-label="#" className="px-4 py-3 font-bold">
                      #{employee.id}
                    </td>
                    <td data-label="الموظف" className="px-4 py-3">
                      <div className="space-y-1">
                        <div className="font-black text-[var(--text-primary)]">{employee.name}</div>
                        {employee.notes ? <div className="text-xs font-semibold text-[var(--text-muted)]">{employee.notes}</div> : null}
                      </div>
                    </td>
                    <td data-label="النوع" className="px-4 py-3">
                      <span className={`${TABLE_STATUS_CHIP_BASE} bg-sky-100 text-sky-800`}>{employeeTypeLabel(employee.employee_type)}</span>
                    </td>
                    <td data-label="الهاتف" className="px-4 py-3 font-semibold" dir="ltr">
                      {employee.phone || '-'}
                    </td>
                    <td data-label="الأجر" className="px-4 py-3 font-black text-[var(--text-primary)]">
                      {formatCompensation(employee)}
                    </td>
                    <td data-label="وقت العمل" className="px-4 py-3 text-[var(--text-secondary)]">
                      {employee.work_schedule || '-'}
                    </td>
                    <td data-label="الحالة" className="px-4 py-3">
                      <span
                        className={`${TABLE_STATUS_CHIP_BASE} ${
                          employee.active ? 'bg-emerald-100 text-emerald-800' : 'bg-stone-200 text-stone-800'
                        }`}
                      >
                        {employee.active ? 'نشط' : 'متوقف'}
                      </span>
                    </td>
                    <td data-label="الإجراءات" className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => openEditModal(employee)} className={`${TABLE_ACTION_BUTTON_BASE} gap-1.5`}>
                          <Pencil className="h-3.5 w-3.5" />
                          <span>تعديل</span>
                        </button>
                        <button type="button" onClick={() => void handleToggleActive(employee)} className={`${TABLE_ACTION_BUTTON_BASE} gap-1.5`}>
                          <Power className="h-3.5 w-3.5" />
                          <span>{employee.active ? 'إيقاف' : 'تفعيل'}</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(employee)}
                          className={`${TABLE_ACTION_BUTTON_BASE} gap-1.5 border-rose-300 bg-rose-100/80 text-rose-900 hover:bg-rose-100`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          <span>حذف</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      <Modal
        open={isModalOpen}
        onClose={closeEmployeeModal}
        title={editingEmployee ? 'تعديل الموظف' : 'إضافة موظف'}
        footer={
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={closeEmployeeModal} className="btn-secondary ui-size-sm">
              إلغاء
            </button>
            <button type="submit" form="restaurant-employee-form" disabled={isSubmitting} className="btn-primary ui-size-sm">
              {editingEmployee ? 'حفظ التعديل' : 'إضافة الموظف'}
            </button>
          </div>
        }
      >
        <form id="restaurant-employee-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="form-label">اسم الموظف</span>
              <input
                className="form-input"
                value={employeeForm.name}
                onChange={(event) => setEmployeeForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="الاسم الكامل"
                required
              />
            </label>

            <label className="space-y-1">
              <span className="form-label">نوع الموظف</span>
              <select
                className="form-select"
                value={employeeForm.employee_type}
                onChange={(event) =>
                  setEmployeeForm((current) => ({
                    ...current,
                    employee_type: event.target.value as RestaurantEmployeeType,
                  }))
                }
              >
                {EMPLOYEE_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1">
              <span className="form-label">الهاتف</span>
              <input
                className="form-input"
                value={employeeForm.phone ?? ''}
                onChange={(event) => setEmployeeForm((current) => ({ ...current, phone: event.target.value }))}
                placeholder="رقم الهاتف"
                dir="ltr"
              />
            </label>

            <label className="space-y-1">
              <span className="form-label">وقت العمل</span>
              <input
                className="form-input"
                value={employeeForm.work_schedule ?? ''}
                onChange={(event) => setEmployeeForm((current) => ({ ...current, work_schedule: event.target.value }))}
                placeholder="مثال: صباح 08:00 - 16:00"
              />
            </label>

            <label className="space-y-1">
              <span className="form-label">دورة الأجر</span>
              <select
                className="form-select"
                value={employeeForm.compensation_cycle}
                onChange={(event) =>
                  setEmployeeForm((current) => ({
                    ...current,
                    compensation_cycle: event.target.value as RestaurantEmployeeCompensationCycle,
                  }))
                }
              >
                {COMPENSATION_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1">
              <span className="form-label">قيمة الأجر</span>
              <input
                type="number"
                min={0}
                step="0.01"
                className="form-input"
                value={employeeForm.compensation_amount}
                onChange={(event) =>
                  setEmployeeForm((current) => ({
                    ...current,
                    compensation_amount: Number(event.target.value),
                  }))
                }
              />
            </label>
          </div>

          <label className="space-y-1">
            <span className="form-label">ملاحظات</span>
            <textarea
              rows={4}
              className="form-input min-h-28"
              value={employeeForm.notes ?? ''}
              onChange={(event) => setEmployeeForm((current) => ({ ...current, notes: event.target.value }))}
              placeholder="أي ملاحظات تنظيمية تخص هذا الموظف"
            />
          </label>

          <label className="inline-flex items-center gap-2 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] px-3 py-3 text-sm font-black text-[var(--text-primary)]">
            <input
              type="checkbox"
              checked={employeeForm.active}
              onChange={(event) => setEmployeeForm((current) => ({ ...current, active: event.target.checked }))}
            />
            <span>الموظف نشط</span>
          </label>

          {submitError ? (
            <div className="rounded-2xl border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-bold text-rose-800">{submitError}</div>
          ) : null}
        </form>
      </Modal>
    </PageShell>
  );
}
