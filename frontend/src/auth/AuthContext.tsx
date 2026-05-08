import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";
import { authApi } from "../api/authApi";
import { kbApi } from "../api/kbApi";
import { tokenStorage } from "../api/client";
import type { CurrentUser, LoginRequest } from "../types/auth";
import type { KnowledgeBase } from "../types/kb";

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: CurrentUser | null;
  accessibleKbs: KnowledgeBase[];
  selectedKb: KnowledgeBase | null;
  login: (payload: LoginRequest) => Promise<void>;
  logout: () => void;
  refreshAccessibleKbs: () => Promise<void>;
  setSelectedKbById: (kbId: number) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [accessibleKbs, setAccessibleKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshAccessibleKbs = async () => {
    if (!user) {
      setAccessibleKbs([]);
      setSelectedKb(null);
      return;
    }
    const kbs = await kbApi.listAccessibleKnowledgeBases();
    setAccessibleKbs(kbs);
    setSelectedKb((prev) => {
      if (prev && kbs.some((kb) => kb.id === prev.id)) return prev;
      return kbs[0] ?? null;
    });
  };

  const bootstrap = async () => {
    const token = tokenStorage.get();
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
      const kbs = await kbApi.listAccessibleKnowledgeBases();
      setAccessibleKbs(kbs);
      setSelectedKb(kbs[0] ?? null);
    } catch {
      tokenStorage.clear();
      setUser(null);
      setAccessibleKbs([]);
      setSelectedKb(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void bootstrap();
  }, []);

  const login = async (payload: LoginRequest) => {
    const auth = await authApi.login(payload);
    tokenStorage.set(auth.access_token);
    const me = await authApi.me();
    setUser(me);
    const kbs = await kbApi.listAccessibleKnowledgeBases();
    setAccessibleKbs(kbs);
    setSelectedKb(kbs[0] ?? null);
  };

  const logout = () => {
    tokenStorage.clear();
    setUser(null);
    setAccessibleKbs([]);
    setSelectedKb(null);
  };

  const setSelectedKbById = (kbId: number) => {
    const next = accessibleKbs.find((kb) => kb.id === kbId) ?? null;
    setSelectedKb(next);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(user),
      isLoading,
      user,
      accessibleKbs,
      selectedKb,
      login,
      logout,
      refreshAccessibleKbs,
      setSelectedKbById,
    }),
    [user, isLoading, accessibleKbs, selectedKb],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
