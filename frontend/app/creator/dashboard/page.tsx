"use client";

import { AppShell } from "@/components/layout/AppShell";
import { StatCard } from "@/components/shared/StatCard";
import { useAuth } from "@/lib/auth-context";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Camera, RefreshCw, Search } from "lucide-react";
import { formatCount, formatEngagement } from "@/lib/utils";

export default function CreatorDashboardPage() {
  const { user } = useAuth();

  const { data: profile, isLoading } = useQuery({
    queryKey: ["creator-profile"],
    queryFn: () => api.creators.getProfile("me"),
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
  const pendingCount = connections?.pending?.length ?? 0;
  const acceptedCount = connections?.accepted?.length ?? 0;

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Greeting */}
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-800">
            Hey, {firstName} 👋
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Here's how your profile is doing.
          </p>
        </div>

        {/* Stat cards */}
        {isLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-28 rounded-2xl" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Followers"
              value={formatCount(profile?.instagram_followers ?? 0)}
              sub="Instagram"
              accent
            />
            <StatCard
              label="Engagement"
              value={formatEngagement(profile?.instagram_engagement_rate ?? 0)}
              sub="Rate"
            />
            <StatCard
              label="Connections"
              value={acceptedCount}
              sub="Accepted"
            />
            <StatCard
              label="Pending"
              value={pendingCount}
              sub="Requests from brands"
            />
          </div>
        )}

        {/* Instagram connect prompt */}
        {!user?.instagram_connected && (
          <div className="bg-gradient-to-r from-pink-50 to-purple-50 rounded-2xl border border-pink-100 p-6 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800 mb-1">
                Connect your Instagram
              </p>
              <p className="text-sm text-slate-500">
                Let brands see your real follower count and engagement rate.
              </p>
            </div>
            <Link href={`${process.env.NEXT_PUBLIC_API_URL}/api/auth/instagram/connect`}>
              <Button className="gap-2 bg-gradient-to-r from-pink-500 to-purple-600 border-0 hover:opacity-90">
                <Camera className="w-4 h-4" />
                Connect
              </Button>
            </Link>
          </div>
        )}

        {/* Quick actions */}
        <div>
          <h2 className="font-outfit text-lg font-semibold text-slate-800 mb-4">
            Quick actions
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            <Link href="/creator/discovery">
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex items-center gap-4 hover:shadow-md transition-shadow cursor-pointer group">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                  <Search className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-800">Browse campaigns</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Find briefs that match your niche
                  </p>
                </div>
              </div>
            </Link>
            <button
              onClick={() => api.creators.syncInstagram()}
              className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex items-center gap-4 hover:shadow-md transition-shadow text-left group"
            >
              <div className="w-10 h-10 rounded-xl bg-pink-50 flex items-center justify-center group-hover:bg-pink-100 transition-colors">
                <RefreshCw className="w-5 h-5 text-pink-600" />
              </div>
              <div>
                <p className="font-medium text-slate-800">Sync Instagram stats</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Update your follower count now
                </p>
              </div>
            </button>
          </div>
        </div>

        {/* Pending connections */}
        {pendingCount > 0 && (
          <div>
            <h2 className="font-outfit text-lg font-semibold text-slate-800 mb-4">
              Brands waiting for you{" "}
              <span className="text-sm font-normal text-slate-400">
                ({pendingCount})
              </span>
            </h2>
            <div className="space-y-2">
              {connections?.pending.map((conn) => (
                <div
                  key={conn.id}
                  className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      Brand request #{conn.id.slice(-6)}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {new Date(conn.created_at).toLocaleDateString("en-IN")}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => api.connections.decline(conn.id)}
                    >
                      Decline
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => api.connections.accept(conn.id)}
                    >
                      Accept
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
