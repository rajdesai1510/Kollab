"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Briefcase, Camera, Loader2 } from "lucide-react";

type Role = "creator" | "brand";

const roles = [
  {
    id: "creator" as Role,
    icon: Camera,
    label: "I'm a Creator",
    desc: "I create content on Instagram and want to work with brands.",
    accent: "indigo",
  },
  {
    id: "brand" as Role,
    icon: Briefcase,
    label: "I'm a Brand",
    desc: "I represent a business looking for creators to collaborate with.",
    accent: "rose",
  },
];

export default function OnboardingPage() {
  const { setRole, user } = useAuth();
  const router = useRouter();
  const [selected, setSelected] = useState<Role | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleContinue = async () => {
    if (!selected) return;
    setIsLoading(true);
    setError("");
    try {
      await setRole(selected);
      router.push(`/onboarding/${selected}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-10">
          <span className="font-outfit font-bold text-2xl text-slate-800">
            Nex<span className="text-indigo-600">us</span>
          </span>
          <h2 className="font-outfit text-2xl font-semibold text-slate-800 mt-6 mb-2">
            Welcome{user?.name ? `, ${user.name.split(" ")[0]}` : ""}!
          </h2>
          <p className="text-slate-500 text-sm">
            How will you use Nexus?
          </p>
        </div>

        {/* Role Cards */}
        <div className="space-y-3 mb-6">
          {roles.map(({ id, icon: Icon, label, desc }) => {
            const isActive = selected === id;
            return (
              <button
                key={id}
                onClick={() => setSelected(id)}
                className={`w-full text-left rounded-2xl border p-5 transition-all ${
                  isActive
                    ? "border-indigo-400 bg-indigo-50 shadow-sm"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
                }`}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      isActive
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800">{label}</p>
                    <p className="text-sm text-slate-500 mt-0.5">{desc}</p>
                  </div>
                  {/* Selection dot */}
                  <div
                    className={`ml-auto w-4 h-4 rounded-full border-2 shrink-0 mt-1 transition-colors ${
                      isActive
                        ? "border-indigo-600 bg-indigo-600"
                        : "border-slate-300"
                    }`}
                  />
                </div>
              </button>
            );
          })}
        </div>

        {error && (
          <p className="text-sm text-red-500 text-center mb-4">{error}</p>
        )}

        <Button
          onClick={handleContinue}
          disabled={!selected || isLoading}
          className="w-full h-12"
          size="lg"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            "Continue →"
          )}
        </Button>

        <p className="text-xs text-slate-400 text-center mt-4">
          You can only pick one — choose carefully!
        </p>
      </div>
    </div>
  );
}
