import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi } from '../services/api';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  checkAuth: () => Promise<void>;
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      isLoading: true,

      checkAuth: async () => {
        set({ isLoading: true });
        try {
          const isValid = await authApi.verify();
          set({ isAuthenticated: isValid, isLoading: false });
        } catch {
          set({ isAuthenticated: false, isLoading: false });
        }
      },

      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          const result = await authApi.login(username, password);
          if (result.success) {
            set({ isAuthenticated: true, isLoading: false });
            return { success: true };
          }
          set({ isLoading: false });
          return { success: false, error: result.message };
        } catch (error) {
          set({ isLoading: false });
          const message = error instanceof Error ? error.message : 'Đăng nhập thất bại';
          return { success: false, error: message };
        }
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch {
          // Ignore logout errors
        }
        set({ isAuthenticated: false });
      },
    }),
    {
      name: 'dashboard-auth',
      partialize: (state) => ({ isAuthenticated: state.isAuthenticated }),
    }
  )
);
