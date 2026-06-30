"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Loader2, Plus, X, FileText } from "lucide-react";
import type { DeliverableType, NicheCategory } from "@/types";

const DELIVERABLE_TYPES: DeliverableType[] = [
  "Instagram Reel", "Instagram Post", "Instagram Story",
  "Instagram Reel + Stories", "YouTube Short", "YouTube Video",
  "Blog Post", "Other",
];

const NICHES: NicheCategory[] = [
  "Food", "Fitness", "Fashion", "Beauty", "Technology",
  "Travel", "Lifestyle", "Gaming", "Education", "Finance", "Other",
];

function NewCampaignForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "",
    description: "",
    deliverable_type: "" as DeliverableType | "",
    budget_min: "",
    budget_max: "",
    target_niches: [] as NicheCategory[],
    target_city: "",
    pan_india: false,
  });

  const toggle = <T extends string>(arr: T[], val: T): T[] =>
    arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || form.title.length < 10) {
      setError("Title must be at least 10 characters.");
      return;
    }
    if (!form.description.trim() || form.description.length < 30) {
      setError("Description must be at least 30 characters.");
      return;
    }
    if (!form.deliverable_type) {
      setError("Select a deliverable type.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      // Brand profile is needed — get it first
      const profile = await api.brands.getProfile();
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/campaigns/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("cs_access_token")}`,
        },
        body: JSON.stringify({
          title: form.title,
          description: form.description,
          deliverable_type: form.deliverable_type,
          budget_min: form.budget_min ? parseInt(form.budget_min) : null,
          budget_max: form.budget_max ? parseInt(form.budget_max) : null,
          target_niches: form.target_niches,
          target_city: form.target_city || null,
          pan_india: form.pan_india,
        }),
      });
      queryClient.invalidateQueries({ queryKey: ["my-campaigns"] });
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-outfit text-lg font-semibold text-slate-800">
            Post a campaign
          </h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100">
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="title">Campaign title *</Label>
            <Input
              id="title"
              placeholder="e.g. Looking for fitness creators in Mumbai"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="desc">Brief description *</Label>
            <textarea
              id="desc"
              rows={4}
              placeholder="Describe your brand, what content you need, and what you're offering…"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Deliverable type *</Label>
            <div className="flex flex-wrap gap-2">
              {DELIVERABLE_TYPES.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, deliverable_type: d }))}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    form.deliverable_type === d
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="bmin">Min budget (₹)</Label>
              <Input id="bmin" type="number" placeholder="5000"
                value={form.budget_min}
                onChange={(e) => setForm((f) => ({ ...f, budget_min: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="bmax">Max budget (₹)</Label>
              <Input id="bmax" type="number" placeholder="20000"
                value={form.budget_max}
                onChange={(e) => setForm((f) => ({ ...f, budget_max: e.target.value }))} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Target niches</Label>
            <div className="flex flex-wrap gap-2">
              {NICHES.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() =>
                    setForm((f) => ({
                      ...f,
                      target_niches: toggle(f.target_niches, n),
                    }))
                  }
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    form.target_niches.includes(n)
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="city">Target city</Label>
            <Input id="city" placeholder="e.g. Delhi (leave empty for pan-India)"
              value={form.target_city}
              onChange={(e) => setForm((f) => ({ ...f, target_city: e.target.value }))} />
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.pan_india}
              onChange={(e) => setForm((f) => ({ ...f, pan_india: e.target.checked }))}
              className="w-4 h-4 accent-indigo-600"
            />
            <span className="text-sm text-slate-700">Open to creators from anywhere in India</span>
          </label>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex gap-3 pt-1">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading} className="flex-1">
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Post campaign"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function BrandCampaignsPage() {
  const [showNew, setShowNew] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["my-campaigns"],
    queryFn: () => api.campaigns.list({ limit: 20 }),
    retry: false,
  });

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-outfit text-2xl font-bold text-slate-800">Campaigns</h1>
            <p className="text-slate-500 text-sm mt-1">Manage your briefs and see who's interested.</p>
          </div>
          <Button onClick={() => setShowNew(true)} className="gap-2">
            <Plus className="w-4 h-4" />
            New campaign
          </Button>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}
          </div>
        ) : data?.results.length === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-slate-200 py-16 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-600 mb-1">No campaigns yet</p>
            <p className="text-xs text-slate-400 mb-5">
              Post a brief so creators can express interest.
            </p>
            <Button size="sm" onClick={() => setShowNew(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              Post your first campaign
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {data?.results.map((c) => (
              <div
                key={c.id}
                className="bg-white rounded-2xl border border-slate-100 shadow-sm px-5 py-4 flex items-center gap-4"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">{c.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {c.deliverable_type} · {c.interested_count} interested ·{" "}
                    {new Date(c.created_at).toLocaleDateString("en-IN")}
                  </p>
                </div>
                <Badge
                  variant={c.status === "open" ? "default" : "secondary"}
                  className="text-xs capitalize shrink-0"
                >
                  {c.status}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </div>

      {showNew && <NewCampaignForm onClose={() => setShowNew(false)} />}
    </AppShell>
  );
}
