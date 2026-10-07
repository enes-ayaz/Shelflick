import {
  AddToLibraryPayload,
  AuthResponse,
  LibraryItemDTO,
  LiveSearchResultItem,
  RecommendationRequest,
  RecommendationResponse,
  UnifiedMediaDTO,
  UserDTO,
  WatchStatus,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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
 * Ensures TMDB images are routed through the backend DoH Image Proxy
 * to bypass local ISP DNS sinkholing, while leaving AniList and direct CDNs intact.
 */
export function formatPosterUrl(url: string | null | undefined): string {
  if (!url) return "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500";
  
  if (url.includes("/api/v1/proxy/image")) return url;
  
  if (url.includes("image.tmdb.org")) {
    return `${API_BASE_URL}/api/v1/proxy/image?url=${encodeURIComponent(url)}`;
  }
  
  // Veritabanı veya TMDB'den "/xyz.jpg" şeklinde yarım path gelirse:
  if (url.startsWith("/")) {
    return `${API_BASE_URL}/api/v1/proxy/image?path=${encodeURIComponent(url)}&size=w500`;
  }
  
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

export async function registerApi(
  email: string,
  password: string,
  name?: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Kayıt olurken bir hata oluştu.");
  }
  return data as AuthResponse;
}

export async function loginApi(
  email: string,
  password: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Giriş yapılırken bir hata oluştu.");
  }
  return data as AuthResponse;
}

export async function googleAuthApi(credential: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Google ile giriş yapılırken bir hata oluştu.");
  }
  return data as AuthResponse;
}

export async function getCurrentUserApi(): Promise<UserDTO | null> {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/auth/me`);
    if (!response.ok) return null;
    return await response.json();
  } catch (err) {
    console.warn("Failed to fetch current user profile:", err);
    return null;
  }
}

// ================= MEDIA & RECOMMENDATION APIS ================= //

export async function fetchRecommendation(
  request: RecommendationRequest
): Promise<RecommendationResponse> {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/recommend`, {
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
    const url = new URL(`${API_BASE_URL}/api/v1/recommend/random`);
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
    const response = await authFetch(`${API_BASE_URL}/api/v1/library/items`, {
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

export async function deleteLibraryItem(itemId: string, userId?: string): Promise<boolean> {
  try {
    const url = new URL(`${API_BASE_URL}/api/v1/library/items/${itemId}`);
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
    const url = new URL(`${API_BASE_URL}/api/v1/library/items`);
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
    const response = await authFetch(`${API_BASE_URL}/api/v1/feedback`, {
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
  signal?: AbortSignal
): Promise<LiveSearchResultItem[]> {
  const cleanQ = query.trim();
  if (!cleanQ || cleanQ.length < 2) return [];

  try {
    const url = new URL(`${API_BASE_URL}/api/v1/search/live`);
    url.searchParams.set("q", cleanQ);

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

