"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Loader2, ArrowRight, ArrowLeft, MapPin } from "lucide-react";
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

const RATE_TIERS = [
  { label: "Less than ₹5,000", min: 0, max: 5000 },
  { label: "₹5,000 - ₹10,000", min: 5000, max: 10000 },
  { label: "₹10,000 - ₹25,000", min: 10000, max: 25000 },
  { label: "₹25,000 - ₹50,000", min: 25000, max: 50000 },
  { label: "₹50,000+", min: 50000, max: null },
  { label: "I prefer to negotiate", min: null, max: null },
];

const MOCK_AVATARS = [
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Priya",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Raj",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Ananya",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Kabir",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Diya",
  "https://api.dicebear.com/7.x/adventurer/svg?seed=Arjun",
];

export default function CreatorDetailsWizard() {
  const router = useRouter();
  const { refreshUser, user } = useAuth();
  
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isDetectingLocation, setIsDetectingLocation] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    avatar_url: "",
    niches: [] as NicheCategory[],
    collab_types: [] as CollabType[],
    state: "",
    city: "",
    rateTier: null as number | null,
  });

  useEffect(() => {
    if (user?.avatar_url && !form.avatar_url) {
      setForm((f) => ({ ...f, avatar_url: user.avatar_url ?? "" }));
    }
  }, [user, form.avatar_url]);

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }
    setIsDetectingLocation(true);
    setError("");
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

  const toggle = <T extends string>(arr: T[], val: T): T[] =>
    arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val];

  const validateStep = (currentStep: number): boolean => {
    setError("");
    if (currentStep === 1) {
      if (!form.avatar_url.trim()) {
        setError("Profile picture is mandatory. Please select one or enter a custom URL.");
        return false;
      }
    } else if (currentStep === 2) {
      if (form.niches.length === 0) {
        setError("Please pick at least one niche.");
        return false;
      }
      if (form.niches.length > 5) {
        setError("You can only pick up to 5 niches.");
        return false;
      }
    } else if (currentStep === 3) {
      // Collab types are optional
    } else if (currentStep === 4) {
      if (!form.state) {
        setError("Please select a state.");
        return false;
      }
      if (!form.city.trim()) {
        setError("Please enter your city.");
        return false;
      }
      if (form.city.length > 100) {
        setError("City name is too long.");
        return false;
      }
    } else if (currentStep === 5) {
      if (form.rateTier === null) {
        setError("Please select a rate tier.");
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep((s) => s + 1);
    }
  };

  const handleBack = () => {
    setError("");
    setStep((s) => Math.max(1, s - 1));
  };

  const handleSubmit = async () => {
    if (!validateStep(5)) return;
    
    setIsLoading(true);
    setError("");
    try {
      const selectedTier = form.rateTier !== null ? RATE_TIERS[form.rateTier] : null;
      
      await api.creators.updateProfile({
        avatar_url: form.avatar_url,
        city: form.city,
        state: form.state,
        niches: form.niches,
        collab_types: form.collab_types,
        rate_min: selectedTier?.min !== null ? selectedTier?.min : null,
        rate_max: selectedTier?.max !== null ? selectedTier?.max : null,
      });
      await refreshUser();
      router.push("/creator/dashboard");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  const progress = (step / 5) * 100;

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-6 flex flex-col items-center">
      <div className="max-w-xl w-full">
        {/* Header & Progress */}
        <div className="text-center mb-10">
          <span className="font-outfit font-bold text-2xl text-slate-800">
            Nex<span className="text-indigo-600">us</span>
          </span>
          <h2 className="font-outfit text-2xl font-semibold text-slate-800 mt-6 mb-4">
            {step === 1 && "Choose your profile picture"}
            {step === 2 && "What do you create?"}
            {step === 3 && "How do you collaborate?"}
            {step === 4 && "Where are you based?"}
            {step === 5 && "Set your rates"}
          </h2>
          
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden max-w-xs mx-auto">
            <div 
              className="bg-indigo-600 h-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-slate-400 text-xs mt-3 font-medium tracking-wide uppercase">
            Step {step} of 5
          </p>
        </div>

        {/* Wizard Card */}
        <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-8">
          
          {/* STEP 1: Avatar Selection */}
          {step === 1 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
              <p className="text-sm text-slate-500 mb-2">
                A profile picture is required. Pick one of our pre-made avatars or enter a custom image URL.
              </p>
              
              {/* Selected Avatar Preview */}
              <div className="flex flex-col items-center gap-2 mb-6">
                <div className="w-24 h-24 rounded-full border-2 border-indigo-500 overflow-hidden bg-slate-100 flex items-center justify-center">
                  {form.avatar_url ? (
                    <img 
                      src={form.avatar_url} 
                      alt="Selected Profile" 
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "https://api.dicebear.com/7.x/adventurer/svg?seed=Priya";
                      }}
                    />
                  ) : (
                    <span className="text-slate-400 text-xs text-center px-2">No Image</span>
                  )}
                </div>
                <span className="text-xs text-slate-400 font-medium">Selected Preview</span>
              </div>

              {/* Avatar Options Grid */}
              <div className="grid grid-cols-3 gap-3">
                {MOCK_AVATARS.map((url, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, avatar_url: url }))}
                    className={`p-1.5 rounded-2xl border-2 transition-all overflow-hidden aspect-square flex items-center justify-center bg-slate-50 ${
                      form.avatar_url === url 
                        ? "border-indigo-600 ring-2 ring-indigo-100 bg-indigo-50/50" 
                        : "border-slate-100 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <img src={url} alt={`Avatar option ${i + 1}`} className="w-full h-full object-contain" />
                  </button>
                ))}
              </div>

              {/* Custom URL Input */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <label htmlFor="custom-avatar" className="text-sm font-medium text-slate-700">Or use a custom image URL</label>
                <input
                  id="custom-avatar"
                  type="text"
                  placeholder="https://example.com/my-photo.jpg"
                  value={form.avatar_url}
                  onChange={(e) => setForm((f) => ({ ...f, avatar_url: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
            </div>
          )}
          
          {/* STEP 2: Niches */}
          {step === 2 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
              <p className="text-sm text-slate-500 mb-2">
                Pick up to 5 categories that best describe your content.
              </p>
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
                      className={`px-4 py-2.5 rounded-full text-sm font-medium transition-colors ${
                        active
                          ? "bg-indigo-600 text-white shadow-sm shadow-indigo-200"
                          : "bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200"
                      }`}
                    >
                      {n}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* STEP 3: Collab Types */}
          {step === 3 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
              <p className="text-sm text-slate-500 mb-2">
                What kind of brand deals are you open to? (Select all that apply)
              </p>
              <div className="flex flex-wrap gap-2">
                {COLLAB_TYPES.map((c) => {
                  const active = form.collab_types.includes(c);
                  return (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, collab_types: toggle(f.collab_types, c) }))}
                      className={`px-4 py-2.5 rounded-full text-sm font-medium transition-colors ${
                        active
                          ? "bg-indigo-600 text-white shadow-sm shadow-indigo-200"
                          : "bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200"
                      }`}
                    >
                      {c}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* STEP 4: Location */}
          {step === 4 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={detectLocation}
                  disabled={isDetectingLocation}
                  className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-indigo-100 bg-indigo-50/50 hover:bg-indigo-50 text-indigo-600 text-xs font-semibold transition-colors disabled:opacity-75"
                >
                  {isDetectingLocation ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <MapPin className="w-3.5 h-3.5" />
                  )}
                  Detect Location via GPS
                </button>
              </div>
              <div className="space-y-2">
                <label htmlFor="state" className="text-sm font-medium text-slate-700">State / UT</label>
                <select
                  id="state"
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
              <div className="space-y-2">
                <label htmlFor="city" className="text-sm font-medium text-slate-700">District</label>
                <select
                  id="city"
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
          )}

          {/* STEP 5: Rates */}
          {step === 5 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
              <p className="text-sm text-slate-500 mb-2">
                What is your typical rate per deliverable? This helps brands find creators in their budget.
              </p>
              <div className="space-y-3">
                {RATE_TIERS.map((tier, index) => (
                  <button
                    key={index}
                    onClick={() => setForm(f => ({ ...f, rateTier: index }))}
                    className={`w-full text-left px-4 py-4 rounded-xl border text-sm font-medium transition-all ${
                      form.rateTier === index 
                      ? "border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    {tier.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-6 p-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-600">
              {error}
            </div>
          )}

          {/* Navigation Controls */}
          <div className="flex items-center justify-between mt-10 pt-6 border-t border-slate-100">
            {step > 1 ? (
              <button type="button" onClick={handleBack} className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-700 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
            ) : (
              <div /> // Placeholder for flex spacing
            )}
            
            {step < 5 ? (
              <button 
                type="button" 
                onClick={handleNext} 
                className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium px-6 py-2.5 rounded-lg transition-colors shadow-sm"
              >
                Next <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-8 py-2.5 rounded-lg transition-colors shadow-sm disabled:opacity-70"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Complete Setup"}
              </button>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
