import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MapPin, TrendingUp, Users } from "lucide-react";
import { formatCount, formatEngagement } from "@/lib/utils";
import type { CreatorProfile } from "@/types";

interface CreatorCardProps {
  creator: CreatorProfile;
  onConnect?: (creatorProfileId: string) => void;
  isConnecting?: boolean;
}

export function CreatorCard({ creator, onConnect, isConnecting }: CreatorCardProps) {
  const initials = creator.display_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex flex-col gap-4 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Avatar className="w-12 h-12 shrink-0">
          <AvatarImage src={creator.instagram_profile_pic_url ?? undefined} />
          <AvatarFallback className="text-sm bg-indigo-100 text-indigo-700 font-semibold">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-800 truncate">
            {creator.display_name}
          </p>
          {creator.instagram_handle && (
            <p className="text-xs text-slate-400">@{creator.instagram_handle}</p>
          )}
          {(creator.city || creator.state) && (
            <div className="flex items-center gap-1 mt-1">
              <MapPin className="w-3 h-3 text-slate-400" />
              <span className="text-xs text-slate-400">
                {[creator.city, creator.state].filter(Boolean).join(", ")}
              </span>
            </div>
          )}
        </div>
        {creator.follower_tier && (
          <Badge
            variant="secondary"
            className="text-xs capitalize shrink-0"
          >
            {creator.follower_tier}
          </Badge>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-50 rounded-xl p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Users className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">Followers</span>
          </div>
          <p className="font-outfit font-bold text-slate-800">
            {formatCount(creator.instagram_followers)}
          </p>
        </div>
        <div className="bg-slate-50 rounded-xl p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">Engagement</span>
          </div>
          <p className="font-outfit font-bold text-slate-800">
            {formatEngagement(creator.instagram_engagement_rate)}
          </p>
        </div>
      </div>

      {/* Niches */}
      {creator.niches.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {creator.niches.slice(0, 4).map((n) => (
            <span
              key={n}
              className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full"
            >
              {n}
            </span>
          ))}
          {creator.niches.length > 4 && (
            <span className="text-xs text-slate-400 px-1 py-1">
              +{creator.niches.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Connect button */}
      {onConnect && (
        <Button
          size="sm"
          className="w-full"
          disabled={isConnecting || !creator.open_to_collabs}
          onClick={() => onConnect(creator.id)}
          variant={creator.open_to_collabs ? "default" : "secondary"}
        >
          {!creator.open_to_collabs
            ? "Not available"
            : isConnecting
            ? "Sending…"
            : "Request to connect"}
        </Button>
      )}
    </div>
  );
}
