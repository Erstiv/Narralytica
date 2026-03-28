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

// Processing
export const startProcessing = (episodeId: number) =>
  fetchAPI<{ job_id: string; message: string }>(`/process/episode/${episodeId}`, {
    method: "POST",
  });
export const getProcessingHealth = () => fetchAPI<Record<string, unknown>>("/process/health");
export const getProcessingJobs = () => fetchAPI<{ jobs: ProcessingJob[] }>("/process/jobs");
export const getProcessingJob = (jobId: string) =>
  fetchAPI<ProcessingJob>(`/process/jobs/${jobId}`);

export interface ProcessingJob {
  job_id: string;
  status: string;
  episode_id: number;
  show_id: number;
  video_path: string;
  current_step: string;
  progress_pct: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  elapsed_seconds: number | null;
}

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

// Metadata density levels for the UI slider
export type MetadataDensity = "essential" | "standard" | "maximum";

export interface Scene {
  id: number;
  episode_id: number;
  start_timestamp: number;
  end_timestamp: number;
  duration: number;

  // Characters & Dialog
  characters_present: { name: string; confidence: number; is_speaking?: boolean }[];
  key_dialog: { speaker: string; exact_quote: string; timestamp: number; emotion?: string }[];
  character_interactions: { character_a: string; character_b: string; interaction_type: string; description: string }[];
  character_motivations_feelings: string | null;

  // Actions & Humor
  actions: string | null;
  interactions: string | null;
  visual_gags: string | null;
  dialog_based_humor: string | null;

  // Location & Setting
  location: string | null;
  time_of_day: string | null;
  setting_type: string | null;
  background: string | null;

  // Visual & Cinematographic
  color_palette: string[];
  lighting: string | null;
  camera_shot_type: string | null;
  camera_movement: string | null;
  scene_composition: string | null;
  visual_style_notes: string | null;

  // Audio & Music
  music_present: boolean | null;
  music_description: string | null;
  sound_effects: string | null;
  ambient_audio: string | null;

  // Mood & Tone
  mood_ambience: string | null;
  scene_pacing: string | null;
  tone: string | null;
  emotional_arc: string | null;

  // Narrative & Context
  tropes_memes: string[];
  cultural_references: string[];
  recurring_gags: string | null;
  plot_significance: string | null;
  continuity_notes: string | null;

  // Explicitness (5 dimensions)
  explicitness: string;
  explicitness_language: number;
  explicitness_violence: number;
  explicitness_sexual: number;
  explicitness_substance: number;
  explicitness_thematic: number;

  // Scene Structure
  scene_transitions: string | null;
  text_on_screen: string | null;

  // Search & Meta
  overall_confidence: number;
  thumbnail_path: string | null;
  description_text: string | null;
  merged_transcript: { speaker: string; text: string; start: number; end: number }[] | null;
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
