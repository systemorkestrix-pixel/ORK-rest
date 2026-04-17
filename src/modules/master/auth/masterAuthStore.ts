import { create } from 'zustand';

import { api } from '@/shared/api/client';
import type { MasterIdentity } from '@/shared/api/types';

type MasterAuthStatus = 'idle' | 'checking' | 'authenticated' | 'anonymous';

interface MasterAuthState {
  identity: MasterIdentity | null;
  loginError: string | null;
  status: MasterAuthStatus;
  hydrateSession: () => Promise<void>;
  login: (payload: { username: string; password: string }) => Promise<boolean>;
  logout: () => Promise<void>;
  clearLoginError: () => void;
}

export const useMasterAuthStore = create<MasterAuthState>((set, get) => ({
  identity: null,
  loginError: null,
  status: 'idle',
  hydrateSession: async () => {
    const currentStatus = get().status;
    if (currentStatus === 'checking') {
      return;
    }

    set({ status: 'checking' });
    try {
      const session = await api.masterSession();
      set({ identity: session.identity, loginError: null, status: 'authenticated' });
    } catch {
      set({ identity: null, status: 'anonymous' });
    }
  },
  login: async ({ username, password }) => {
    set({ status: 'checking', loginError: null });
    try {
      const session = await api.masterLogin({ username, password });
      set({ identity: session.identity, loginError: null, status: 'authenticated' });
      return true;
    } catch (error) {
      set({
        identity: null,
        status: 'anonymous',
        loginError: error instanceof Error ? error.message : 'تعذر تسجيل الدخول إلى اللوحة الأم.',
      });
      return false;
    }
  },
  logout: async () => {
    try {
      await api.masterLogout();
    } catch {
      // Ignore logout failure and clear local session state anyway.
    }
    set({ identity: null, loginError: null, status: 'anonymous' });
  },
  clearLoginError: () => set({ loginError: null }),
}));
