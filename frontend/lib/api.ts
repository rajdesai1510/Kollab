/**
 * Nexus — API Client (Class-based)
 *
 * Single class wrapping all backend API calls.
 * Handles: auth headers, silent token refresh on 401, error parsing.
 *
 * Token strategy:
 *   - Access token (60 min)  — stored in localStorage, sent with every request
 *   - Refresh token (30 days) — stored in localStorage, used only to get a new access token
 *   - On 401: automatically call /api/auth/refresh, retry the original request once
 *   - If refresh also fails: clear both tokens, redirect to login
 *
 * Usage:
 *   import { api } from "@/lib/api";
 *   const user = await api.auth.me();
 */

import type {
  AuthTokens,
  BrandProfile,
  BrandProfileFormData,
  Campaign,
  Connection,
  CreatorProfile,
  CreatorProfileFormData,
  Notification,
  PaginatedResponse,
  User,
} from "@/types";

const BASE_URL =
  typeof window !== "undefined"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ─────────────────────────────────────────────────────────────
// Token storage — both access and refresh tokens in localStorage
// ─────────────────────────────────────────────────────────────
const ACCESS_TOKEN_KEY = "cs_access_token";
const REFRESH_TOKEN_KEY = "cs_refresh_token";

export const tokenStore = {
  // Access token
  get: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem(ACCESS_TOKEN_KEY) : null,
  set: (token: string): void => {
    if (typeof window !== "undefined") localStorage.setItem(ACCESS_TOKEN_KEY, token);
  },
  clear: (): void => {
    if (typeof window !== "undefined") localStorage.removeItem(ACCESS_TOKEN_KEY);
  },

  // Refresh token
  getRefresh: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem(REFRESH_TOKEN_KEY) : null,
  setRefresh: (token: string): void => {
    if (typeof window !== "undefined") localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },
  clearRefresh: (): void => {
    if (typeof window !== "undefined") localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  // Clear both
  clearAll: (): void => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  },
};

// ─────────────────────────────────────────────────────────────
// Base HTTP client with silent token refresh on 401
// ─────────────────────────────────────────────────────────────
class HttpClient {
  private baseUrl: string;
  /** Prevents multiple concurrent refresh attempts (singleton promise). */
  private refreshPromise: Promise<string | null> | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private buildHeaders(extra?: Record<string, string>): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...extra,
    };
    const token = tokenStore.get();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  }

  /**
   * Silently exchange the refresh token for a new access token.
   * De-duplicated: concurrent requests all wait on the same promise.
   *
   * Returns the new access token, or null if refresh failed.
   */
  private async refreshAccessToken(): Promise<string | null> {
    if (this.refreshPromise) return this.refreshPromise;

    this.refreshPromise = (async (): Promise<string | null> => {
      const refreshToken = tokenStore.getRefresh();
      if (!refreshToken) return null;

      try {
        const res = await fetch(`${this.baseUrl}/api/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!res.ok) return null;

        const data: { access_token: string; refresh_token: string } = await res.json();
        tokenStore.set(data.access_token);
        // Store the rotated refresh token (old one is now revoked in Redis)
        if (data.refresh_token) tokenStore.setRefresh(data.refresh_token);
        return data.access_token;
      } catch {
        return null;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /** Force logout — clear tokens and redirect to login page. */
  private forceLogout(): void {
    tokenStore.clearAll();
    if (typeof window !== "undefined") {
      window.location.href = "/?session_expired=1";
    }
  }

  async request<T>(
    method: string,
    path: string,
    body?: unknown,
    options?: { headers?: Record<string, string>; _isRetry?: boolean }
  ): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: this.buildHeaders(options?.headers),
      body: body ? JSON.stringify(body) : undefined,
    });

    // ── Silent token refresh on 401 ──────────────────────────
    if (res.status === 401 && !options?._isRetry) {
      const newToken = await this.refreshAccessToken();

      if (newToken) {
        // Retry original request with the new access token
        return this.request<T>(method, path, body, {
          ...options,
          _isRetry: true,
        });
      } else {
        // Refresh also failed — session is dead
        this.forceLogout();
        throw new Error("Session expired. Please log in again.");
      }
    }

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const json = await res.json();
        detail = json.detail ?? detail;
      } catch {
        // ignore JSON parse errors
      }
      throw new Error(detail);
    }

    // 204 No Content
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  get = <T>(path: string) => this.request<T>("GET", path);
  post = <T>(path: string, body?: unknown) => this.request<T>("POST", path, body);
  put = <T>(path: string, body?: unknown) => this.request<T>("PUT", path, body);
  patch = <T>(path: string, body?: unknown) => this.request<T>("PATCH", path, body);
  del = <T>(path: string) => this.request<T>("DELETE", path);
}

// ─────────────────────────────────────────────────────────────
// Domain sub-clients
// ─────────────────────────────────────────────────────────────

class AuthApi {
  constructor(private http: HttpClient) {}

  /** Redirect the browser to Google OAuth — no fetch needed. */
  googleLoginUrl(): string {
    return `${BASE_URL}/api/auth/google`;
  }

  me = () => this.http.get<User>("/api/auth/me");

  setRole = (role: "creator" | "brand") =>
    this.http.post<User>("/api/auth/onboarding/role", { role });

  getInstagramAuthUrl = () =>
    this.http.get<{ url: string }>("/api/auth/instagram/url");

  connectInstagram = (code: string) =>
    this.http.post<User>("/api/auth/instagram/connect", { code });

  logout = () => this.http.post<void>("/api/auth/logout");
}

class CreatorsApi {
  constructor(private http: HttpClient) {}

  getProfile = (profileId: string) =>
    this.http.get<CreatorProfile>(`/api/creators/${profileId}`);

  updateProfile = (data: Partial<CreatorProfileFormData>) =>
    this.http.put<CreatorProfile>("/api/creators/profile", data);

  search = (params: {
    niche?: string;
    city?: string;
    min_followers?: number;
    page?: number;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) qs.append(k, String(v));
    });
    return this.http.get<PaginatedResponse<CreatorProfile>>(
      `/api/creators/search?${qs}`
    );
  };

  toggleCollab = () =>
    this.http.patch<CreatorProfile>("/api/creators/toggle-collab");

  syncInstagram = () =>
    this.http.post<CreatorProfile>("/api/creators/sync-instagram");
}

class BrandsApi {
  constructor(private http: HttpClient) {}

  getProfile = (brandProfileId?: string) =>
    brandProfileId
      ? this.http.get<BrandProfile>(`/api/brands/${brandProfileId}`)
      : this.http.get<BrandProfile>("/api/brands/profile");

  createProfile = (data: BrandProfileFormData) =>
    this.http.post<BrandProfile>("/api/brands/profile", data);

  updateProfile = (data: Partial<BrandProfileFormData>) =>
    this.http.put<BrandProfile>("/api/brands/profile", data);

  syncInstagram = () =>
    this.http.post<BrandProfile>("/api/brands/sync-instagram");
}

class CampaignsApi {
  constructor(private http: HttpClient) {}

  list = (params?: { status?: string; page?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params)
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) qs.append(k, String(v));
      });
    return this.http.get<PaginatedResponse<Campaign>>(`/api/campaigns/?${qs}`);
  };

  get = (id: string) => this.http.get<Campaign>(`/api/campaigns/${id}`);

  expressInterest = (campaignId: string) =>
    this.http.post<{ message: string }>(`/api/campaigns/${campaignId}/interest`);
}

class ConnectionsApi {
  constructor(private http: HttpClient) {}

  list = () =>
    this.http.get<{ accepted: Connection[]; pending: Connection[] }>(
      "/api/connections/"
    );

  request = (recipientProfileId: string, campaignId?: string) =>
    this.http.post<Connection>("/api/connections/request", {
      recipient_profile_id: recipientProfileId,
      campaign_id: campaignId ?? null,
    });

  accept = (id: string) =>
    this.http.post<Connection>(`/api/connections/${id}/accept`);

  decline = (id: string) =>
    this.http.post<Connection>(`/api/connections/${id}/decline`);
}

class NotificationsApi {
  constructor(private http: HttpClient) {}

  list = () => this.http.get<Notification[]>("/api/notifications/");

  markRead = (ids: string[]) =>
    this.http.post<void>("/api/notifications/read", { notification_ids: ids });
}

// ─────────────────────────────────────────────────────────────
// Main API singleton
// ─────────────────────────────────────────────────────────────

class ApiClient {
  private http = new HttpClient(BASE_URL);

  auth = new AuthApi(this.http);
  creators = new CreatorsApi(this.http);
  brands = new BrandsApi(this.http);
  campaigns = new CampaignsApi(this.http);
  connections = new ConnectionsApi(this.http);
  notifications = new NotificationsApi(this.http);
}

export const api = new ApiClient();
