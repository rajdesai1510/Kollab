"use client";

/**
 * OAuth Callback handler
 * The backend redirects here after Google login:
 * /auth/callback?token=<jwt>
 *
 * We store the token, refresh user, then redirect.
 */

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { tokenStore } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";
import { Suspense } from "react";

function CallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refreshUser } = useAuth();

  useEffect(() => {
    const token = searchParams.get("token");
    const refreshToken = searchParams.get("refresh_token");

    if (!token) {
      router.replace("/auth/login?error=no_token");
      return;
    }

    tokenStore.set(token);
    if (refreshToken) tokenStore.setRefresh(refreshToken);

    refreshUser().then(() => {
      router.replace("/dashboard");
    });
  }, [searchParams, router, refreshUser]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-50">
      <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      <p className="text-slate-500 text-sm">Signing you in…</p>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    }>
      <CallbackHandler />
    </Suspense>
  );
}
