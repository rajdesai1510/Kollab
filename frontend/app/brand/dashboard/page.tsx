"use client";

import { AppShell } from "@/components/layout/AppShell";
import { StatCard } from "@/components/shared/StatCard";
import { useAuth } from "@/lib/auth-context";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Search, Plus, FileText } from "lucide-react";

export default function BrandDashboardPage() {
  const { user } = useAuth();

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["brand-profile"],
    queryFn: () => api.brands.getProfile(),
    enabled: !!user,
    retry: false,
  });

  const { data: campaigns, isLoading: campaignsLoading } = useQuery({
    queryKey: ["my-campaigns"],
    queryFn: () => api.campaigns.list({ limit: 5 }),
    enabled: !!user,
    retry: false,
  });

  const { data: connections } = useQuery({
    queryKey: ["connections"],
    queryFn: () => api.connections.list(),
    enabled: !!user,
    retry: false,
  });

  const firstName = user?.name?.split(" ")[0] ?? "there";

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Greeting */}
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-800">
            Hey, {firstName} 👋
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {profile?.business_name
              ? `Welcome back to ${profile.business_name}.`
              : "Let's find your next creator."}
          </p>
        </div>

        {/* Stats */}
        {profileLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 rounded-2xl" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <StatCard
              label="Total connections"
              value={profile?.total_connections ?? 0}
              sub="Accepted"
              accent
            />
            <StatCard
              label="Campaigns posted"
              value={profile?.total_campaigns_posted ?? 0}
              sub="All time"
            />
            <StatCard
              label="Pending requests"
              value={connections?.pending?.length ?? 0}
              sub="Awaiting creator response"
            />
          </div>
        )}

        {/* Quick actions */}
        <div>
          <h2 className="font-outfit text-lg font-semibold text-slate-800 mb-4">
            Quick actions
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            <Link href="/brand/discover">
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex items-center gap-4 hover:shadow-md transition-shadow cursor-pointer group">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                  <Search className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-800">Search creators</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Filter by niche, city, and follower count
                  </p>
                </div>
              </div>
            </Link>
            <Link href="/brand/campaigns/new">
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex items-center gap-4 hover:shadow-md transition-shadow cursor-pointer group">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center group-hover:bg-emerald-100 transition-colors">
                  <Plus className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-800">Post a campaign</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Let creators come to you
                  </p>
                </div>
              </div>
            </Link>
          </div>
        </div>

        {/* Recent campaigns */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-outfit text-lg font-semibold text-slate-800">
              Your campaigns
            </h2>
            <Link href="/brand/campaigns">
              <Button variant="ghost" size="sm" className="text-indigo-600">
                View all
              </Button>
            </Link>
          </div>

          {campaignsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 rounded-xl" />
              ))}
            </div>
          ) : campaigns?.results.length === 0 ? (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 p-8 text-center">
              <FileText className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-600 mb-1">
                No campaigns yet
              </p>
              <p className="text-xs text-slate-400 mb-4">
                Post a brief and let creators reach out to you.
              </p>
              <Link href="/brand/campaigns/new">
                <Button size="sm">Post first campaign</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {campaigns?.results.map((c) => (
                <div
                  key={c.id}
                  className="bg-white rounded-2xl border border-slate-100 shadow-sm px-5 py-4 flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-800">{c.title}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {c.interested_count} interested ·{" "}
                      <span className="capitalize">{c.status}</span>
                    </p>
                  </div>
                  <Link href={`/brand/campaigns/${c.id}`}>
                    <Button variant="ghost" size="sm">View</Button>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
