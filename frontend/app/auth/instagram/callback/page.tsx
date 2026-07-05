"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Loader2, Camera, AlertCircle } from "lucide-react";

export default function InstagramCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading, refreshUser } = useAuth();
  
  const [error, setError] = useState("");
  const processed = useRef(false);

  useEffect(() => {
    // Wait for authentication context to finish loading
    if (authLoading) return;

    const handleCallback = async () => {
      // Prevent double execution in strict mode
      if (processed.current) return;
      processed.current = true;

      const code = searchParams.get("code");
      const err = searchParams.get("error");
      const errReason = searchParams.get("error_reason");
      const errDesc = searchParams.get("error_description");

      const userRole = user?.role || "creator";
      const redirectTarget = userRole === "brand"
        ? "/onboarding/brand?step=2"
        : "/onboarding/creator/instagram";

      // If the user cancelled or Instagram/Meta returned an OAuth error (e.g. Captcha failed, access denied)
      if (err) {
        const errorMsg = errDesc || errReason || err;
        setError(`Instagram connection failed: ${errorMsg}`);
        setTimeout(() => router.push(redirectTarget), 4000);
        return;
      }

      if (!user) {
        setError("You must be logged in to connect your Instagram account.");
        setTimeout(() => router.push("/auth/login"), 3000);
        return;
      }

      if (!code) {
        setError("Invalid response received from Instagram.");
        setTimeout(() => router.push(redirectTarget), 3000);
        return;
      }

      try {
        await api.auth.connectInstagram(code);
        await refreshUser();
        
        if (userRole === "brand") {
          if (!user.onboarding_complete) {
            router.push("/onboarding/brand?step=2");
          } else {
            router.push("/brand/dashboard");
          }
        } else {
          if (!user.onboarding_complete) {
            router.push("/onboarding/creator/details");
          } else {
            router.push("/creator/dashboard");
          }
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to connect Instagram");
        setTimeout(() => router.push(userRole === "brand" ? "/onboarding/brand?step=2" : "/onboarding/creator"), 4000);
      }
    };

    handleCallback();
  }, [searchParams, router, refreshUser, user, authLoading]);

  // Loading state for auth check
  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 max-w-sm w-full space-y-4">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
          <h2 className="text-lg font-bold text-slate-800">Verifying session...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 max-w-md w-full">
        {error ? (
          <div className="space-y-4">
            <div className="w-12 h-12 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-slate-800">Connection Failed</h2>
            <p className="text-sm text-slate-500 leading-relaxed">{error}</p>
            <p className="text-xs text-slate-400">Redirecting you back...</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-12 h-12 bg-pink-50 text-pink-600 rounded-full flex items-center justify-center mx-auto">
              <Camera className="w-6 h-6 animate-pulse" />
            </div>
            <h2 className="text-xl font-bold text-slate-800">Connecting Instagram...</h2>
            <p className="text-sm text-slate-500">Please wait while we link your account and sync stats.</p>
            <Loader2 className="w-5 h-5 animate-spin mx-auto text-pink-600 mt-2" />
          </div>
        )}
      </div>
    </div>
  );
}
