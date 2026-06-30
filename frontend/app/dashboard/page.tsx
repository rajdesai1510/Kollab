"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

/**
 * Smart redirect dashboard — based on user role, redirects to the right home.
 * Also handles: not authenticated → /auth/login, onboarding incomplete → /onboarding
 */
export default function DashboardPage() {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/auth/login");
      return;
    }
    if (!user?.onboarding_complete) {
      router.replace("/onboarding");
      return;
    }
    switch (user.role) {
      case "creator":
        router.replace("/creator/dashboard");
        break;
      case "brand":
        router.replace("/brand/dashboard");
        break;
      case "admin":
        router.replace("/admin/dashboard");
        break;
    }
  }, [isLoading, isAuthenticated, user, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
    </div>
  );
}
