"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, ArrowRight, ArrowLeft, Building2 } from "lucide-react";

interface BrandFormState {
  business_name: string;
  category: string;
  custom_category: string;
  description: string;
}

const BRAND_CATEGORIES = [
  "Food & Beverage", "Fitness & Wellness", "Fashion & Apparel",
  "Beauty & Skincare", "Technology", "Education",
  "Travel & Hospitality", "Home & Decor", "Health & Pharma",
  "Finance", "Automotive", "Real Estate", "Retail",
  "E-Commerce / D2C", "Entertainment", "Non-Profit / NGO", "Other",
];

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

function BrandOnboardingForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const stepParam = searchParams.get("step");
  const { refreshUser, user } = useAuth();

  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isInstagramLoading, setIsInstagramLoading] = useState(false);
  const [instagramAuthUrl, setInstagramAuthUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  const [form, setForm] = useState<BrandFormState>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("nexus_brand_onboarding_wizard");
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {}
      }
    }
    return {
      business_name: "",
      category: "",
      custom_category: "",
      description: "",
    };
  });

  useEffect(() => {
    localStorage.setItem("nexus_brand_onboarding_wizard", JSON.stringify(form));
  }, [form]);

  useEffect(() => {
    if (stepParam === "2") {
      setStep(2);
    }
  }, [stepParam]);

  // Load Instagram URL when entering Step 2
  useEffect(() => {
    if (step === 2 && !instagramAuthUrl) {
      const fetchAuthUrl = async () => {
        setIsInstagramLoading(true);
        try {
          const res = await api.auth.getInstagramAuthUrl();
          setInstagramAuthUrl(res.url);
        } catch (e: unknown) {
          console.error("Failed to load Instagram auth URL", e);
        } finally {
          setIsInstagramLoading(false);
        }
      };
      fetchAuthUrl();
    }
  }, [step, instagramAuthUrl]);

  const handleNext = () => {
    if (!form.business_name.trim()) {
      setError("Business name is required.");
      return;
    }
    if (!form.category) {
      setError("Please select a category.");
      return;
    }
    if (form.category === "Other" && !form.custom_category.trim()) {
      setError("Please specify your category.");
      return;
    }
    setError("");
    setStep(2);
  };

  const handleBack = () => {
    setError("");
    setStep(1);
  };

  const handleCompleteSetup = async () => {
    setIsLoading(true);
    setError("");
    try {
      const finalCategory = form.category === "Other" ? form.custom_category.trim() : form.category;
      
      await api.brands.createProfile({
        business_name: form.business_name.trim(),
        category: (finalCategory as any) || null,
        tagline: "",
        description: form.description.trim(),
        website_url: "",
        city: "",
        state: "",
      });

      // Clear local storage
      localStorage.removeItem("nexus_brand_onboarding_wizard");
      await refreshUser();
      router.push("/brand/dashboard");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center py-12 px-6">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <span className="font-outfit font-bold text-2xl text-slate-800">
            Nex<span className="text-rose-500">us</span>
          </span>
          
          {/* Stepper indicator */}
          <div className="flex items-center justify-center gap-2 mt-4">
            <span className={`w-8 h-2 rounded-full transition-all duration-300 ${step === 1 ? "bg-rose-500 w-12" : "bg-slate-200"}`} />
            <span className={`w-8 h-2 rounded-full transition-all duration-300 ${step === 2 ? "bg-rose-500 w-12" : "bg-slate-200"}`} />
          </div>
        </div>

        {step === 1 ? (
          <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="text-center">
              <div className="w-12 h-12 bg-rose-50 text-rose-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Building2 className="w-6 h-6" />
              </div>
              <h2 className="font-outfit text-2xl font-bold text-slate-900 mb-1">
                Tell us about your brand
              </h2>
              <p className="text-slate-500 text-sm">
                Set up your business identity to connect with creators.
              </p>
            </div>

            <div className="space-y-4">
              {/* Business Name */}
              <div className="space-y-1.5">
                <Label htmlFor="business_name">Business Name *</Label>
                <Input
                  id="business_name"
                  placeholder="e.g. Bloom Naturals"
                  value={form.business_name}
                  onChange={(e) => setForm(f => ({ ...f, business_name: e.target.value }))}
                  className="h-11 rounded-xl"
                />
              </div>

              {/* Category */}
              <div className="space-y-1.5">
                <Label htmlFor="category">Category *</Label>
                <select
                  id="category"
                  value={form.category}
                  onChange={(e) => setForm(f => ({ ...f, category: e.target.value }))}
                  className="w-full h-11 rounded-xl border border-slate-200 px-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500 bg-white"
                >
                  <option value="">Select a category</option>
                  {BRAND_CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Custom Category */}
              {form.category === "Other" && (
                <div className="space-y-1.5 animate-in fade-in slide-in-from-top-2 duration-200">
                  <Label htmlFor="custom_category">Please specify category *</Label>
                  <Input
                    id="custom_category"
                    placeholder="e.g. Sustainable Crafts"
                    value={form.custom_category}
                    onChange={(e) => setForm(f => ({ ...f, custom_category: e.target.value }))}
                    className="h-11 rounded-xl"
                  />
                </div>
              )}

              {/* Description */}
              <div className="space-y-1.5">
                <Label htmlFor="description">Short Description</Label>
                <textarea
                  id="description"
                  rows={4}
                  placeholder="Describe your brand, products, or collaboration goals..."
                  value={form.description}
                  onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500 resize-none"
                />
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-500 text-center font-medium bg-red-50 p-2 rounded-lg border border-red-100">
                {error}
              </p>
            )}

            <Button
              onClick={handleNext}
              className="w-full h-12 bg-rose-500 hover:bg-rose-600 text-white rounded-xl flex items-center justify-center gap-2"
            >
              Continue <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        ) : (
          <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="text-center">
              <div className="w-16 h-16 bg-rose-50 text-rose-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <InstagramIcon className="w-8 h-8" />
              </div>
              <h2 className="font-outfit text-2xl font-bold text-slate-900 mb-1">
                Link your Instagram account
              </h2>
              <p className="text-slate-500 text-sm leading-relaxed">
                Connect your brand's social profile to showcase your aesthetic and style to creators.
              </p>
            </div>

            {user?.instagram_connected ? (
              <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 text-center">
                <p className="text-emerald-800 font-medium text-sm flex items-center justify-center gap-1.5">
                  <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse" />
                  Instagram Connected
                </p>
              </div>
            ) : null}

            {error && (
              <p className="text-sm text-red-500 text-center font-medium bg-red-50 p-2 rounded-lg border border-red-100">
                {error}
              </p>
            )}

            <div className="space-y-3">
              {!user?.instagram_connected && (
                isInstagramLoading ? (
                  <button disabled className="w-full flex items-center justify-center gap-2 h-12 text-sm font-medium rounded-xl bg-slate-100 text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Loading...
                  </button>
                ) : (
                  <a
                    href={instagramAuthUrl || "#"}
                    className="w-full flex items-center justify-center gap-2 h-12 text-sm font-medium rounded-xl bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 hover:opacity-90 text-white transition-opacity shadow-sm font-outfit"
                  >
                    <InstagramIcon className="w-5 h-5" />
                    Connect Instagram
                  </a>
                )
              )}

              <Button
                onClick={handleCompleteSetup}
                disabled={isLoading}
                className="w-full h-12 bg-rose-500 hover:bg-rose-600 text-white rounded-xl"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : user?.instagram_connected ? (
                  "Complete Setup"
                ) : (
                  "Complete Setup (Skip Instagram)"
                )}
              </Button>

              <button
                onClick={handleBack}
                disabled={isLoading}
                className="w-full h-12 flex items-center justify-center text-sm font-medium text-slate-400 hover:text-slate-600 transition-colors gap-1.5"
              >
                <ArrowLeft className="w-4 h-4" /> Go Back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function BrandOnboardingPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    }>
      <BrandOnboardingForm />
    </Suspense>
  );
}
