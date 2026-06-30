// ─────────────────────────────────────────────────────────────
// Nexus — Shared TypeScript Types
// Mirror the backend Pydantic schemas
// ─────────────────────────────────────────────────────────────

export type UserRole = "creator" | "brand" | "admin";

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  role: UserRole;
  onboarding_complete: boolean;
  instagram_connected: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ─── Creator Profile ─────────────────────────────────────────

export type NicheCategory =
  | "Food" | "Fitness" | "Fashion" | "Beauty" | "Technology"
  | "Travel" | "Lifestyle" | "Gaming" | "Education" | "Finance"
  | "Parenting" | "Music" | "Comedy" | "Health" | "Automotive"
  | "Real Estate" | "Other";

export type FollowerTier = "nano" | "micro" | "mid" | "macro";

export type CollabType =
  | "Paid Post" | "Product Seeding" | "Long-term Ambassador"
  | "Barter" | "Affiliate" | "Event Coverage";

export interface CreatorProfile {
  id: string;
  user_id: string;
  display_name: string;
  bio: string | null;
  city: string | null;
  state: string | null;
  country: string;
  niches: NicheCategory[];
  collab_types: CollabType[];
  rate_min: number | null;
  rate_max: number | null;
  instagram_handle: string | null;
  instagram_followers: number;
  instagram_engagement_rate: number;
  instagram_profile_pic_url: string | null;
  instagram_category: string | null;
  follower_tier: FollowerTier | null;
  open_to_collabs: boolean;
  is_featured: boolean;
  profile_views: number;
  total_connections: number;
  instagram_last_synced: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreatorProfileFormData {
  display_name: string;
  bio: string;
  city: string;
  state: string;
  niches: NicheCategory[];
  collab_types: CollabType[];
  rate_min: number | null;
  rate_max: number | null;
  avatar_url?: string;
}

// ─── Brand Profile ────────────────────────────────────────────

export type BrandCategory =
  | "Food & Beverage" | "Fitness & Wellness" | "Fashion & Apparel"
  | "Beauty & Skincare" | "Technology" | "Education"
  | "Travel & Hospitality" | "Home & Decor" | "Health & Pharma"
  | "Finance" | "Automotive" | "Real Estate" | "Retail"
  | "E-Commerce / D2C" | "Entertainment" | "Non-Profit / NGO" | "Other";

export interface BrandProfile {
  id: string;
  user_id: string;
  business_name: string;
  tagline: string | null;
  description: string | null;
  logo_url: string | null;
  category: BrandCategory | null;
  website_url: string | null;
  instagram_handle: string | null;
  city: string | null;
  state: string | null;
  country: string;
  total_connections: number;
  total_campaigns_posted: number;
  created_at: string;
  updated_at: string;
}

export interface BrandProfileFormData {
  business_name: string;
  tagline: string;
  description: string;
  category: BrandCategory | null;
  website_url: string;
  city: string;
  state: string;
}

// ─── Campaign ────────────────────────────────────────────────

export type CampaignStatus = "open" | "paused" | "closed";
export type DeliverableType =
  | "Instagram Reel" | "Instagram Post" | "Instagram Story"
  | "Instagram Reel + Stories" | "YouTube Short" | "YouTube Video"
  | "Blog Post" | "Podcast Mention" | "Other";

export interface Campaign {
  id: string;
  brand_id: string;
  title: string;
  description: string;
  deliverable_type: DeliverableType;
  budget_min: number | null;
  budget_max: number | null;
  target_niches: NicheCategory[];
  target_city: string | null;
  target_state: string | null;
  pan_india: boolean;
  interested_count: number;
  status: CampaignStatus;
  created_at: string;
  updated_at: string;
}

// ─── Connection ───────────────────────────────────────────────

export type ConnectionStatus = "pending" | "accepted" | "declined" | "blocked";

export interface Connection {
  id: string;
  requester_id: string;
  requester_profile_id: string;
  recipient_id: string;
  recipient_profile_id: string;
  status: ConnectionStatus;
  campaign_id: string | null;
  created_at: string;
  accepted_at: string | null;
}

// ─── Notification ─────────────────────────────────────────────

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  action_url: string | null;
  created_at: string;
}

// ─── API Responses ────────────────────────────────────────────

export interface PaginatedResponse<T> {
  results: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface ApiError {
  detail: string;
}
