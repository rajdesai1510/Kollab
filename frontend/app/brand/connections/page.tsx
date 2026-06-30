"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, MessageCircle } from "lucide-react";
import Link from "next/link";

export default function BrandConnectionsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["connections"],
    queryFn: () => api.connections.list(),
    retry: false,
  });

  const pending = data?.pending ?? [];
  const accepted = data?.accepted ?? [];

  return (
    <AppShell>
      <div className="space-y-8">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-800">
            Connections
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Track outgoing requests and active creator relationships.
          </p>
        </div>

        {/* Pending */}
        <section>
          <h2 className="font-outfit text-lg font-semibold text-slate-800 mb-4">
            Awaiting response{" "}
            {pending.length > 0 && (
              <span className="text-sm font-normal text-slate-400">
                ({pending.length})
              </span>
            )}
          </h2>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => <Skeleton key={i} className="h-16 rounded-2xl" />)}
            </div>
          ) : pending.length === 0 ? (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 py-10 text-center">
              <p className="text-sm text-slate-400">No pending requests</p>
            </div>
          ) : (
            <div className="space-y-2">
              {pending.map((c) => (
                <div
                  key={c.id}
                  className="bg-white rounded-2xl border border-slate-100 shadow-sm px-5 py-4 flex items-center gap-4"
                >
                  <Avatar className="w-10 h-10 shrink-0">
                    <AvatarFallback className="bg-slate-100 text-slate-600 text-sm font-semibold">
                      {c.recipient_profile_id.slice(-2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800">
                      Creator #{c.recipient_profile_id.slice(-6)}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Sent {new Date(c.created_at).toLocaleDateString("en-IN")}
                    </p>
                  </div>
                  <Badge variant="secondary" className="text-xs">Pending</Badge>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Active */}
        <section>
          <h2 className="font-outfit text-lg font-semibold text-slate-800 mb-4">
            Active collaborations{" "}
            {accepted.length > 0 && (
              <span className="text-sm font-normal text-slate-400">
                ({accepted.length})
              </span>
            )}
          </h2>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 rounded-2xl" />)}
            </div>
          ) : accepted.length === 0 ? (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 py-10 text-center">
              <Users className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-600 mb-1">
                No active connections yet
              </p>
              <p className="text-xs text-slate-400 mb-4">
                Request a creator first.
              </p>
              <Link href="/brand/discover">
                <Button size="sm">Find creators</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {accepted.map((c) => (
                <div
                  key={c.id}
                  className="bg-white rounded-2xl border border-slate-100 shadow-sm px-5 py-4 flex items-center gap-4"
                >
                  <Avatar className="w-10 h-10 shrink-0">
                    <AvatarFallback className="bg-indigo-100 text-indigo-700 text-sm font-semibold">
                      {c.recipient_profile_id.slice(-2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800">
                      Creator #{c.recipient_profile_id.slice(-6)}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Connected {c.accepted_at
                        ? new Date(c.accepted_at).toLocaleDateString("en-IN")
                        : "—"}
                    </p>
                  </div>
                  <Badge className="text-xs">Active</Badge>
                  <Button size="sm" variant="outline" className="gap-1.5 shrink-0">
                    <MessageCircle className="w-3.5 h-3.5" />
                    Chat
                  </Button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
