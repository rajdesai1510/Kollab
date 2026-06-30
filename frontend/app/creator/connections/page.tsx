"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, MessageCircle } from "lucide-react";
import type { Connection } from "@/types";

function ConnectionRow({
  conn,
  onAccept,
  onDecline,
}: {
  conn: Connection;
  onAccept?: (id: string) => void;
  onDecline?: (id: string) => void;
}) {
  const initials = conn.requester_id.slice(0, 2).toUpperCase();
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm px-5 py-4 flex items-center gap-4">
      <Avatar className="w-10 h-10 shrink-0">
        <AvatarFallback className="bg-indigo-100 text-indigo-700 text-sm font-semibold">
          {initials}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">
          Brand #{conn.requester_profile_id.slice(-6)}
        </p>
        <p className="text-xs text-slate-400 mt-0.5">
          {new Date(conn.created_at).toLocaleDateString("en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </p>
      </div>
      <Badge
        variant={
          conn.status === "accepted"
            ? "default"
            : conn.status === "pending"
            ? "secondary"
            : "outline"
        }
        className="text-xs capitalize"
      >
        {conn.status}
      </Badge>
      {conn.status === "pending" && onAccept && onDecline && (
        <div className="flex gap-2 shrink-0">
          <Button size="sm" variant="outline" onClick={() => onDecline(conn.id)}>
            Decline
          </Button>
          <Button size="sm" onClick={() => onAccept(conn.id)}>
            Accept
          </Button>
        </div>
      )}
      {conn.status === "accepted" && (
        <Button size="sm" variant="outline" className="gap-1.5 shrink-0">
          <MessageCircle className="w-3.5 h-3.5" />
          Chat
        </Button>
      )}
    </div>
  );
}

export default function CreatorConnectionsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["connections"],
    queryFn: () => api.connections.list(),
    retry: false,
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => api.connections.accept(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connections"] }),
  });

  const declineMutation = useMutation({
    mutationFn: (id: string) => api.connections.decline(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connections"] }),
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
            Manage brand requests and active collaborations.
          </p>
        </div>

        {/* Pending requests */}
        <section>
          <h2 className="font-outfit text-lg font-semibold text-slate-800 mb-4">
            Pending requests{" "}
            {pending.length > 0 && (
              <span className="text-sm font-normal text-slate-400">
                ({pending.length})
              </span>
            )}
          </h2>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <Skeleton key={i} className="h-16 rounded-2xl" />
              ))}
            </div>
          ) : pending.length === 0 ? (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 py-10 text-center">
              <p className="text-sm text-slate-400">No pending requests</p>
            </div>
          ) : (
            <div className="space-y-2">
              {pending.map((c) => (
                <ConnectionRow
                  key={c.id}
                  conn={c}
                  onAccept={(id) => acceptMutation.mutate(id)}
                  onDecline={(id) => declineMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Active connections */}
        <section>
          <h2 className="font-outfit text-lg font-semibold text-slate-800 mb-4">
            Active connections{" "}
            {accepted.length > 0 && (
              <span className="text-sm font-normal text-slate-400">
                ({accepted.length})
              </span>
            )}
          </h2>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 rounded-2xl" />
              ))}
            </div>
          ) : accepted.length === 0 ? (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 py-10 text-center">
              <Users className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-600 mb-1">
                No active connections yet
              </p>
              <p className="text-xs text-slate-400">
                Accept a brand request to unlock in-platform chat.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {accepted.map((c) => (
                <ConnectionRow key={c.id} conn={c} />
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
