import {
  AddToLibraryPayload,
  AuthResponse,
  LibraryItemDTO,
  LibraryStats,
  LiveSearchResultItem,
  MediaTypeFilter,
  RecommendationRequest,
  RecommendationResponse,
  UnifiedMediaDTO,
  UserDTO,
  WatchStatus,
} from "@/types";

export function getApiBaseUrl(): string {
  const envUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL;

  if (envUrl && envUrl.trim() && !envUrl.includes("localhost")) {
    return envUrl.trim().replace(/\/+$/, "");
  }

  // If in browser and on production domain (e.g. shelflick.com or vercel.app), default to production Render API
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      return "https://shelflick-api.onrender.com";
    }
  }

  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, "");
  }

  return "http://localhost:8000";
}

export const API_BASE_URL = getApiBaseUrl();
const TOKEN_KEY = "shelflick_token";

/**
 * Get stored JWT access token from localStorage (browser-only).
 */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Save JWT access token in localStorage.
 */
export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

/**
 * Remove JWT access token from localStorage.
 */
export function removeAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/**
 * Authenticated fetch wrapper that automatically appends
 * the Authorization: Bearer <token> header to all outbound requests.
 */
export async function authFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(init.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(input, {
    ...init,
    headers,
  });
}

/**
 * Formats poster URLs. Directly serves unblocked CDN images (m.media-amazon.com,
 * static.tvmaze.com, s4.anilist.co, mzstatic.com) and rewrites any legacy image.tmdb.org
 * or /api/v1/proxy/image URLs to the global wsrv.nl CDN so the backend bears 0 proxy load.
 */
export function formatPosterUrl(url: string | null | undefined): string {
  if (!url) {
    return "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500";
  }

  // If already proxied via wsrv.nl CDN, return as-is
  if (url.startsWith("https://wsrv.nl/?url=")) {
    return url;
  }

  // Handle legacy backend proxy URLs (/api/v1/proxy/image)
  if (url.includes("/api/v1/proxy/image")) {
    try {
      const parsed = new URL(url, "http://localhost:8000");
      const targetParam = parsed.searchParams.get("url");
      const pathParam = parsed.searchParams.get("path");
      const sizeParam = parsed.searchParams.get("size") || "w500";

      if (targetParam) {
        return `https://wsrv.nl/?url=${encodeURIComponent(targetParam)}`;
      }
      if (pathParam) {
        const cleanPath = pathParam.replace(/^\/+/, "");
        const tmdbUrl = `https://image.tmdb.org/t/p/${sizeParam}/${cleanPath}`;
        return `https://wsrv.nl/?url=${encodeURIComponent(tmdbUrl)}`;
      }
    } catch {
      // Fall through if URL parsing fails
    }
  }

  // Handle direct image.tmdb.org URLs (bypassing Turkish ISP DNS blocks via wsrv.nl)
  if (url.includes("image.tmdb.org")) {
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}`;
  }

  // Direct fast unblocked CDNs (m.media-amazon.com, static.tvmaze.com, s4.anilist.co, mzstatic.com, etc.)
  return url;
}

// Fallback curated sample recommendations if backend is unreachable
const FALLBACK_RECOMMENDATION: RecommendationResponse = {
  recommended_media: {
    external_id: "16498",
    source: "ANILIST",
    title: "Monster",
    original_title: "MONSTER",
    release_year: 2004,
    poster_url: "https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx19-gtMC64182sm4.jpg",
    synopsis: "Dr. Kenzo Tenma is a renowned Japanese brain surgeon in Germany. After choosing to operate on a young boy over the city's mayor, his life unspools into a psychological abyss when that boy grows into a monstrous sociopath.",
    genres: ["Drama", "Mystery", "Psychological", "Thriller"],
    themes: ["serial killer", "investigation", "cold war", "philosophy"],
    base_score: 8.8,
    vote_count: 145000,
    runtime_minutes: 24,
  },
  justification: "Kırmızı Listendeki yüzeysel klişelerden ve abartılı shounen anlatısından tamamen uzak olan Monster, aradığın derin psikolojik gerilimi ve etik hesaplaşmayı kusursuz işliyor. Kenzo Tenma ve Johan Liebert arasındaki kedi-fare oyunu seni ekrana kilitleyecek.",
  confidence_score: 0.96,
  parsed_intent: {
    is_direct_title_search: false,
    direct_title: null,
    media_type_filter: "ANIME",
    mood_keywords: ["karanlık", "tekinsiz", "psikolojik"],
    target_themes: ["felsefi", "gerilim"],
    excluded_tropes: ["shounen", "arkadaşlık gücü"],
    reference_titles: [],
  },
  candidates_count: 8,
  all_candidates: [],
};

const FALLBACK_RANDOM: RecommendationResponse = {
  recommended_media: {
    external_id: "157336",
    source: "TMDB_MOVIE",
    title: "Interstellar",
    original_title: "Interstellar",
    release_year: 2014,
    poster_url: "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
    synopsis: "The adventures of a group of explorers who make use of a newly discovered wormhole to surpass the limitations on human space travel and conquer the vast distances involved in an interstellar voyage.",
    genres: ["Adventure", "Drama", "Science Fiction"],
    themes: ["black hole", "space exploration", "time dilation", "father-daughter"],
    base_score: 8.4,
    vote_count: 36000,
    runtime_minutes: 169,
  },
  justification: "Şansına Güveniyorum keşfinde zaman ve uzay büken eşsiz bir sinema başyapıtı çıktı! Christopher Nolan'ın yerçekimi, sevgi ve insanlığın hayatta kalma mücadelesini ele aldığı bu destansı eser sana unutulmaz anlar yaşatacak.",
  confidence_score: 0.99,
  parsed_intent: {
    is_direct_title_search: false,
    direct_title: null,
    media_type_filter: "MOVIE",
    mood_keywords: ["epik", "uzay", "bilim kurgu"],
    target_themes: ["kara delik", "zaman", "felsefe"],
    excluded_tropes: [],
    reference_titles: [],
  },
  candidates_count: 1,
  all_candidates: [],
};

// ================= AUTH API CALLS ================= //

/** Error thrown by auth calls; `status` is 0 for network failures. */
export class AuthApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
  }
}

const VALIDATION_FIELD_LABELS: Record<string, string> = {
  email: "E-posta",
  password: "Şifre",
  name: "Ad",
  credential: "Google kimliği",
};

function extractErrorDetail(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  // FastAPI / Pydantic 422: [{ loc: [...], msg: "...", type: "..." }]
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: unknown[]; type?: string; msg?: string };
    const field = String(first.loc?.[first.loc.length - 1] ?? "");
    const label = VALIDATION_FIELD_LABELS[field] || "Alan";
    if (field === "email") return "Geçerli bir e-posta adresi girin.";
    if (first.type?.includes("too_short")) {
      return field === "password" ? "Şifre en az 6 karakter olmalıdır." : `${label} çok kısa.`;
    }
    if (first.type?.includes("too_long")) return `${label} çok uzun.`;
    if (first.type === "missing") return `${label} alanı zorunludur.`;
    return `${label}: ${first.msg || "geçersiz değer"}`;
  }
  return null;
}

async function authRequest<T>(path: string, body: unknown, fallbackMsg: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);

  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    const aborted = err instanceof DOMException && err.name === "AbortError";
    throw new AuthApiError(
      aborted
        ? "Sunucu yanıt vermedi (zaman aşımı). Lütfen tekrar deneyin."
        : "Sunucuya bağlanılamadı. Backend'in çalıştığından ve internet bağlantınızdan emin olun.",
      0
    );
  } finally {
    clearTimeout(timeout);
  }

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const detail = extractErrorDetail(data);
    const msg =
      detail ||
      (response.status >= 500
        ? "Sunucuda beklenmeyen bir hata oluştu. Lütfen biraz sonra tekrar deneyin."
        : fallbackMsg);
    throw new AuthApiError(msg, response.status);
  }

  if (!data || typeof data !== "object" || !(data as { access_token?: string }).access_token) {
    throw new AuthApiError("Sunucudan geçersiz yanıt alındı.", response.status);
  }
  return data as T;
}

export function registerApi(email: string, password: string, name?: string): Promise<AuthResponse> {
  return authRequest<AuthResponse>(
    "/api/v1/auth/register",
    { email: email.trim(), password, name: name?.trim() || undefined },
    "Kayıt olurken bir hata oluştu."
  );
}

export function loginApi(email: string, password: string): Promise<AuthResponse> {
  return authRequest<AuthResponse>(
    "/api/v1/auth/login",
    { email: email.trim(), password },
    "Giriş yapılırken bir hata oluştu."
  );
}

export function googleAuthApi(credential: string): Promise<AuthResponse> {
  return authRequest<AuthResponse>(
    "/api/v1/auth/google",
    { credential },
    "Google ile giriş yapılırken bir hata oluştu."
  );
}

/**
 * Returns the current user, `null` if the token is invalid (401/403),
 * and throws AuthApiError(status 0) on network/server problems so the
 * caller can keep the session instead of logging the user out.
 */
export async function getCurrentUserApi(): Promise<UserDTO | null> {
  let response: Response;
  try {
    response = await authFetch(`${getApiBaseUrl()}/api/v1/auth/me`);
  } catch {
    throw new AuthApiError("Sunucuya bağlanılamadı.", 0);
  }
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new AuthApiError("Profil alınamadı.", response.status);
  return (await response.json()) as UserDTO;
}

// ================= MEDIA & RECOMMENDATION APIS ================= //

export async function fetchRecommendation(
  request: RecommendationRequest
): Promise<RecommendationResponse> {
  try {
    const response = await authFetch(`${getApiBaseUrl()}/api/v1/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.warn("Backend unavailable, using rich client-side fallback:", error);
    return {
      ...FALLBACK_RECOMMENDATION,
      parsed_intent: {
        ...FALLBACK_RECOMMENDATION.parsed_intent,
        mood_keywords: [request.prompt.slice(0, 20)],
      },
    };
  }
}

export const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

export async function fetchRandomMasterpiece(
  userId?: string,
  mediaType?: string
): Promise<RecommendationResponse> {
  try {
    const url = new URL(`${getApiBaseUrl()}/api/v1/recommend/random`);
    if (userId) {
      url.searchParams.set("user_id", userId);
    }
    if (mediaType && mediaType.toUpperCase() !== "ALL") {
      url.searchParams.set("media_type", mediaType.toLowerCase());
    }
    const response = await authFetch(url.toString());
    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.warn("Backend unavailable for random discovery, using fallback:", error);
    return FALLBACK_RANDOM;
  }
}

export async function addToLibrary(payload: AddToLibraryPayload): Promise<LibraryItemDTO | null> {
  try {
    const response = await authFetch(`${getApiBaseUrl()}/api/v1/library/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: payload.user_id,
        media: payload.media,
        status: payload.status || "PLAN_TO_WATCH",
        is_favorite: payload.is_favorite,
        user_score: payload.user_score,
        personal_notes: payload.personal_notes,
        drop_reason: payload.drop_reason,
        watched_episodes: payload.watched_episodes,
        watched_seasons: payload.watched_seasons,
      }),
    });
    if (!response.ok) {
      throw new Error(`Failed to add item to library: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error adding item to library:", error);
    return null;
  }
}

export async function getLibraryStats(userId?: string): Promise<LibraryStats> {
  try {
    const url = new URL(`${getApiBaseUrl()}/api/v1/library/stats`);
    if (userId) {
      url.searchParams.set("user_id", userId);
    }
    const response = await authFetch(url.toString());
    if (!response.ok) {
      throw new Error(`Failed to fetch library stats: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching library stats:", error);
    return {
      total_watch_time_minutes: 0,
      total_watch_time_formatted: { days: 0, hours: 0, minutes: 0 },
      total_episodes_watched: 0,
      radar_items: [],
    };
  }
}

export async function deleteLibraryItem(itemId: string, userId?: string): Promise<boolean> {
  try {
    const url = new URL(`${getApiBaseUrl()}/api/v1/library/items/${itemId}`);
    if (userId) {
      url.searchParams.set("user_id", userId);
    }
    const response = await authFetch(url.toString(), {
      method: "DELETE",
    });
    return response.ok;
  } catch (error) {
    console.error("Error deleting library item:", error);
    return false;
  }
}

export async function fetchLibraryItems(
  userId?: string,
  statusFilter?: WatchStatus
): Promise<LibraryItemDTO[]> {
  try {
    const url = new URL(`${getApiBaseUrl()}/api/v1/library/items`);
    if (userId) {
      url.searchParams.set("user_id", userId);
    }
    if (statusFilter) {
      url.searchParams.set("status_filter", statusFilter);
    }
    const response = await authFetch(url.toString());
    if (!response.ok) {
      throw new Error(`Failed to fetch library items: HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching library items:", error);
    return [];
  }
}

export async function sendUserFeedback(
  mediaId: string,
  action: "LIKE" | "WATCHING" | "DISLIKE" | "DISMISS"
): Promise<{ success: boolean }> {
  try {
    const response = await authFetch(`${getApiBaseUrl()}/api/v1/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_id: mediaId, action }),
    });
    return { success: response.ok };
  } catch {
    return { success: true };
  }
}

/**
 * Fast non-LLM live autocomplete search across TMDB & AniList.
 */
export async function fetchLiveSearch(
  query: string,
  signal?: AbortSignal,
  mediaType?: MediaTypeFilter
): Promise<LiveSearchResultItem[]> {
  const cleanQ = query.trim();
  if (!cleanQ || cleanQ.length < 2) return [];

  try {
    const url = new URL(`${getApiBaseUrl()}/api/v1/search/live`);
    url.searchParams.set("q", cleanQ);
    if (mediaType && mediaType !== "ALL") {
      url.searchParams.set("type", mediaType);
    }

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal,
    });

    if (!response.ok) {
      return [];
    }
    return await response.json();
  } catch (error: any) {
    if (error?.name === "AbortError") return [];
    console.warn("Live search error:", error);
    return [];
  }
}

