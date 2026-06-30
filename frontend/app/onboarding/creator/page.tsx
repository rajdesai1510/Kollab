"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

const InstagramIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
  </svg>
);

export default function CreatorInstagramPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchUrl = async () => {
      try {
        const res = await api.auth.getInstagramAuthUrl();
        setAuthUrl(res.url);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load Instagram auth URL");
      } finally {
        setIsLoading(false);
      }
    };
    fetchUrl();
  }, []);

  const handleSkip = () => {
    router.push("/onboarding/creator/details");
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-6 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-3xl border border-slate-100 shadow-sm p-8 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="w-16 h-16 bg-pink-50 text-pink-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <InstagramIcon className="w-8 h-8" />
        </div>
        
        <h2 className="font-outfit text-2xl font-bold text-slate-900 mb-3">
          Connect your Instagram
        </h2>
        <p className="text-slate-500 mb-8 text-sm leading-relaxed">
          We use Instagram to automatically pull your profile picture, username, and stats. No typing required.
        </p>

        {error && (
          <p className="text-sm text-red-500 mb-6 bg-red-50 p-3 rounded-lg border border-red-100">
            {error}
          </p>
        )}

        <div className="space-y-3">
          {isLoading ? (
            <button disabled className="w-full flex items-center justify-center gap-2 h-12 text-sm font-medium rounded-xl bg-slate-100 text-slate-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              Loading...
            </button>
          ) : (
            <a
              href={authUrl || "#"}
              className="w-full flex items-center justify-center gap-2 h-12 text-sm font-medium rounded-xl bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 hover:opacity-90 text-white transition-opacity shadow-sm"
            >
              <InstagramIcon className="w-5 h-5" />
              Connect Instagram
            </a>
          )}

          <button
            onClick={handleSkip}
            className="w-full h-12 flex items-center justify-center text-sm font-medium text-slate-500 hover:text-slate-700 transition-colors"
          >
            I'll do this later
          </button>
        </div>
      </div>
    </div>
  );
}
