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

// Shows
export const getShows = () => fetchAPI<ShowSummary[]>("/library/shows");
export const getShowDetail = (id: number) => fetchAPI<ShowDetail>(`/library/shows/${id}`);

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
  show_name?: string;
  episode_title?: string;
  episode_label?: string;
  match_reason?: string;
}

export interface SearchRequest {
  query: string;
  min_confidence?: number;
  characters?: string[];
  tone?: string;
  plot_significance?: string;
  setting_type?: string;
  max_explicitness_violence?: number;
  max_explicitness_language?: number;
  show_id?: number;
  episode_id?: number;
  limit?: number;
}

export interface SearchFacets {
  characters: string[];
  tones: string[];
  pacings: string[];
  plot_significance: string[];
  setting_types: string[];
}

export const getSearchFacets = () => fetchAPI<SearchFacets>("/search/facets");

// Shows
export interface ShowSummary {
  id: number;
  name: string;
  year: number | null;
  network: string | null;
  genres: string[];
  poster_url: string | null;
  fanart_url: string | null;
  sonarr_id: number | null;
  episode_count: number;
}

export interface ThemeConfig {
  primary_color?: string;
  secondary_color?: string;
  accent_color?: string;
  font?: string;
  style?: string;
}

export interface ShowEpisode {
  id: number;
  title: string;
  episode_number: number;
  air_date: string | null;
  overview: string | null;
  status: string;
  has_file: boolean;
  duration_seconds: number | null;
}

export interface ShowDetail {
  id: number;
  name: string;
  year: number | null;
  network: string | null;
  overview: string | null;
  genres: string[];
  poster_url: string | null;
  fanart_url: string | null;
  banner_url: string | null;
  clearlogo_url: string | null;
  rating_value: number | null;
  rating_votes: number | null;
  theme_config: ThemeConfig;
  cutprint: { threshold: number; min_scene: number; genre: string } | null;
  seasons: Record<string, ShowEpisode[]>;
  total_episodes: number;
}

// --- Sonarr Library Browser ---
export interface SonarrShow {
  sonarr_id: number;
  tvdb_id: number | null;
  title: string;
  year: number | null;
  network: string | null;
  genres: string[];
  season_count: number;
  episode_count: number;
  episode_file_count: number;
  overview: string;
  poster_url: string | null;
  fanart_url: string | null;
  path: string | null;
  rating: number | null;
}

export interface SonarrEpisode {
  sonarr_episode_id: number;
  title: string;
  season: number;
  episode_number: number;
  air_date: string | null;
  overview: string | null;
  has_file: boolean;
  file_path: string | null;
  file_size_mb: number | null;
  runtime: number | null;
}

export const browseSonarrShows = (q?: string) =>
  fetchAPI<{ count: number; shows: SonarrShow[] }>(
    `/library/sonarr/shows${q ? `?q=${encodeURIComponent(q)}` : ""}`
  );

export const browseSonarrEpisodes = (sonarrId: number, season?: number) =>
  fetchAPI<{ count: number; episodes: SonarrEpisode[] }>(
    `/library/sonarr/shows/${sonarrId}/episodes${season != null ? `?season=${season}` : ""}`
  );

export const importShowFromSonarr = (sonarrId: number) =>
  fetchAPI<{
    show_id: number;
    name: string;
    sonarr_id: number;
    episodes_created: number;
    episodes_updated: number;
    message: string;
  }>(`/library/import/${sonarrId}`, { method: "POST" });

export const startSeasonProcessing = (showId: number, season: number, skipIndexed = true) =>
  fetchAPI<{
    show: string;
    season: number;
    queued: number;
    skipped: number;
    message: string;
  }>(`/process/season/${showId}/${season}`, {
    method: "POST",
    body: JSON.stringify({ skip_indexed: skipIndexed }),
  });

export async function uploadVideo(
  file: File,
  showName: string,
  season: number,
  episodeNumber: number,
  episodeTitle: string,
  autoProcess: boolean,
): Promise<{
  show_id: number;
  episode_id: number;
  file_size_mb: number;
  message: string;
  job_id?: string;
  processing?: boolean;
}> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("show_name", showName);
  formData.append("season", String(season));
  formData.append("episode_number", String(episodeNumber));
  formData.append("episode_title", episodeTitle);
  formData.append("auto_process", String(autoProcess));

  const res = await fetch(`${API_URL}/api/process/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

// --- Tweak Studio ---
export interface TweakOut {
  id: number;
  mode: "bridge" | "restyle" | "redub";
  scene_a_id: number;
  scene_b_id: number | null;
  transition_prompt: string | null;
  restyle_prompt: string | null;
  restyle_strength: number | null;
  redub_config: { character: string; text: string; voice_preset: string }[] | null;
  status: "pending" | "generating" | "completed" | "failed";
  error: string | null;
  cost_usd: number;
  output_url: string | null;
  generation_seconds: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface VoicePreset {
  id: string;
  name: string;
  gender: string;
  accent: string;
}

export const createBridgeTweak = (sceneAId: number, sceneBId: number, prompt: string) =>
  fetchAPI<TweakOut>("/tweaks/bridge", {
    method: "POST",
    body: JSON.stringify({ scene_a_id: sceneAId, scene_b_id: sceneBId, transition_prompt: prompt }),
  });

export const createRestyleTweak = (sceneAId: number, prompt: string, strength = 0.7) =>
  fetchAPI<TweakOut>("/tweaks/restyle", {
    method: "POST",
    body: JSON.stringify({ scene_a_id: sceneAId, restyle_prompt: prompt, strength }),
  });

export const createRedubTweak = (sceneAId: number, lines: { character: string; text: string; voice_preset: string }[]) =>
  fetchAPI<TweakOut>("/tweaks/redub", {
    method: "POST",
    body: JSON.stringify({ scene_a_id: sceneAId, lines }),
  });

export const getTweaks = (mode?: string) =>
  fetchAPI<TweakOut[]>(`/tweaks/${mode ? `?mode=${mode}` : ""}`);

export const getTweak = (id: number) => fetchAPI<TweakOut>(`/tweaks/${id}`);

export const deleteTweak = (id: number) =>
  fetchAPI<{ message: string }>(`/tweaks/${id}`, { method: "DELETE" });

export const getVoicePresets = () =>
  fetchAPI<{ voices: VoicePreset[] }>("/tweaks/voices/presets");

// --- Analytics (Stage H) ---
export interface MoodTimelineEntry {
  scene_id: number;
  start: number;
  end: number;
  duration: number;
  tone: string | null;
  tone_intensity: number;
  mood: string | null;
  pacing: string | null;
  pacing_speed: number;
  location: string | null;
  characters: string[];
  explicitness: Record<string, number>;
  music_present: boolean | null;
  plot_significance: string | null;
}

export interface ScreenTimeChar {
  name: string;
  total_seconds: number;
  total_formatted: string;
  episodes: Record<string, number>;
}

export interface SceneDNA {
  scene_id: number;
  dimensions: Record<string, number>;
  metadata: {
    tone: string | null;
    pacing: string | null;
    location: string | null;
    characters: string[];
    plot_significance: string | null;
    confidence: number;
  };
}

export interface DialogResult {
  scene_id: number;
  episode_id: number;
  episode_label: string;
  episode_title: string;
  start_timestamp: number;
  location: string | null;
  matching_lines: { speaker: string; quote: string; timestamp: number | null }[];
}

export interface SimilarScene {
  scene_id: number;
  episode_id: number;
  episode_label: string;
  episode_title: string;
  similarity: number;
  location: string | null;
  tone: string | null;
  characters: string[];
  description: string;
  start_timestamp: number;
}

export interface EpisodeOverview {
  episode_id: number;
  show_name: string;
  episode_title: string;
  episode_label: string;
  scene_count: number;
  total_duration: number;
  total_dialog_lines: number;
  unique_characters: number;
  top_characters: [string, number][];
  tone_distribution: Record<string, number>;
  location_count: number;
  top_locations: [string, number][];
}

export const getMoodTimeline = (episodeId: number) =>
  fetchAPI<{ episode_id: number; scene_count: number; timeline: MoodTimelineEntry[] }>(
    `/analytics/mood-timeline/${episodeId}`
  );

export const getScreenTime = (showId: number, season?: number) =>
  fetchAPI<{ show_id: number; season: number | null; characters: ScreenTimeChar[] }>(
    `/analytics/screen-time/${showId}${season ? `?season=${season}` : ""}`
  );

export const getSceneDNA = (sceneId: number) =>
  fetchAPI<SceneDNA>(`/analytics/scene-dna/${sceneId}`);

export const dialogSearch = (q: string, showId?: number) =>
  fetchAPI<{ query: string; count: number; results: DialogResult[] }>(
    `/analytics/dialog-search?q=${encodeURIComponent(q)}${showId ? `&show_id=${showId}` : ""}`
  );

export const getSimilarScenes = (sceneId: number) =>
  fetchAPI<{ source_scene_id: number; similar: SimilarScene[] }>(
    `/analytics/similar/${sceneId}`
  );

export const getEpisodeOverview = (episodeId: number) =>
  fetchAPI<EpisodeOverview>(`/analytics/episode-overview/${episodeId}`);

// --- Reports ---
export interface ReportRequest {
  scope: "episode" | "season";
  episode_id?: number;
  show_id?: number;
  season?: number;
  report_types: string[];
  nl_query?: string;
  format: "preview" | "docx";
}

export interface ReportSection {
  type: string;
  title: string;
  [key: string]: unknown;
}

export interface ReportPreview {
  title: string;
  sections: ReportSection[];
}

export const generateReportPreview = (req: ReportRequest) =>
  fetchAPI<ReportPreview>("/reports/generate", {
    method: "POST",
    body: JSON.stringify({ ...req, format: "preview" }),
  });

export async function downloadReport(req: ReportRequest): Promise<void> {
  const url = `${API_URL}/api/reports/generate`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...req, format: "docx" }),
  });
  if (!resp.ok) throw new Error(`Download failed: ${resp.status}`);
  const blob = await resp.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  const disposition = resp.headers.get("Content-Disposition");
  a.download = disposition?.match(/filename="(.+)"/)?.[1] || "report.docx";
  a.click();
  URL.revokeObjectURL(a.href);
}
