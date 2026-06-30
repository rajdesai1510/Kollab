"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

export default function InstagramCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useAuth();
  
  const [error, setError] = useState("");
  const processed = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent double execution in strict mode
      if (processed.current) return;
      processed.current = true;

      const code = searchParams.get("code");
      const err = searchParams.get("error");
      const errReason = searchParams.get("error_reason");

      if (err) {
        setError(`Instagram connection failed: ${errReason || err}`);
        setTimeout(() => router.push("/onboarding/creator/instagram"), 3000);
        return;
      }

      if (!code) {
        setError("Invalid response from Instagram.");
        setTimeout(() => router.push("/onboarding/creator/instagram"), 3000);
        return;
      }

      try {
        await api.auth.connectInstagram(code);
        await refreshUser();
        
        // Wait briefly for context to update, but we can also just check current state
        // Actually, refreshUser() updates the context state, but it might not be synchronous for 'user' variable in this closure.
        // Let's rely on api.auth.me() or just direct them based on a query param or assume if they hit this, they either come from settings or onboarding.
        // A simple heuristic: if we are in auth callback, check if we want to redirect to details.
        
        const me = await api.auth.me();
        if (!me.onboarding_complete) {
          router.push("/onboarding/creator/details");
        } else {
          router.push("/creator/dashboard");
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to connect Instagram");
        // Redirect back to connection page on failure after a delay
        setTimeout(() => router.push("/onboarding/creator"), 3000);
      }
    };

    handleCallback();
  }, [searchParams, router, refreshUser]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 max-w-sm w-full">
        {error ? (
          <div className="space-y-4">
            <div className="w-12 h-12 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-slate-800">Connection Failed</h2>
            <p className="text-sm text-slate-500">{error}</p>
            <p className="text-xs text-slate-400">Redirecting you back...</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
            <h2 className="text-xl font-bold text-slate-800">Connecting...</h2>
            <p className="text-sm text-slate-500">Please wait while we link your Instagram account.</p>
          </div>
        )}
      </div>
    </div>
  );
}
