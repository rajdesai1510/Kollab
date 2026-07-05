"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Loader2, Save, RefreshCw, AlertCircle, CheckCircle,
  Camera, MapPin, AlertTriangle, CheckCheck,
} from "lucide-react";
import type { NicheCategory, CollabType } from "@/types";
import {
  INDIA_STATES_AND_DISTRICTS,
  getDistrictsForState,
  findMatchingStateAndDistrict,
} from "@/lib/india-regions";

const NICHES: NicheCategory[] = [
  "Food", "Fitness", "Fashion", "Beauty", "Technology",
  "Travel", "Lifestyle", "Gaming", "Education", "Finance",
  "Parenting", "Music", "Comedy", "Health", "Other",
];

const COLLAB_TYPES: CollabType[] = [
  "Paid Post", "Product Seeding", "Long-term Ambassador",
  "Barter", "Affiliate", "Event Coverage",
];

const MOCK_AVATARS = [
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Priya",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Raj",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Ananya",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Kabir",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Diya",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Arjun",
];

const INSTAGRAM_CONNECT_URL = `${process.env.NEXT_PUBLIC_API_URL}/api/auth/instagram/start`;

export default function CreatorProfilePage() {
  const { user, refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isDetectingLocation, setIsDetectingLocation] = useState(false);

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }
    setIsDetectingLocation(true);
    setError("");
    setSuccess("");
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=10`,
            {
              headers: {
                "Accept-Language": "en"
              }
            }
          );
          if (!res.ok) throw new Error("Failed to fetch location details.");
          const data = await res.json();
          const address = data.address || {};
          
          const apiState = address.state || "";
          const apiDistrict = address.state_district || address.county || address.city || address.subdistrict || "";
          
          const match = findMatchingStateAndDistrict(apiState, apiDistrict);
          if (match) {
            setForm((f) => ({
              ...f,
              state: match.state,
              city: match.district,
            }));
            setSuccess("Location detected successfully!");
          } else {
            setError(`Could not map detected location (${apiDistrict}, ${apiState}) to an Indian state/district.`);
          }
        } catch (err) {
          setError("Failed to resolve your location. Please select manually.");
        } finally {
          setIsDetectingLocation(false);
        }
      },
      (err) => {
        setError("Location access denied or unavailable. Please select manually.");
        setIsDetectingLocation(false);
      },
      { timeout: 10000 }
    );
  };

  const { data: profile, isLoading, refetch } = useQuery({
    queryKey: ["creator-profile"],
    queryFn: () => api.creators.getProfile("me"),
    enabled: !!user,
    retry: false,
  });

  const syncMutation = useMutation({
    mutationFn: () => api.creators.syncInstagram(),
    onSuccess: (updated) => {
      queryClient.setQueryData(["creator-profile"], updated);
      refetch();
      refreshUser();
    },
  });

  const syncError = syncMutation.error instanceof Error
    ? syncMutation.error.message
    : syncMutation.isError ? "Sync failed. Please try again." : null;

  const isTokenError = !!(syncError && (
    syncError.toLowerCase().includes("expired") ||
    syncError.toLowerCase().includes("reconnect") ||
    syncError.toLowerCase().includes("invalid") ||
    syncError.toLowerCase().includes("oauth")
  ));

  const [form, setForm] = useState({
    display_name: "",
    bio: "",
    city: "",
    state: "",
    niches: [] as NicheCategory[],
    collab_types: [] as CollabType[],
    rate_min: "" as string | number,
    rate_max: "" as string | number,
    avatar_url: "",
  });

  useEffect(() => {
    if (profile) {
      setForm({
        display_name: profile.display_name || "",
        bio: profile.bio || "",
        city: profile.city || "",
        state: profile.state || "",
        niches: profile.niches || [],
        collab_types: profile.collab_types || [],
        rate_min: profile.rate_min !== null ? profile.rate_min : "",
        rate_max: profile.rate_max !== null ? profile.rate_max : "",
        avatar_url: profile.instagram_profile_pic_url || user?.avatar_url || "",
      });
    }
  }, [profile, user]);

  const toggle = <T extends string>(arr: T[], val: T): T[] =>
    arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val];

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.display_name.trim()) {
      setError("Display Name is required.");
      return;
    }
    if (!form.avatar_url.trim()) {
      setError("Profile picture is mandatory. Please select an avatar or enter a custom URL.");
      return;
    }
    if (form.niches.length === 0) {
      setError("Please select at least one niche.");
      return;
    }
    if (form.niches.length > 5) {
      setError("You can only select up to 5 niches.");
      return;
    }

    setIsSaving(true);
    try {
      const minVal = form.rate_min === "" ? null : Number(form.rate_min);
      const maxVal = form.rate_max === "" ? null : Number(form.rate_max);

      await api.creators.updateProfile({
        display_name: form.display_name,
        bio: form.bio,
        city: form.city,
        state: form.state,
        niches: form.niches,
        collab_types: form.collab_types,
        rate_min: minVal,
        rate_max: maxVal,
        avatar_url: form.avatar_url,
      });

      await refreshUser();
      await refetch();
      setSuccess("Profile updated successfully!");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update profile");
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
          <h1 className="font-outfit text-3xl font-bold text-slate-800">My Profile</h1>
          <p className="text-slate-500 text-sm mt-1">
            Customize your profile details, manage niches, and sync Instagram stats.
          </p>
        </div>

        {/* Notifications */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-100 rounded-2xl flex items-start gap-3 text-red-600 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="p-4 bg-green-50 border border-green-100 rounded-2xl flex items-start gap-3 text-green-600 text-sm">
            <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Avatar & Instagram Status */}
          <div className="space-y-6 lg:col-span-1">
            <div className="bg-white border border-slate-100 shadow-sm rounded-3xl p-6 flex flex-col items-center">
              <h2 className="font-outfit text-base font-bold text-slate-800 mb-4 self-start">
                Profile Picture
              </h2>

              <div className="w-28 h-28 rounded-full border-2 border-indigo-500 overflow-hidden bg-slate-100 flex items-center justify-center mb-6">
                {form.avatar_url ? (
                  <img
                    src={form.avatar_url}
                    alt="Profile Avatar"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "https://api.dicebear.com/7.x/adventurer/svg?seed=Priya";
                    }}
                  />
                ) : (
                  <span className="text-slate-400 text-xs">No Image</span>
                )}
              </div>

              {/* Avatar options grid */}
              <div className="grid grid-cols-3 gap-2 mb-4 w-full">
                {MOCK_AVATARS.map((url, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, avatar_url: url }))}
                    className={`p-1 rounded-xl border-2 transition-all overflow-hidden aspect-square flex items-center justify-center bg-slate-50 ${
                      form.avatar_url === url
                        ? "border-indigo-600 ring-1 ring-indigo-100 bg-indigo-50/50"
                        : "border-slate-100 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <img src={url} alt={`Option ${i + 1}`} className="w-full h-full object-contain" />
                  </button>
                ))}
              </div>

              <div className="w-full space-y-1">
                <label htmlFor="custom-avatar-input" className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Custom Image URL</label>
                <input
                  id="custom-avatar-input"
                  type="text"
                  placeholder="https://example.com/avatar.png"
                  value={form.avatar_url}
                  onChange={(e) => setForm((f) => ({ ...f, avatar_url: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
            </div>

            {/* Instagram Connection Card */}
            <div className={`rounded-3xl border p-6 space-y-4 ${
              user?.instagram_connected
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
                  {profile?.instagram_handle && (
                    <div className="flex items-center gap-2 bg-white/70 rounded-xl px-3 py-2">
                      <span className="text-slate-400 text-xs">@</span>
                      <span className="font-semibold text-slate-800 text-sm">{profile.instagram_handle}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-white/70 rounded-xl px-3 py-2.5 text-center">
                      <p className="text-xs text-slate-400">Followers</p>
                      <p className="font-bold text-slate-800 text-sm mt-0.5">
                        {profile?.instagram_followers
                          ? profile.instagram_followers.toLocaleString()
                          : <span className="text-slate-300">—</span>}
                      </p>
                    </div>
                    <div className="bg-white/70 rounded-xl px-3 py-2.5 text-center">
                      <p className="text-xs text-slate-400">Engagement</p>
                      <p className="font-bold text-slate-800 text-sm mt-0.5">
                        {profile?.instagram_engagement_rate
                          ? `${profile.instagram_engagement_rate}%`
                          : <span className="text-slate-300">—</span>}
                      </p>
                    </div>
                  </div>

                  {syncError ? (
                    <div className="bg-red-50 border border-red-100 rounded-xl p-3 space-y-2">
                      <p className="text-xs text-red-600 flex items-start gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
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
                    Connect your Instagram so brands can see your real follower count and engagement metrics.
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
          </div>

          {/* Right Column: Profile Form Details */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white border border-slate-100 shadow-sm rounded-3xl p-8 space-y-6">
              <h2 className="font-outfit text-lg font-bold text-slate-800 border-b border-slate-50 pb-4">
                Creator Details
              </h2>

              <div className="space-y-4">
                {/* Display Name */}
                <div className="space-y-1.5">
                  <label htmlFor="display-name" className="text-sm font-semibold text-slate-700">Display Name</label>
                  <input
                    id="display-name"
                    type="text"
                    required
                    value={form.display_name}
                    onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>

                {/* Bio */}
                <div className="space-y-1.5">
                  <label htmlFor="bio" className="text-sm font-semibold text-slate-700">Bio</label>
                  <textarea
                    id="bio"
                    rows={4}
                    value={form.bio}
                    onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
                    placeholder="Tell brands about your channel, content style, or target audience..."
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
                  />
                </div>

                {/* Location Grid */}
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-semibold text-slate-700">Location</span>
                    <button
                      type="button"
                      onClick={detectLocation}
                      disabled={isDetectingLocation}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-100 bg-indigo-50/50 hover:bg-indigo-50 text-indigo-600 text-xs font-semibold transition-colors disabled:opacity-75"
                    >
                      {isDetectingLocation ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <MapPin className="w-3.5 h-3.5" />
                      )}
                      Detect via GPS
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label htmlFor="edit-state" className="text-sm font-semibold text-slate-700">State / UT</label>
                      <select
                        id="edit-state"
                        value={form.state}
                        onChange={(e) => setForm((f) => ({ ...f, state: e.target.value, city: "" }))}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
                      >
                        <option value="">Select state</option>
                        {INDIA_STATES_AND_DISTRICTS.map((s) => (
                          <option key={s.state} value={s.state}>{s.state}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label htmlFor="edit-city" className="text-sm font-semibold text-slate-700">District</label>
                      <select
                        id="edit-city"
                        value={form.city}
                        onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
                        disabled={!form.state}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white disabled:opacity-60 disabled:bg-slate-50"
                      >
                        <option value="">Select district</option>
                        {getDistrictsForState(form.state).map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Niches */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">Niches (Select up to 5)</label>
                  <div className="flex flex-wrap gap-2">
                    {NICHES.map((n) => {
                      const active = form.niches.includes(n);
                      return (
                        <button
                          key={n}
                          type="button"
                          onClick={() =>
                            setForm((f) => ({
                              ...f,
                              niches: !active && f.niches.length >= 5 ? f.niches : toggle(f.niches, n),
                            }))
                          }
                          className={`px-3.5 py-2 rounded-full text-xs font-medium transition-colors ${
                            active
                              ? "bg-indigo-600 text-white shadow-sm shadow-indigo-100"
                              : "bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200"
                          }`}
                        >
                          {n}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Collab Types */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-700">Collaboration Preferences</label>
                  <div className="flex flex-wrap gap-2">
                    {COLLAB_TYPES.map((c) => {
                      const active = form.collab_types.includes(c);
                      return (
                        <button
                          key={c}
                          type="button"
                          onClick={() => setForm((f) => ({ ...f, collab_types: toggle(f.collab_types, c) }))}
                          className={`px-3.5 py-2 rounded-full text-xs font-medium transition-colors ${
                            active
                              ? "bg-indigo-600 text-white shadow-sm shadow-indigo-100"
                              : "bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200"
                          }`}
                        >
                          {c}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Rates Card Info */}
                <div className="space-y-2 border-t border-slate-50 pt-4">
                  <label className="text-sm font-semibold text-slate-700">Fee Rate Range (INR)</label>
                  <p className="text-xs text-slate-400">Estimate your fee range per deliverable. Leave empty if you prefer to negotiate.</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label htmlFor="rate-min-input" className="text-xs font-medium text-slate-500">Min Rate (₹)</label>
                      <input
                        id="rate-min-input"
                        type="number"
                        placeholder="e.g. 5000"
                        value={form.rate_min}
                        onChange={(e) => setForm((f) => ({ ...f, rate_min: e.target.value }))}
                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      />
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="rate-max-input" className="text-xs font-medium text-slate-500">Max Rate (₹)</label>
                      <input
                        id="rate-max-input"
                        type="number"
                        placeholder="e.g. 25000"
                        value={form.rate_max}
                        onChange={(e) => setForm((f) => ({ ...f, rate_max: e.target.value }))}
                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-3 pt-6 border-t border-slate-100">
                <Button
                  type="submit"
                  disabled={isSaving}
                  className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-6 h-11 rounded-xl transition-colors shadow-sm disabled:opacity-70"
                >
                  {isSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save Changes
                </Button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
