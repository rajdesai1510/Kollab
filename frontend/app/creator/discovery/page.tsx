"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, SlidersHorizontal } from "lucide-react";
import { formatINR } from "@/lib/utils";
import type { NicheCategory, Campaign } from "@/types";

const NICHES: NicheCategory[] = [
  "Food", "Fitness", "Fashion", "Beauty", "Technology",
  "Travel", "Lifestyle", "Gaming", "Education", "Finance", "Other",
];

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const [interested, setInterested] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleInterest = async () => {
    setLoading(true);
    try {
      await api.campaigns.expressInterest(campaign.id);
      setInterested(true);
    } catch {
      // show toast in a real app
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-800 leading-tight">
            {campaign.title}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            {campaign.target_city
              ? `${campaign.target_city}${campaign.target_state ? `, ${campaign.target_state}` : ""}`
              : campaign.pan_india
              ? "Pan India"
              : "Remote"}
          </p>
        </div>
        <Badge variant="secondary" className="text-xs shrink-0">
          {campaign.deliverable_type}
        </Badge>
      </div>

      <p className="text-sm text-slate-500 line-clamp-2">{campaign.description}</p>

      <div className="flex flex-wrap gap-1.5">
        {campaign.target_niches.map((n) => (
          <span key={n} className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
            {n}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between pt-1">
        <div>
          {(campaign.budget_min || campaign.budget_max) && (
            <p className="text-sm font-medium text-slate-700">
              {campaign.budget_min && campaign.budget_max
                ? `${formatINR(campaign.budget_min)} – ${formatINR(campaign.budget_max)}`
                : campaign.budget_min
                ? `From ${formatINR(campaign.budget_min)}`
                : `Up to ${formatINR(campaign.budget_max!)}`}
            </p>
          )}
          <p className="text-xs text-slate-400">
            {campaign.interested_count} interested
          </p>
        </div>
        <Button
          size="sm"
          disabled={loading || interested}
          onClick={handleInterest}
          variant={interested ? "secondary" : "default"}
        >
          {interested ? "✓ Interested" : loading ? "…" : "I'm interested"}
        </Button>
      </div>
    </div>
  );
}

export default function CreatorDiscoveryPage() {
  const [selectedNiches, setSelectedNiches] = useState<NicheCategory[]>([]);
  const [city, setCity] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["campaigns", selectedNiches, city, page],
    queryFn: () =>
      api.campaigns.list({
        status: "open",
        page,
        limit: 12,
      }),
    retry: false,
  });

  const toggleNiche = (n: NicheCategory) =>
    setSelectedNiches((prev) =>
      prev.includes(n) ? prev.filter((x) => x !== n) : [...prev, n]
    );

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-800">
            Find Campaigns
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Browse open briefs from brands — express interest in the ones that
            fit.
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-4">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <SlidersHorizontal className="w-4 h-4" />
            Filters
          </div>

          {/* City search */}
          <div className="relative max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Filter by city…"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Niche chips */}
          <div className="flex flex-wrap gap-2">
            {NICHES.map((n) => {
              const active = selectedNiches.includes(n);
              return (
                <button
                  key={n}
                  onClick={() => toggleNiche(n)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    active
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {n}
                </button>
              );
            })}
          </div>
        </div>

        {/* Results */}
        {isLoading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-52 rounded-2xl" />
            ))}
          </div>
        ) : data?.results.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <p className="font-outfit text-xl font-semibold text-slate-600 mb-2">
              No campaigns yet
            </p>
            <p className="text-sm">Check back soon — brands are posting briefs!</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.results.map((c) => (
              <CampaignCard key={c.id} campaign={c} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {data && data.total > 12 && (
          <div className="flex justify-center gap-2 pt-4">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="px-4 py-2 text-sm text-slate-500">
              Page {page} of {Math.ceil(data.total / 12)}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.has_more}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </AppShell>
  );
}
