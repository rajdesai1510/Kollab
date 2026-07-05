"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Camera,
  Link2,
  CheckCheck,
} from "lucide-react";
import Link from "next/link";
import { formatCount, formatEngagement } from "@/lib/utils";

const INSTAGRAM_CONNECT_URL = `${process.env.NEXT_PUBLIC_API_URL}/api/auth/instagram/start`;

const BRAND_CATEGORIES = [
  "Food & Beverage", "Fitness & Wellness", "Fashion & Apparel",
  "Beauty & Skincare", "Technology", "Education",
  "Travel & Hospitality", "Home & Decor", "Health & Pharma",
  "Finance", "Automotive", "Real Estate", "Retail",
  "E-Commerce / D2C", "Entertainment", "Non-Profit / NGO", "Other",
];

export default function BrandProfilePage() {
  const { user, refreshUser } = useAuth();
  const queryClient = useQueryClient();

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");

  const { data: profile, isLoading, refetch } = useQuery({
    queryKey: ["brand-profile"],
    queryFn: () => api.brands.getProfile(),
    enabled: !!user,
    retry: false,
  });

  const [form, setForm] = useState({
    business_name: "",
    tagline: "",
    description: "",
    category: "",
    website_url: "",
    instagram_handle: "",
  });

  useEffect(() => {
    if (profile) {
      setForm({
        business_name: profile.business_name || "",
        tagline: profile.tagline || "",
        description: profile.description || "",
        category: profile.category || "",
        website_url: profile.website_url || "",
        instagram_handle: profile.instagram_handle || "",
      });
    }
  }, [profile]);

  const syncMutation = useMutation({
    mutationFn: () => api.brands.syncInstagram(),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(["brand-profile"], updatedProfile);
      refetch();
    },
  });

  const syncError = syncMutation.error instanceof Error
    ? syncMutation.error.message
    : syncMutation.isError ? "Sync failed. Please try again." : null;

  const isTokenError = syncError?.toLowerCase().includes("expired") ||
    syncError?.toLowerCase().includes("reconnect") ||
    syncError?.toLowerCase().includes("invalid");

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveError("");
    setSaveSuccess("");

    if (!form.business_name.trim()) {
      setSaveError("Business name is required.");
      return;
    }

    setIsSaving(true);
    try {
      await api.brands.updateProfile({
        business_name: form.business_name,
        tagline: form.tagline || undefined,
        description: form.description || undefined,
        category: form.category || undefined,
        website_url: form.website_url || undefined,
        instagram_handle: form.instagram_handle || undefined,
      } as any);
      await refreshUser();
      await refetch();
      setSaveSuccess("Profile updated successfully!");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto space-y-8 pb-12">
        {/* Header */}
        <div>
          <h1 className="font-outfit text-3xl font-bold text-slate-800">Brand Profile</h1>
          <p className="text-slate-500 text-sm mt-1">
            Manage your brand identity and Instagram connection.
          </p>
        </div>

        {/* Save notifications */}
        {saveError && (
          <div className="p-4 bg-red-50 border border-red-100 rounded-2xl flex items-start gap-3 text-red-600 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{saveError}</span>
          </div>
        )}
        {saveSuccess && (
          <div className="p-4 bg-green-50 border border-green-100 rounded-2xl flex items-start gap-3 text-green-600 text-sm">
            <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{saveSuccess}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: Instagram Connection Card */}
          <div className="space-y-5 lg:col-span-1">

            {/* Instagram status card */}
            <div className={`rounded-3xl border p-6 space-y-4 ${user?.instagram_connected
              ? "bg-gradient-to-br from-pink-50 to-purple-50 border-pink-100"
              : "bg-white border-slate-100 shadow-sm"
              }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Camera className={`w-5 h-5 ${user?.instagram_connected ? "text-pink-600" : "text-slate-400"}`} />

                  <h2 className="font-outfit text-base font-bold text-slate-800">Instagram</h2>
                </div>
                {user?.instagram_connected ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold bg-green-100 text-green-700 px-2.5 py-1 rounded-full">
                    <CheckCheck className="w-3 h-3" /> Connected
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold bg-slate-100 text-slate-500 px-2.5 py-1 rounded-full">
                    Not connected
                  </span>
                )}
              </div>

              {user?.instagram_connected ? (
                <div className="space-y-3">
                  {/* Handle */}
                  {profile?.instagram_handle && (
                    <div className="flex items-center gap-2 bg-white/70 rounded-xl px-3 py-2">
                      <span className="text-slate-400 text-xs">@</span>
                      <span className="font-semibold text-slate-800 text-sm">{profile.instagram_handle}</span>
                    </div>
                  )}

                  {/* Stats grid */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-white/70 rounded-xl px-3 py-2.5 text-center">
                      <p className="text-xs text-slate-400">Followers</p>
                      <p className="font-bold text-slate-800 text-sm mt-0.5">
                        {profile?.instagram_followers
                          ? formatCount(profile.instagram_followers)
                          : <span className="text-slate-300">—</span>}
                      </p>
                    </div>
                    <div className="bg-white/70 rounded-xl px-3 py-2.5 text-center">
                      <p className="text-xs text-slate-400">Engagement</p>
                      <p className="font-bold text-slate-800 text-sm mt-0.5">
                        {profile?.instagram_engagement_rate
                          ? formatEngagement(profile.instagram_engagement_rate)
                          : <span className="text-slate-300">—</span>}
                      </p>
                    </div>
                  </div>

                  {/* Sync section */}
                  {syncError ? (
                    <div className="bg-red-50 border border-red-100 rounded-xl p-3 space-y-2">
                      <p className="text-xs text-red-600 flex items-start gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                        {syncError}
                      </p>
                      {isTokenError ? (
                        <a
                          href={INSTAGRAM_CONNECT_URL}
                          className="w-full flex items-center justify-center gap-2 bg-pink-600 hover:bg-pink-700 text-white text-xs font-semibold rounded-xl py-2 transition-colors"
                        >
                          <Camera className="w-3.5 h-3.5" />
                          Reconnect Instagram
                        </a>
                      ) : (
                        <button
                          onClick={() => syncMutation.mutate()}
                          className="w-full flex items-center justify-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl py-2 transition-colors"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                          Try again
                        </button>
                      )}
                    </div>
                  ) : (
                    <button
                      onClick={() => syncMutation.mutate()}
                      disabled={syncMutation.isPending}
                      className="w-full flex items-center justify-center gap-2 bg-white/80 hover:bg-white border border-pink-200 text-pink-700 text-xs font-semibold rounded-xl py-2.5 transition-colors disabled:opacity-60"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
                      {syncMutation.isPending ? "Syncing..." : "Sync stats"}
                    </button>
                  )}

                  {syncMutation.isSuccess && (
                    <p className="text-[11px] text-green-600 text-center flex items-center justify-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Stats updated just now
                    </p>
                  )}

                  {profile?.instagram_last_synced && !syncMutation.isSuccess && (
                    <p className="text-[10px] text-slate-400 text-center">
                      Last synced {new Date(profile.instagram_last_synced).toLocaleString("en-IN", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Connect your brand's Instagram to verify follower counts and show engagement metrics to creators.
                  </p>
                  <a
                    href={INSTAGRAM_CONNECT_URL}
                    className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-pink-500 to-purple-600 hover:opacity-90 text-white text-sm font-semibold rounded-xl py-2.5 transition-opacity"
                  >
                    <Camera className="w-4 h-4" />
                    Connect Instagram
                  </a>
                </div>
              )}
            </div>

            {/* Handle override tip */}
            {!user?.instagram_connected && profile?.instagram_handle && (
              <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4 flex items-start gap-2">
                <Link2 className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                <p className="text-xs text-amber-700">
                  You've entered <strong>@{profile.instagram_handle}</strong> manually. Connect your account above to verify stats and show real follower data.
                </p>
              </div>
            )}
          </div>

          {/* Right: Profile Form */}
          <div className="lg:col-span-2">
            <form onSubmit={handleSave}>
              <div className="bg-white border border-slate-100 shadow-sm rounded-3xl p-8 space-y-6">
                <h2 className="font-outfit text-lg font-bold text-slate-800 border-b border-slate-50 pb-4">
                  Brand Details
                </h2>

                <div className="space-y-4">
                  {/* Business Name */}
                  <div className="space-y-1.5">
                    <label htmlFor="business-name" className="text-sm font-semibold text-slate-700">
                      Business Name <span className="text-red-400">*</span>
                    </label>
                    <input
                      id="business-name"
                      type="text"
                      required
                      value={form.business_name}
                      onChange={(e) => setForm((f) => ({ ...f, business_name: e.target.value }))}
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      placeholder="e.g. Bloom Naturals"
                    />
                  </div>

                  {/* Tagline */}
                  <div className="space-y-1.5">
                    <label htmlFor="tagline" className="text-sm font-semibold text-slate-700">
                      Tagline <span className="text-slate-400 font-normal text-xs">(shown on your brand card)</span>
                    </label>
                    <input
                      id="tagline"
                      type="text"
                      value={form.tagline}
                      onChange={(e) => setForm((f) => ({ ...f, tagline: e.target.value }))}
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      placeholder="e.g. Natural beauty for every skin type"
                    />
                  </div>

                  {/* Description */}
                  <div className="space-y-1.5">
                    <label htmlFor="description" className="text-sm font-semibold text-slate-700">Description</label>
                    <textarea
                      id="description"
                      rows={4}
                      value={form.description}
                      onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                      placeholder="Tell creators about your brand, products, and campaign goals..."
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
                    />
                  </div>

                  {/* Category */}
                  <div className="space-y-1.5">
                    <label htmlFor="category" className="text-sm font-semibold text-slate-700">Category</label>
                    <select
                      id="category"
                      value={form.category}
                      onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
                    >
                      <option value="">Select a category</option>
                      {BRAND_CATEGORIES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  {/* Website */}
                  <div className="space-y-1.5">
                    <label htmlFor="website" className="text-sm font-semibold text-slate-700">Website URL</label>
                    <input
                      id="website"
                      type="url"
                      value={form.website_url}
                      onChange={(e) => setForm((f) => ({ ...f, website_url: e.target.value }))}
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      placeholder="https://yourbrand.com"
                    />
                  </div>

                  {/* Instagram handle (manual) */}
                  <div className="space-y-1.5">
                    <label htmlFor="ig-handle" className="text-sm font-semibold text-slate-700">
                      Instagram Handle
                      {user?.instagram_connected && (
                        <span className="ml-2 text-[11px] font-normal text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                          Auto-filled from connected account
                        </span>
                      )}
                    </label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">@</span>
                      <input
                        id="ig-handle"
                        type="text"
                        value={form.instagram_handle}
                        onChange={(e) => setForm((f) => ({ ...f, instagram_handle: e.target.value.replace("@", "") }))}
                        readOnly={!!user?.instagram_connected}
                        className={`w-full rounded-xl border px-4 py-3 pl-8 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 ${
                          user?.instagram_connected
                            ? "border-green-200 bg-green-50/50 text-slate-600"
                            : "border-slate-200"
                        }`}
                        placeholder="yourbrand"
                      />
                    </div>
                    {!user?.instagram_connected && (
                      <p className="text-xs text-slate-400">
                        Connect your Instagram account above to auto-fill and verify this.
                      </p>
                    )}
                  </div>
                </div>

                {/* Submit */}
                <div className="flex items-center justify-end gap-3 pt-6 border-t border-slate-100">
                  <Button
                    type="submit"
                    disabled={isSaving}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-6 h-11 rounded-xl transition-colors shadow-sm disabled:opacity-70"
                  >
                    {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Changes
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
