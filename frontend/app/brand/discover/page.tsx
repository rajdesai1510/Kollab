"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { CreatorCard } from "@/components/creator/CreatorCard";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, SlidersHorizontal } from "lucide-react";
import type { NicheCategory } from "@/types";

const NICHES: NicheCategory[] = [
  "Food", "Fitness", "Fashion", "Beauty", "Technology",
  "Travel", "Lifestyle", "Gaming", "Education", "Finance", "Other",
];

const FOLLOWER_FILTERS = [
  { label: "Any", value: 0 },
  { label: "10K+", value: 10000 },
  { label: "50K+", value: 50000 },
  { label: "100K+", value: 100000 },
];

export default function BrandDiscoverPage() {
  const queryClient = useQueryClient();
  const [city, setCity] = useState("");
  const [selectedNiches, setSelectedNiches] = useState<NicheCategory[]>([]);
  const [minFollowers, setMinFollowers] = useState(0);
  const [page, setPage] = useState(1);
  const [connectingId, setConnectingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["creators-search", city, selectedNiches, minFollowers, page],
    queryFn: () =>
      api.creators.search({
        city: city || undefined,
        niche: selectedNiches[0] || undefined,
        min_followers: minFollowers || undefined,
        page,
        limit: 12,
      }),
    retry: false,
  });

  const connectMutation = useMutation({
    mutationFn: (profileId: string) => api.connections.request(profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connections"] });
    },
  });

  const handleConnect = async (profileId: string) => {
    setConnectingId(profileId);
    try {
      await connectMutation.mutateAsync(profileId);
    } finally {
      setConnectingId(null);
    }
  };

  const toggleNiche = (n: NicheCategory) =>
    setSelectedNiches((prev) =>
      prev.includes(n) ? prev.filter((x) => x !== n) : [n] // single select for simplicity
    );

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-800">
            Discover Creators
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Find the right micro-influencers for your next campaign.
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-4">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <SlidersHorizontal className="w-4 h-4" />
            Filters
          </div>

          {/* City */}
          <div className="relative max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="City (e.g. Mumbai)"
              value={city}
              onChange={(e) => { setCity(e.target.value); setPage(1); }}
              className="pl-9"
            />
          </div>

          {/* Niches */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">Niche</p>
            <div className="flex flex-wrap gap-2">
              {NICHES.map((n) => {
                const active = selectedNiches.includes(n);
                return (
                  <button
                    key={n}
                    onClick={() => { toggleNiche(n); setPage(1); }}
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

          {/* Min followers */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">
              Minimum followers
            </p>
            <div className="flex gap-2 flex-wrap">
              {FOLLOWER_FILTERS.map(({ label, value }) => (
                <button
                  key={label}
                  onClick={() => { setMinFollowers(value); setPage(1); }}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    minFollowers === value
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Creator grid */}
        {isLoading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-64 rounded-2xl" />
            ))}
          </div>
        ) : data?.results.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <p className="font-outfit text-xl font-semibold text-slate-600 mb-2">
              No creators found
            </p>
            <p className="text-sm">
              Try broadening your filters.
            </p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.results.map((creator) => (
              <CreatorCard
                key={creator.id}
                creator={creator}
                onConnect={handleConnect}
                isConnecting={connectingId === creator.id}
              />
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
