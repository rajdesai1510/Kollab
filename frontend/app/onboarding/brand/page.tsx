"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import type { BrandCategory } from "@/types";

const BRAND_CATEGORIES: BrandCategory[] = [
  "Food & Beverage", "Fitness & Wellness", "Fashion & Apparel",
  "Beauty & Skincare", "Technology", "Education",
  "Travel & Hospitality", "Home & Decor", "Health & Pharma",
  "Finance", "E-Commerce / D2C", "Retail", "Entertainment",
  "Non-Profit / NGO", "Other",
];

const INDIAN_STATES = [
  "Andhra Pradesh", "Delhi", "Gujarat", "Karnataka", "Kerala",
  "Maharashtra", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
  "Uttar Pradesh", "West Bengal", "Other",
];

export default function BrandOnboardingPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    business_name: "",
    tagline: "",
    description: "",
    category: "" as BrandCategory | "",
    website_url: "",
    city: "",
    state: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.business_name.trim()) {
      setError("Business name is required.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      await api.brands.createProfile({
        business_name: form.business_name,
        tagline: form.tagline,
        description: form.description,
        category: form.category || null,
        website_url: form.website_url,
        city: form.city,
        state: form.state,
      });
      await refreshUser();
      router.push("/brand/dashboard");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-6">
      <div className="max-w-xl mx-auto">
        <div className="text-center mb-8">
          <span className="font-outfit font-bold text-2xl text-slate-800">
            Nex<span className="text-indigo-600">us</span>
          </span>
          <h2 className="font-outfit text-2xl font-semibold text-slate-800 mt-6 mb-2">
            Tell us about your brand
          </h2>
          <p className="text-slate-500 text-sm">
            This is how creators will discover you.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-5">
            {/* Business name */}
            <div className="space-y-1.5">
              <Label htmlFor="business_name">Business name *</Label>
              <Input
                id="business_name"
                placeholder="e.g. Nirvana Naturals"
                value={form.business_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, business_name: e.target.value }))
                }
              />
            </div>

            {/* Tagline */}
            <div className="space-y-1.5">
              <Label htmlFor="tagline">Tagline</Label>
              <Input
                id="tagline"
                placeholder="e.g. Clean beauty for everyday India"
                value={form.tagline}
                onChange={(e) =>
                  setForm((f) => ({ ...f, tagline: e.target.value }))
                }
              />
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <Label htmlFor="description">About your brand</Label>
              <textarea
                id="description"
                rows={3}
                placeholder="What do you sell? Who is your customer? What kind of creator are you looking for?"
                value={form.description}
                onChange={(e) =>
                  setForm((f) => ({ ...f, description: e.target.value }))
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
              />
            </div>

            {/* Category */}
            <div className="space-y-1.5">
              <Label htmlFor="category">Category</Label>
              <select
                id="category"
                value={form.category}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    category: e.target.value as BrandCategory,
                  }))
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
              >
                <option value="">Select a category</option>
                {BRAND_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Website */}
            <div className="space-y-1.5">
              <Label htmlFor="website_url">Website</Label>
              <Input
                id="website_url"
                type="url"
                placeholder="https://yourbrand.in"
                value={form.website_url}
                onChange={(e) =>
                  setForm((f) => ({ ...f, website_url: e.target.value }))
                }
              />
            </div>

            {/* Location */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  placeholder="e.g. Bengaluru"
                  value={form.city}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, city: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="state">State</Label>
                <select
                  id="state"
                  value={form.state}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, state: e.target.value }))
                  }
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
                >
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-500 text-center">{error}</p>
          )}

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full h-12"
            size="lg"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              "Complete setup →"
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
