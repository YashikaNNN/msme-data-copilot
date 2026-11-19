"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, Business, getToken, setToken } from "@/lib/api";

type AuthContextValue = {
  business: Business | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    business_name: string;
    owner_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setBusiness(null);
      setLoading(false);
      return;
    }
    try {
      const data = await apiGet<{ business: Business }>("/auth/me");
      setBusiness(data.business);
    } catch {
      setToken(null);
      setBusiness(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiPost<{ token: string; business: Business }>("/auth/login", { email, password });
    setToken(data.token);
    setBusiness(data.business);
  }, []);

  const register = useCallback(
    async (payload: { business_name: string; owner_name: string; email: string; password: string }) => {
      const data = await apiPost<{ token: string; business: Business }>("/auth/register", payload);
      setToken(data.token);
      setBusiness(data.business);
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await apiPost("/auth/logout");
    } catch {
      // ignore network errors on logout
    }
    setToken(null);
    setBusiness(null);
  }, []);

  const value = useMemo(
    () => ({ business, loading, login, register, logout, refresh }),
    [business, loading, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
