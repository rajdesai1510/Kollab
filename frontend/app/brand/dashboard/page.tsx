"use client";

import { AppShell } from "@/components/layout/AppShell";
import { StatCard } from "@/components/shared/StatCard";
import { useAuth } from "@/lib/auth-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  Search,
  Plus,
  FileText,
  Camera,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import { formatCount, formatEngagement } from "@/lib/utils";

const INSTAGRAM_CONNECT_URL = `${process.env.NEXT_PUBLIC_API_URL}/api/auth/instagram/start`;

export default function BrandDashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

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

  const syncMutation = useMutation({
    mutationFn: () => api.brands.syncInstagram(),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(["brand-profile"], updatedProfile);
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

  const firstName = user?.name?.split(" ")[0] ?? "there";
  const igConnected = user?.instagram_connected;

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

        {/* Instagram status banner */}
        {igConnected ? (
          <div className="bg-gradient-to-r from-pink-50 to-purple-50 border border-pink-100 rounded-2xl px-5 py-4 flex items-center gap-4">
            <div className="w-9 h-9 rounded-xl bg-white flex items-center justify-center shadow-sm shrink-0">
              <Camera className="w-4 h-4 text-pink-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="text-sm font-semibold text-slate-800">Instagram connected</p>
                {profile?.instagram_handle && (
                  <span className="text-xs bg-white/80 text-pink-700 font-medium px-2 py-0.5 rounded-full border border-pink-100">
                    @{profile.instagram_handle}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {profile?.instagram_last_synced
                  ? `Last synced ${new Date(profile.instagram_last_synced).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}`
                  : "Never synced — click Sync to fetch your stats"}
              </p>
            </div>
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="shrink-0 flex items-center gap-1.5 bg-white hover:bg-pink-50 border border-pink-200 text-pink-700 text-xs font-semibold rounded-xl px-3.5 py-2 transition-colors disabled:opacity-60"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
              {syncMutation.isPending ? "Syncing..." : "Sync"}
            </button>
          </div>
        ) : (
          <div className="bg-slate-50 border border-slate-200 rounded-2xl px-5 py-4 flex items-center gap-4">
            <div className="w-9 h-9 rounded-xl bg-white flex items-center justify-center shadow-sm shrink-0 border border-slate-100">
              <Camera className="w-4 h-4 text-slate-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-700">Instagram not connected</p>
              <p className="text-xs text-slate-400 mt-0.5">
                Connect to show your follower count and engagement rate to creators.
              </p>
            </div>
            <a href={INSTAGRAM_CONNECT_URL} className="shrink-0">
              <Button size="sm" className="gap-1.5 bg-gradient-to-r from-pink-500 to-purple-600 border-0 hover:opacity-90 text-xs h-8 px-3.5">
                <Camera className="w-3.5 h-3.5" />
                Connect
              </Button>
            </a>
          </div>
        )}

        {/* Sync success */}
        {syncMutation.isSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-2xl px-5 py-3.5 flex items-center gap-3">
            <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
            <p className="text-sm text-green-700 font-medium">Stats synced successfully!</p>
          </div>
        )}

        {/* Sync error */}
        {syncError && (
          <div className="bg-red-50 border border-red-200 rounded-2xl px-5 py-4 flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-red-700">Instagram sync failed</p>
              <p className="text-xs text-red-500 mt-0.5 break-words">{syncError}</p>
            </div>
            {isTokenError ? (
              <a
                href={INSTAGRAM_CONNECT_URL}
                className="shrink-0 flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-xl px-3 py-1.5 transition-colors"
              >
                <Camera className="w-3 h-3" />
                Reconnect
              </a>
            ) : (
              <button
                onClick={() => syncMutation.mutate()}
                className="shrink-0 text-xs font-semibold text-red-600 hover:text-red-800 underline"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {/* Stats */}
        {profileLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 rounded-2xl" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="IG Followers"
              value={igConnected ? formatCount(profile?.instagram_followers ?? 0) : "—"}
              sub={igConnected ? "Instagram" : "Connect IG"}
              accent={!!igConnected}
            />
            <StatCard
              label="IG Engagement"
              value={igConnected ? formatEngagement(profile?.instagram_engagement_rate ?? 0) : "—"}
              sub={igConnected ? "Rate" : "Connect IG"}
            />
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
                  <p className="text-xs text-slate-400 mt-0.5">Filter by niche, city, and follower count</p>
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
                  <p className="text-xs text-slate-400 mt-0.5">Let creators come to you</p>
                </div>
              </div>
            </Link>
          </div>
        </div>

        {/* Recent campaigns */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-outfit text-lg font-semibold text-slate-800">Your campaigns</h2>
            <Link href="/brand/campaigns">
              <Button variant="ghost" size="sm" className="text-indigo-600">View all</Button>
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
              <p className="text-sm font-medium text-slate-600 mb-1">No campaigns yet</p>
              <p className="text-xs text-slate-400 mb-4">Post a brief and let creators reach out to you.</p>
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
                      {c.interested_count} interested · <span className="capitalize">{c.status}</span>
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