"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, setToken, getToken } from "./api";
import type { User } from "./types";

type AuthCtx = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string, goals: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (getToken()) {
        try { setUser(await api.me()); }
        catch { setToken(null); }
      }
      setLoading(false);
    })();
  }, []);

  async function login(email: string, password: string) {
    const { token, user } = await api.login({ email, password });
    setToken(token);
    setUser(user);
  }
  async function register(email: string, password: string, name: string, goals: string) {
    const { token, user } = await api.register({ email, password, name, goals });
    setToken(token);
    setUser(user);
  }
  function logout() {
    setToken(null);
    setUser(null);
  }
  async function refresh() {
    try { setUser(await api.me()); } catch { /* ignora */ }
  }

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}
