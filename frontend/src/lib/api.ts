const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Episodes
export const getEpisodes = () => fetchAPI<Episode[]>("/episodes/");
export const getEpisode = (id: number) => fetchAPI<Episode>(`/episodes/${id}`);

// Scenes
export const getScenes = (episodeId: number) =>
  fetchAPI<Scene[]>(`/scenes/episode/${episodeId}`);
export const getScene = (id: number) => fetchAPI<Scene>(`/scenes/${id}`);

// Search
export const searchScenes = (query: SearchRequest) =>
  fetchAPI<SearchResult[]>("/search/", {
    method: "POST",
    body: JSON.stringify(query),
  });

// Health
export const getHealth = () => fetchAPI<{ status: string }>("/health");

// Types
export interface Episode {
  id: number;
  show_id: number;
  title: string;
  season: number;
  episode_number: number;
  duration_seconds: number | null;
  status: string;
  gemini_cost_usd: number;
  indexed_at: string | null;
  created_at: string;
}

export interface Scene {
  id: number;
  episode_id: number;
  start_timestamp: number;
  end_timestamp: number;
  duration: number;
  characters_present: { name: string; confidence: number }[];
  key_dialog: { speaker: string; exact_quote: string; timestamp: number }[];
  actions: string | null;
  interactions: string | null;
  mood_ambience: string | null;
  color_palette: string[];
  tropes_memes: string[];
  explicitness: string;
  background: string | null;
  scene_transitions: string | null;
  motivations_feelings: string | null;
  overall_confidence: number;
  thumbnail_path: string | null;
  description_text: string | null;
  created_at: string;
}

export interface SearchResult {
  scene: Scene;
  similarity: number;
}

export interface SearchRequest {
  query: string;
  min_confidence?: number;
  characters?: string[];
  limit?: number;
}
