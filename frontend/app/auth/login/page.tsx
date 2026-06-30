"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  // Already logged in → redirect
  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated && user) {
      if (!user.onboarding_complete) {
        router.replace("/onboarding");
      } else {
        router.replace("/dashboard");
      }
    }
  }, [isAuthenticated, isLoading, user, router]);

  const handleGoogleLogin = () => {
    window.location.href = api.auth.googleLoginUrl();
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="font-outfit text-3xl font-bold text-slate-900 tracking-tight">
            Nex<span className="text-indigo-600">us</span>
          </h1>
          <p className="text-slate-500 mt-2 text-sm">
            India's creator-brand collaboration platform
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8">
          <h2 className="font-outfit text-xl font-semibold text-slate-800 text-center mb-1">
            Sign in to continue
          </h2>
          <p className="text-sm text-slate-400 text-center mb-8">
            Use your Google account — takes 10 seconds.
          </p>

          <button
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 h-12 text-base bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
          >
            <LogIn className="w-5 h-5" />
            Continue with Google
          </button>

          <p className="text-xs text-slate-400 text-center mt-6 leading-relaxed">
            By signing in, you agree to our Terms of Service and Privacy Policy.
            No password required.
          </p>
        </div>

        {/* Back link */}
        <p className="text-center mt-6 text-sm text-slate-400">
          <a href="/" className="hover:text-slate-600 transition-colors">
            ← Back to home
          </a>
        </p>
      </div>
    </div>
  );
}
