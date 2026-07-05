"use client";

/**
 * Nexus — Auth Context
 *
 * Provides current user state + auth actions to the entire app.
 * Use the `useAuth()` hook anywhere inside <AuthProvider>.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { api, tokenStore } from "@/lib/api";
import type { User, UserRole } from "@/types";
import { Loader2 } from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Context shape
// ─────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  /** Called after Google OAuth callback sets the token in localStorage. */
  refreshUser: () => Promise<void>;

  /** Set role during onboarding. */
  setRole: (role: UserRole) => Promise<void>;

  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ─────────────────────────────────────────────────────────────
// Provider
// ─────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = tokenStore.get();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await api.auth.me();
      setUser(me);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message.toLowerCase() : "";
      if (
        errMsg.includes("unauthorized") ||
        errMsg.includes("expired") ||
        errMsg.includes("invalid") ||
        errMsg.includes("auth")
      ) {
        tokenStore.clearAll();
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const setRole = useCallback(
    async (role: UserRole) => {
      const updated = await api.auth.setRole(role as "creator" | "brand");
      setUser(updated);
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch {
      // ignore — clear tokens regardless
    }
    tokenStore.clearAll();
    setUser(null);
    router.push("/");
  }, [router]);

  const pathname = usePathname();
  const publicPaths = ["/", "/auth/login", "/auth/callback", "/auth/instagram/callback"];
  const isPublic = publicPaths.includes(pathname);

  useEffect(() => {
    if (!isLoading && !user && !isPublic) {
      router.push("/");
    }
  }, [user, isLoading, isPublic, router]);

  if (isLoading && !isPublic) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-400 text-xs font-medium animate-pulse">Verifying credentials...</p>
      </div>
    );
  }

  if (!isLoading && !user && !isPublic) {
    return null;
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        refreshUser,
        setRole,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ─────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
