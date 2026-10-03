export type MediaTypeFilter = "ALL" | "ANIME" | "MOVIE" | "SERIES";

export interface UnifiedMediaDTO {
  external_id: string;
  source: "TMDB_MOVIE" | "TMDB_SERIES" | "ANILIST";
  title: string;
  original_title?: string | null;
  release_year?: number | null;
  poster_url: string;
  synopsis: string;
  genres: string[];
  themes: string[];
  base_score: number;
  vote_count: number;
  runtime_minutes?: number;
}

export interface UserIntentFilter {
  is_direct_title_search: boolean;
  direct_title?: string | null;
  media_type_filter: MediaTypeFilter;
  mood_keywords: string[];
  target_themes: string[];
  excluded_tropes: string[];
  reference_titles: string[];
}

export interface SingleRecommendation {
  media: UnifiedMediaDTO;
  justification: string;
  confidence_score?: number;
}

export interface LiveSearchResultItem {
  id: string;
  title: string;
  release_year?: number | null;
  type: "MOVIE" | "SERIES" | "ANIME";
  poster_path?: string | null;
  source?: string | null;
  base_score?: number | null;
  synopsis?: string | null;
  genres?: string[];
}

export interface RecommendationResponse {
  recommendations?: SingleRecommendation[];
  recommended_media: UnifiedMediaDTO | null;
  justification: string;
  confidence_score: number;
  parsed_intent: UserIntentFilter;
  candidates_count: number;
  all_candidates: UnifiedMediaDTO[];
}

export interface RecommendationRequest {
  prompt: string;
  user_id?: string;
  limit?: number;
}

export type FeedbackAction = "LIKE" | "WATCHING" | "DISLIKE" | "DISMISS";

export type WatchStatus = "PLAN_TO_WATCH" | "WATCHING" | "COMPLETED" | "DROPPED";

export interface LibraryItemDTO {
  id: string;
  media_id: string;
  external_id: string;
  source: string;
  title: string;
  original_title?: string | null;
  release_year?: number | null;
  poster_url: string;
  genres: string[];
  themes: string[];
  base_score: number;
  status: WatchStatus;
  is_favorite: boolean;
  user_score?: number | null;
  personal_notes?: string | null;
  drop_reason?: string | null;
}

export interface AddToLibraryPayload {
  user_id?: string;
  media: UnifiedMediaDTO;
  status?: WatchStatus;
  is_favorite?: boolean;
  user_score?: number;
  personal_notes?: string;
  drop_reason?: string;
}

export interface UserDTO {
  id: string;
  email: string;
  name: string;
  username?: string | null;
  google_id?: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserDTO;
}

