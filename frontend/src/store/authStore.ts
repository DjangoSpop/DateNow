/**
 * Authentication state management
 */
import { create } from 'zustand';
import { authApi, tokenStorage } from '../lib/api';

interface AuthState {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, firstName: string, lastName?: string) => Promise<void>;
  logout: () => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,

  initialize: async () => {
    if (!tokenStorage.getAccessToken()) return;
    // Validate the stored session with the server instead of trusting token presence.
    try {
      await authApi.me();
      set({ isAuthenticated: true });
    } catch {
      tokenStorage.clear();
      set({ isAuthenticated: false });
    }
  },

  login: async (email: string, password: string) => {
    const response = await authApi.login({ email, password });
    tokenStorage.set(response.data);
    set({ isAuthenticated: true });
  },

  register: async (email: string, password: string, firstName: string, lastName?: string) => {
    const response = await authApi.register({
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    tokenStorage.set(response.data);
    set({ isAuthenticated: true });
  },

  logout: () => {
    authApi.logout();
    set({ isAuthenticated: false });
  },
}));
