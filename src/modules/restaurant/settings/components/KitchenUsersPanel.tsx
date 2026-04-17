import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/modules/auth/store';
import { api } from '@/shared/api/client';
import type { PermissionCatalogItem, User, UserPermissionsProfile } from '@/shared/api/types';
import { useDataView } from '@/shared/hooks/useDataView';
import { Modal } from '@/shared/ui/Modal';
import { TableControls } from '@/shared/ui/TableControls';
import { TablePagination } from '@/shared/ui/TablePagination';
import { TABLE_STATUS_CHIP_BASE } from '@/shared/ui/tableAppearance';

interface KitchenUserFormState {
  name: string;
  username: string;
  active: boolean;
  password: string;
}

type KitchenUserModalStep = 'account' | 'security' | 'review';

interface KitchenUsersPanelProps {
  allowCreate?: boolean;
  title?: string;
  description?: string;
  introNote?: ReactNode;
}

const emptyForm: KitchenUserFormState = {
  name: '',
  username: '',
  active: true,
  password: '',
};

function resolveUserRowTone(active: boolean | null | undefined): 'success' | 'warning' | 'danger' {
  if (active === false) return 'danger';
  return 'success';
}

export function KitchenUsersPanel({
  allowCreate = true,
  title,
  description,
  introNote,
}: KitchenUsersPanelProps) {
  const currentUser = useAuthStore((state) => state.user);
  const role = useAuthStore((state) => state.role);
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('id');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<KitchenUserFormState>(emptyForm);
  const [userModalStep, setUserModalStep] = useState<KitchenUserModalStep>('account');
  const [userModalError, setUserModalError] = useState('');

  const [permissionsModalOpen, setPermissionsModalOpen] = useState(false);
  const [permissionsTargetUser, setPermissionsTargetUser] = useState<User | null>(null);
  const [permissionDraft, setPermissionDraft] = useState<Set<string>>(new Set<string>());

  const usersQuery = useQuery<User[]>({
    queryKey: ['manager-users'],
    queryFn: () => api.managerUsers(role ?? 'manager'),
    enabled: role === 'manager',
  });

  const permissionsCatalogQuery = useQuery<PermissionCatalogItem[]>({
    queryKey: ['manager-users-permissions-catalog', permissionsTargetUser?.role],
    queryFn: () => api.managerPermissionsCatalog(role ?? 'manager', permissionsTargetUser?.role),
    enabled: role === 'manager' && permissionsModalOpen && Boolean(permissionsTargetUser?.role),
  });

  const userPermissionsQuery = useQuery<UserPermissionsProfile>({
    queryKey: ['manager-user-permissions', permissionsTargetUser?.id],
    queryFn: () => api.managerUserPermissions(role ?? 'manager', permissionsTargetUser?.id ?? 0),
    enabled: role === 'manager' && permissionsModalOpen && Boolean(permissionsTargetUser?.id),
  });

  useEffect(() => {
    if (!permissionsModalOpen || !userPermissionsQuery.data) return;
    setPermissionDraft(new Set<string>(userPermissionsQuery.data.effective_permissions));
  }, [permissionsModalOpen, userPermissionsQuery.data]);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['manager-users'] });
    queryClient.invalidateQueries({ queryKey: ['manager-user-permissions'] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      api.managerCreateUser(role ?? 'manager', {
        name: form.name,
        username: form.username,
        password: form.password,
        role: 'kitchen',
        active: form.active,
      }),
    onSuccess: () => {
      setModalOpen(false);
      setEditingId(null);
      setForm(emptyForm);
      refresh();
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      api.managerUpdateUser(role ?? 'manager', editingId ?? 0, {
        name: form.name,
        role: 'kitchen',
        active: form.active,
        password: form.password || undefined,
      }),
    onSuccess: () => {
      setModalOpen(false);
      setEditingId(null);
      setForm(emptyForm);
      refresh();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: number) => api.managerDeleteUser(role ?? 'manager', userId),
    onSuccess: refresh,
  });

  const savePermissionsMutation = useMutation({
    mutationFn: () => {
      const target = permissionsTargetUser;
      const profile = userPermissionsQuery.data;
      if (!target || !profile) {
        throw new Error('لا يمكن حفظ الصلاحيات قبل تحميل البيانات.');
      }
      const defaults = new Set<string>(profile.default_permissions);
      const nextEffective = new Set<string>(permissionDraft);
      const allow = Array.from(nextEffective).filter((code) => !defaults.has(code));
      const deny = Array.from(defaults).filter((code) => !nextEffective.has(code));
      return api.managerUpdateUserPermissions(role ?? 'manager', target.id, { allow, deny });
    },
    onSuccess: (updated: UserPermissionsProfile) => {
      setPermissionDraft(new Set<string>(updated.effective_permissions));
      queryClient.invalidateQueries({ queryKey: ['manager-users'] });
      queryClient.invalidateQueries({ queryKey: ['manager-user-permissions', permissionsTargetUser?.id] });
    },
  });

  const actionError = useMemo(() => {
    if (createMutation.isError) {
      return createMutation.error instanceof Error ? createMutation.error.message : 'تعذر إضافة المستخدم.';
    }
    if (updateMutation.isError) {
      return updateMutation.error instanceof Error ? updateMutation.error.message : 'تعذر تحديث المستخدم.';
    }
    if (deleteMutation.isError) {
      return deleteMutation.error instanceof Error ? deleteMutation.error.message : 'تعذر حذف المستخدم.';
    }
    return '';
  }, [
    createMutation.error,
    createMutation.isError,
    deleteMutation.error,
    deleteMutation.isError,
    updateMutation.error,
    updateMutation.isError,
  ]);

  const kitchenUsers = useMemo(
    () => (usersQuery.data ?? []).filter((row) => row.role === 'kitchen' && row.username !== 'manager'),
    [usersQuery.data]
  );

  const view = useDataView<User>({
    rows: kitchenUsers,
    search,
    page,
    pageSize: 10,
    sortBy,
    sortDirection,
    searchAccessor: (row) => `${row.id} ${row.name} ${row.username}`,
    sortAccessors: {
      id: (row) => row.id,
      name: (row) => row.name,
      username: (row) => row.username,
    },
  });

  const permissionsCatalog = permissionsCatalogQuery.data ?? [];
  const normalizedKitchenUserName = form.name.trim();
  const normalizedKitchenUsername = form.username.trim();
  const userAccountError = !normalizedKitchenUserName
    ? 'أدخل اسم المستخدم الكامل.'
    : !editingId && !normalizedKitchenUsername
      ? 'أدخل اسم الدخول لهذا الحساب.'
      : null;
  const userSecurityError =
    editingId === null
      ? form.password.trim().length < 8
        ? 'أدخل كلمة مرور من 8 أحرف على الأقل.'
        : null
      : form.password && form.password.trim().length > 0 && form.password.trim().length < 8
        ? 'إذا أردت تغيير كلمة المرور فأدخل 8 أحرف على الأقل.'
        : null;
  const userAccountReady = userAccountError === null;
  const userSecurityReady = userSecurityError === null;
  const userReviewReady = userAccountReady && userSecurityReady;

  const permissionsActionError = useMemo(() => {
    if (permissionsCatalogQuery.isError) {
      return permissionsCatalogQuery.error instanceof Error
        ? permissionsCatalogQuery.error.message
        : 'تعذر تحميل كتالوج الصلاحيات.';
    }
    if (userPermissionsQuery.isError) {
      return userPermissionsQuery.error instanceof Error
        ? userPermissionsQuery.error.message
        : 'تعذر تحميل صلاحيات المستخدم.';
    }
    if (savePermissionsMutation.isError) {
      return savePermissionsMutation.error instanceof Error
        ? savePermissionsMutation.error.message
        : 'تعذر حفظ الصلاحيات.';
    }
    return '';
  }, [
    permissionsCatalogQuery.error,
    permissionsCatalogQuery.isError,
    savePermissionsMutation.error,
    savePermissionsMutation.isError,
    userPermissionsQuery.error,
    userPermissionsQuery.isError,
  ]);

  const openCreateModal = () => {
    setEditingId(null);
    setForm(emptyForm);
    setUserModalStep('account');
    setUserModalError('');
    setModalOpen(true);
  };

  const openEditModal = (user: User) => {
    setEditingId(user.id);
    setForm({
      name: user.name,
      username: user.username,
      active: user.active ?? true,
      password: '',
    });
    setUserModalStep('account');
    setUserModalError('');
    setModalOpen(true);
  };

  const openPermissionsModal = (user: User) => {
    setPermissionsTargetUser(user);
    setPermissionDraft(new Set<string>(user.permissions_effective ?? []));
    setPermissionsModalOpen(true);
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!userAccountReady) {
      setUserModalStep('account');
      setUserModalError(userAccountError ?? 'أكمل بيانات الحساب أولًا.');
      return;
    }
    if (!userSecurityReady) {
      setUserModalStep('security');
      setUserModalError(userSecurityError ?? 'أكمل حماية الحساب أولًا.');
      return;
    }
    if (editingId) {
      updateMutation.mutate();
      return;
    }
    createMutation.mutate();
  };

  const closeUserModal = () => {
    setModalOpen(false);
    setEditingId(null);
    setForm(emptyForm);
    setUserModalStep('account');
    setUserModalError('');
  };

  if (usersQuery.isLoading) {
    return (
      <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card)] p-5 text-sm text-[var(--text-muted)] shadow-[var(--console-shadow)]">
        جارٍ تحميل مستخدمي المطبخ...
      </div>
    );
  }

  if (usersQuery.isError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        تعذر تحميل مستخدمي المطبخ.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {(title || description) && (
        <div className="space-y-1">
          {title ? <h3 className="text-sm font-black text-[var(--text-primary-strong)]">{title}</h3> : null}
          {description ? <p className="text-xs text-[var(--text-muted)]">{description}</p> : null}
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-3">
        {allowCreate ? (
          <button type="button" onClick={openCreateModal} className="btn-primary w-full sm:w-auto">
            إضافة مستخدم مطبخ
          </button>
        ) : (
          <div />
        )}
      </div>

      {introNote ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
          {introNote}
        </div>
      ) : null}

      <TableControls
        search={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(1);
        }}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        sortDirection={sortDirection}
        onSortDirectionChange={setSortDirection}
        sortOptions={[
          { value: 'id', label: 'ترتيب: الرقم' },
          { value: 'name', label: 'ترتيب: الاسم' },
          { value: 'username', label: 'ترتيب: اسم المستخدم' },
        ]}
        searchPlaceholder="ابحث في مستخدمي المطبخ..."
      />

      {actionError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
          {actionError}
        </div>
      ) : null}

      <section className="admin-table-shell">
        <div className="adaptive-table overflow-x-auto">
          <table className="table-unified min-w-full text-sm">
            <thead className="bg-brand-50 text-gray-700">
              <tr>
                <th className="px-4 py-3 font-bold">#</th>
                <th className="px-4 py-3 font-bold">الاسم</th>
                <th className="px-4 py-3 font-bold">اسم المستخدم</th>
                <th className="px-4 py-3 font-bold">الحالة</th>
                <th className="px-4 py-3 font-bold">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {view.rows.map((user) => (
                <tr key={user.id} className={`border-t border-gray-100 table-row--${resolveUserRowTone(user.active)}`}>
                  <td data-label="#" className="px-4 py-3 font-bold">
                    #{user.id}
                  </td>
                  <td data-label="الاسم" className="px-4 py-3">
                    {user.name}
                  </td>
                  <td data-label="اسم المستخدم" className="px-4 py-3">
                    {user.username}
                  </td>
                  <td data-label="الحالة" className="px-4 py-3">
                    <span
                      className={`${TABLE_STATUS_CHIP_BASE} ${
                        user.active === false ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      {user.active === false ? 'غير نشط' : 'نشط'}
                    </span>
                  </td>
                  <td data-label="الإجراءات" className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button type="button" className="btn-secondary ui-size-sm" onClick={() => openPermissionsModal(user)}>
                        صلاحيات
                      </button>
                      <button type="button" className="btn-secondary ui-size-sm" onClick={() => openEditModal(user)}>
                        تعديل
                      </button>
                      <button
                        type="button"
                        className="btn-danger ui-size-sm"
                        disabled={deleteMutation.isPending || currentUser?.id === user.id}
                        onClick={() => {
                          if (!window.confirm(`تأكيد الحذف النهائي للمستخدم ${user.name}؟`)) return;
                          deleteMutation.mutate(user.id);
                        }}
                        title={currentUser?.id === user.id ? 'لا يمكن حذف الحساب الحالي' : 'حذف نهائي للمستخدم'}
                      >
                        حذف
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {view.rows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-gray-500">
                    لا يوجد مستخدمو مطبخ حتى الآن.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <TablePagination page={view.page} totalPages={view.totalPages} totalRows={view.totalRows} onPageChange={setPage} />
      </section>

      <Modal
        open={modalOpen}
        onClose={closeUserModal}
        title={editingId ? `تعديل مستخدم المطبخ #${editingId}` : 'إضافة مستخدم مطبخ جديد'}
        description="أكمل الحساب خطوة بخطوة ثم احفظه."
      >
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-2 md:grid-cols-3">
            {([
              { id: 'account', label: '1. الحساب', ready: true },
              { id: 'security', label: '2. الحماية', ready: userAccountReady },
              { id: 'review', label: '3. المراجعة', ready: userAccountReady && userSecurityReady },
            ] as Array<{ id: KitchenUserModalStep; label: string; ready: boolean }>).map((stepCard) => {
              const isActive = userModalStep === stepCard.id;
              const isCompleted =
                (stepCard.id === 'account' && userAccountReady && userModalStep !== 'account') ||
                (stepCard.id === 'security' && userSecurityReady && userModalStep === 'review');
              const isDisabled = !stepCard.ready && !isActive;
              return (
                <button
                  key={stepCard.id}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => !isDisabled && setUserModalStep(stepCard.id)}
                  className={`rounded-2xl border px-4 py-3 text-right transition ${
                    isActive
                      ? 'border-brand-300 bg-brand-50 text-brand-800'
                      : isCompleted
                        ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                        : 'border-[var(--console-border)] bg-[var(--surface-card-soft)] text-[var(--text-secondary)]'
                  } ${isDisabled ? 'cursor-not-allowed opacity-60' : 'hover:border-brand-200 hover:bg-white'}`}
                >
                  <p className="text-[11px] font-bold">الخطوة الحالية</p>
                  <p className="mt-1 text-sm font-black">{stepCard.label}</p>
                </button>
              );
            })}
          </div>

          {userModalStep === 'account' ? (
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1">
                <span className="form-label">الاسم الكامل</span>
                <input
                  className="form-input"
                  placeholder="مثال: أحمد محمد علي"
                  value={form.name}
                  onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                  required
                />
              </label>

              <label className="space-y-1">
                <span className="form-label">اسم المستخدم</span>
                <input
                  className="form-input"
                  placeholder="مثال: kitchen_01"
                  value={form.username}
                  disabled={editingId !== null}
                  onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
                  required
                />
              </label>

              <label className="flex items-center gap-2 rounded-xl border border-gray-300 px-3 py-2 text-sm md:col-span-2">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(event) => setForm((prev) => ({ ...prev, active: event.target.checked }))}
                />
                الحساب نشط
              </label>
            </div>
          ) : (
            <div className="rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <p className="text-xs font-bold text-[var(--text-muted)]">بيانات الحساب</p>
                  <div className="flex flex-wrap gap-2 text-xs font-semibold text-[var(--text-secondary)]">
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">{normalizedKitchenUserName || 'بدون اسم'}</span>
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">{normalizedKitchenUsername || 'بدون اسم دخول'}</span>
                    <span className="rounded-full border border-[var(--console-border)] bg-white px-3 py-1">{form.active ? 'نشط' : 'غير نشط'}</span>
                  </div>
                </div>
                <button type="button" onClick={() => setUserModalStep('account')} className="btn-secondary ui-size-sm">
                  تعديل الحساب
                </button>
              </div>
            </div>
          )}

          {userModalStep === 'security' ? (
            <div className="space-y-3 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="space-y-1">
                <h3 className="text-sm font-black text-[var(--text-primary-strong)]">حماية الحساب</h3>
                <p className="text-xs font-semibold text-[var(--text-muted)]">
                  {editingId ? 'يمكنك ترك كلمة المرور فارغة إذا كنت لا تريد تغييرها.' : 'أدخل كلمة مرور جديدة لهذا الحساب.'}
                </p>
              </div>

              <label className="space-y-1">
                <span className="form-label">كلمة المرور {editingId ? '(اختياري)' : ''}</span>
                <input
                  type="password"
                  className="form-input"
                  placeholder={editingId ? 'اتركه فارغًا للإبقاء على كلمة المرور الحالية' : '8 أحرف على الأقل'}
                  value={form.password}
                  onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                  required={editingId === null}
                />
              </label>
            </div>
          ) : userModalStep === 'review' ? (
            <div className="space-y-4 rounded-2xl border border-[var(--console-border)] bg-[var(--surface-card-soft)] p-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-[var(--console-border)] bg-white px-3 py-3">
                  <p className="text-[11px] font-bold text-[var(--text-muted)]">الحساب</p>
                  <p className="mt-1 text-sm font-black text-[var(--text-primary)]">{normalizedKitchenUserName || 'بدون اسم'}</p>
                  <p className="mt-2 text-xs font-semibold text-[var(--text-secondary)]">{normalizedKitchenUsername || 'بدون اسم دخول'}</p>
                </div>
                <div className="rounded-xl border border-[var(--console-border)] bg-white px-3 py-3">
                  <p className="text-[11px] font-bold text-[var(--text-muted)]">الحالة والحماية</p>
                  <p className="mt-1 text-sm font-black text-[var(--text-primary)]">{form.active ? 'الحساب نشط' : 'الحساب غير نشط'}</p>
                  <p className="mt-2 text-xs font-semibold text-[var(--text-secondary)]">
                    {editingId ? (form.password ? 'سيتم تحديث كلمة المرور' : 'ستبقى كلمة المرور الحالية') : 'سيتم إنشاء كلمة المرور الجديدة مع الحساب'}
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          {(userModalError || createMutation.isError || updateMutation.isError) ? (
            <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-bold text-rose-700">
              {userModalError ||
                (createMutation.error as Error)?.message ||
                (updateMutation.error as Error)?.message ||
                'تعذر حفظ مستخدم المطبخ.'}
            </p>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-200 pt-3">
            <button type="button" onClick={closeUserModal} className="btn-secondary">
              إلغاء
            </button>
            <div className="flex flex-wrap gap-2">
              {userModalStep === 'security' ? (
                <button type="button" onClick={() => setUserModalStep('account')} className="btn-secondary">
                  رجوع
                </button>
              ) : null}
              {userModalStep === 'review' ? (
                <button type="button" onClick={() => setUserModalStep('security')} className="btn-secondary">
                  رجوع
                </button>
              ) : null}
              {userModalStep === 'account' ? (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    if (!userAccountReady) {
                      setUserModalError(userAccountError ?? 'أكمل بيانات الحساب أولًا.');
                      return;
                    }
                    setUserModalError('');
                    setUserModalStep('security');
                  }}
                >
                  متابعة الحماية
                </button>
              ) : null}
              {userModalStep === 'security' ? (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    if (!userSecurityReady) {
                      setUserModalError(userSecurityError ?? 'أكمل الحماية أولًا.');
                      return;
                    }
                    setUserModalError('');
                    setUserModalStep('review');
                  }}
                >
                  مراجعة الحساب
                </button>
              ) : null}
              {userModalStep === 'review' ? (
                <button type="submit" disabled={createMutation.isPending || updateMutation.isPending || !userReviewReady} className="btn-primary">
                  {createMutation.isPending || updateMutation.isPending ? 'جارٍ الحفظ...' : 'حفظ'}
                </button>
              ) : null}
            </div>
          </div>
        </form>
      </Modal>

      <Modal
        open={permissionsModalOpen}
        onClose={() => {
          setPermissionsModalOpen(false);
          setPermissionsTargetUser(null);
          setPermissionDraft(new Set<string>());
        }}
        title={permissionsTargetUser ? `صلاحيات المستخدم ${permissionsTargetUser.name}` : 'صلاحيات المستخدم'}
        description="اختر الصلاحيات التي يحتاجها هذا الحساب."
      >
        <div className="space-y-3">
          {permissionsActionError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
              {permissionsActionError}
            </div>
          ) : null}

          {userPermissionsQuery.data ? (
            <div className="rounded-xl border border-brand-100 bg-brand-50/40 px-3 py-2 text-xs text-gray-700">
              <span className="font-bold">الصلاحيات الفعالة الآن:</span> {userPermissionsQuery.data.effective_permissions.length}
            </div>
          ) : null}

          {permissionsCatalogQuery.isLoading || userPermissionsQuery.isLoading ? (
            <div className="rounded-xl border border-brand-100 bg-white px-4 py-6 text-center text-sm text-gray-500">
              جارٍ تحميل الصلاحيات...
            </div>
          ) : (
            <div className="max-h-[55vh] overflow-y-auto rounded-xl border border-brand-100 bg-white p-3">
              {permissionsCatalog.length === 0 ? (
                <p className="text-sm text-gray-500">لا توجد صلاحيات قابلة للعرض لهذا الحساب.</p>
              ) : (
                <div className="space-y-2">
                  {permissionsCatalog.map((permission) => (
                    <label
                      key={permission.code}
                      className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 px-3 py-2 text-sm transition hover:border-brand-200 hover:bg-brand-50/30"
                    >
                      <input
                        type="checkbox"
                        checked={permissionDraft.has(permission.code)}
                        onChange={(event) => {
                          setPermissionDraft((previous) => {
                            const next = new Set(previous);
                            if (event.target.checked) next.add(permission.code);
                            else next.delete(permission.code);
                            return next;
                          });
                        }}
                        className="mt-1"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-gray-800">{permission.label}</span>
                          {permission.default_enabled ? (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-700">
                              افتراضي
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-0.5 text-xs text-gray-500">{permission.description}</p>
                        <p className="mt-0.5 text-[11px] text-gray-400">{permission.code}</p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              className="btn-primary"
              disabled={savePermissionsMutation.isPending || permissionsCatalogQuery.isLoading || userPermissionsQuery.isLoading}
              onClick={() => savePermissionsMutation.mutate()}
            >
              {savePermissionsMutation.isPending ? 'جارٍ حفظ الصلاحيات...' : 'حفظ الصلاحيات'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setPermissionsModalOpen(false);
                setPermissionsTargetUser(null);
                setPermissionDraft(new Set<string>());
              }}
            >
              إغلاق
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
