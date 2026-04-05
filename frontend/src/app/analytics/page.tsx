"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getShows,
  getShowDetail,
  getMoodTimeline,
  getScreenTime,
  getSceneDNA,
  dialogSearch,
  getSimilarScenes,
  getEpisodeOverview,
  type ShowSummary,
  type ShowEpisode,
  type MoodTimelineEntry,
  type ScreenTimeChar,
  type SceneDNA as SceneDNAType,
  type DialogResult,
  type SimilarScene,
  type EpisodeOverview,
} from "@/lib/api";

// =============================================================================
// Shared helpers
// =============================================================================
function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

const TONE_COLORS: Record<string, string> = {
  comedic: "#FACC15", humorous: "#FDE047", lighthearted: "#A3E635", playful: "#BEF264",
  dramatic: "#F87171", tense: "#EF4444", suspenseful: "#DC2626", dark: "#991B1B",
  emotional: "#C084FC", melancholic: "#A78BFA", sad: "#818CF8",
  neutral: "#9CA3AF", informational: "#6B7280",
  action: "#FB923C", chaotic: "#F97316", frenetic: "#EA580C",
};

function getToneColor(tone: string | null) {
  return TONE_COLORS[(tone || "").toLowerCase()] || "#6B7280";
}

// =============================================================================
// Episode Picker
// =============================================================================
function EpisodePicker({
  onSelect,
}: {
  onSelect: (showId: number, episodeId: number, label: string) => void;
}) {
  const [shows, setShows] = useState<ShowSummary[]>([]);
  const [selectedShow, setSelectedShow] = useState<number | null>(null);
  const [seasons, setSeasons] = useState<Record<string, ShowEpisode[]>>({});
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);

  useEffect(() => {
    getShows().then(setShows).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedShow) return;
    getShowDetail(selectedShow).then((d) => {
      setSeasons(d.seasons);
      const keys = Object.keys(d.seasons).sort((a, b) => Number(a) - Number(b));
      if (keys.length) setSelectedSeason(keys[0]);
    }).catch(() => {});
  }, [selectedShow]);

  const seasonKeys = Object.keys(seasons).sort((a, b) => Number(a) - Number(b));
  const episodes = selectedSeason ? seasons[selectedSeason] || [] : [];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Show</label>
          <select
            value={selectedShow || ""}
            onChange={(e) => {
              setSelectedShow(Number(e.target.value));
              setSelectedSeason(null);
            }}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-simpsons-yellow focus:outline-none"
          >
            <option value="">Select show...</option>
            {shows.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        {seasonKeys.length > 0 && (
          <div className="flex gap-1">
            {seasonKeys.map((s) => (
              <button
                key={s}
                onClick={() => setSelectedSeason(s)}
                className={`px-3 py-2 rounded text-xs font-medium transition ${
                  selectedSeason === s
                    ? "bg-simpsons-yellow text-black"
                    : "bg-gray-800 text-gray-400 hover:text-gray-200"
                }`}
              >
                S{s.padStart(2, "0")}
              </button>
            ))}
          </div>
        )}
      </div>

      {episodes.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {episodes.filter((e) => e.status === "ready").map((ep) => (
            <button
              key={ep.id}
              onClick={() =>
                onSelect(
                  selectedShow!,
                  ep.id,
                  `S${selectedSeason?.padStart(2, "0")}E${String(ep.episode_number).padStart(2, "0")} ${ep.title}`
                )
              }
              className="bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded px-3 py-1.5 text-xs transition"
            >
              E{String(ep.episode_number).padStart(2, "0")} — {ep.title}
            </button>
          ))}
          {episodes.filter((e) => e.status === "ready").length === 0 && (
            <p className="text-xs text-gray-600">No indexed episodes in this season yet</p>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Mood Timeline Chart
// =============================================================================
function MoodTimeline({ data, onSceneClick }: { data: MoodTimelineEntry[]; onSceneClick?: (sceneId: number) => void }) {
  if (!data.length) return null;
  const maxTime = data[data.length - 1].end;

  return (
    <div>
      <h3 className="text-lg font-semibold mb-3">Mood Timeline</h3>

      {/* Tone track */}
      <div className="mb-4">
        <span className="text-xs text-gray-500 block mb-1">Tone</span>
        <div className="flex h-10 rounded-lg overflow-hidden border border-gray-800">
          {data.map((entry) => {
            const width = ((entry.end - entry.start) / maxTime) * 100;
            return (
              <div
                key={entry.scene_id}
                className="relative group"
                style={{
                  width: `${width}%`,
                  backgroundColor: getToneColor(entry.tone),
                  opacity: 0.3 + entry.tone_intensity * 0.7,
                  cursor: onSceneClick ? "pointer" : undefined,
                }}
                title={`${entry.tone || "?"} — ${entry.location || "?"} (${formatTime(entry.start)}) — Click for Scene DNA`}
                onClick={() => onSceneClick?.(entry.scene_id)}
              >
                <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-[10px] whitespace-nowrap z-10">
                  {entry.tone} &middot; {entry.location} &middot; {formatTime(entry.start)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pacing track */}
      <div className="mb-4">
        <span className="text-xs text-gray-500 block mb-1">Pacing</span>
        <div className="flex h-6 rounded-lg overflow-hidden border border-gray-800">
          {data.map((entry) => {
            const width = ((entry.end - entry.start) / maxTime) * 100;
            return (
              <div
                key={entry.scene_id}
                style={{
                  width: `${width}%`,
                  backgroundColor: `rgba(250, 204, 21, ${0.1 + entry.pacing_speed * 0.9})`,
                }}
                title={`${entry.pacing || "?"} — ${formatTime(entry.start)}`}
              />
            );
          })}
        </div>
        <div className="flex justify-between text-[10px] text-gray-600 mt-0.5">
          <span>0:00</span>
          <span>{formatTime(maxTime)}</span>
        </div>
      </div>

      {/* Characters track */}
      <div className="mb-4">
        <span className="text-xs text-gray-500 block mb-1">Characters per Scene</span>
        <div className="flex h-8 items-end gap-px">
          {data.map((entry) => {
            const width = ((entry.end - entry.start) / maxTime) * 100;
            const charCount = entry.characters.length;
            const barH = Math.min(100, charCount * 20);
            return (
              <div
                key={entry.scene_id}
                className="bg-blue-500/40 rounded-t"
                style={{
                  width: `${width}%`,
                  height: `${barH}%`,
                }}
                title={`${charCount} chars: ${entry.characters.join(", ")}`}
              />
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-[10px]">
        {Object.entries(
          data.reduce<Record<string, number>>((acc, d) => {
            if (d.tone) acc[d.tone] = (acc[d.tone] || 0) + 1;
            return acc;
          }, {})
        )
          .sort((a, b) => b[1] - a[1])
          .slice(0, 8)
          .map(([tone, count]) => (
            <span key={tone} className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: getToneColor(tone) }}
              />
              <span className="text-gray-400">
                {tone} ({count})
              </span>
            </span>
          ))}
      </div>
    </div>
  );
}

// =============================================================================
// Screen Time Bar Chart
// =============================================================================
function ScreenTimeChart({ characters }: { characters: ScreenTimeChar[] }) {
  if (!characters.length) return null;
  const top = characters.slice(0, 12);
  const maxSec = top[0]?.total_seconds || 1;

  return (
    <div>
      <h3 className="text-lg font-semibold mb-1">Character Presence</h3>
      <p className="text-xs text-gray-500 mb-3">Total duration of scenes each character appears in</p>
      <div className="space-y-2">
        {top.map((c, i) => (
          <div key={c.name} className="flex items-center gap-3">
            <span className="text-xs text-gray-400 w-28 truncate text-right" title={c.name}>
              {c.name}
            </span>
            <div className="flex-1 h-6 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${(c.total_seconds / maxSec) * 100}%`,
                  backgroundColor: `hsl(${(i * 37) % 360}, 70%, 55%)`,
                }}
              />
            </div>
            <span className="text-xs text-gray-500 w-16">{c.total_formatted}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Scene DNA Radar (SVG)
// =============================================================================
function SceneDNARadar({ dna }: { dna: SceneDNAType }) {
  const dims = Object.entries(dna.dimensions);
  const n = dims.length;
  const cx = 120, cy = 120, r = 90;

  function polarToXY(angle: number, value: number) {
    const rad = (angle - 90) * (Math.PI / 180);
    return {
      x: cx + r * value * Math.cos(rad),
      y: cy + r * value * Math.sin(rad),
    };
  }

  const angleStep = 360 / n;

  // Build polygon points
  const points = dims.map(([, val], i) => {
    const { x, y } = polarToXY(i * angleStep, val);
    return `${x},${y}`;
  }).join(" ");

  return (
    <div>
      <h3 className="text-lg font-semibold mb-3">Scene DNA</h3>
      <div className="flex items-start gap-6">
        <svg viewBox="0 0 240 240" className="w-56 h-56 flex-shrink-0">
          {/* Grid rings */}
          {[0.25, 0.5, 0.75, 1.0].map((ring) => (
            <circle
              key={ring}
              cx={cx}
              cy={cy}
              r={r * ring}
              fill="none"
              stroke="#374151"
              strokeWidth={0.5}
            />
          ))}
          {/* Axis lines + labels */}
          {dims.map(([label], i) => {
            const { x, y } = polarToXY(i * angleStep, 1.15);
            const axisEnd = polarToXY(i * angleStep, 1.0);
            return (
              <g key={label}>
                <line
                  x1={cx} y1={cy}
                  x2={axisEnd.x} y2={axisEnd.y}
                  stroke="#374151"
                  strokeWidth={0.5}
                />
                <text
                  x={x} y={y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="fill-gray-500 text-[8px]"
                >
                  {label}
                </text>
              </g>
            );
          })}
          {/* Data polygon */}
          <polygon
            points={points}
            fill="rgba(250, 204, 21, 0.2)"
            stroke="#FACC15"
            strokeWidth={2}
          />
          {/* Data points */}
          {dims.map(([, val], i) => {
            const { x, y } = polarToXY(i * angleStep, val);
            return (
              <circle key={i} cx={x} cy={y} r={3} fill="#FACC15" />
            );
          })}
        </svg>

        <div className="space-y-1 text-xs">
          {dims.map(([label, val]) => (
            <div key={label} className="flex items-center gap-2">
              <span className="text-gray-400 w-20 capitalize">{label}</span>
              <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-simpsons-yellow rounded-full"
                  style={{ width: `${val * 100}%` }}
                />
              </div>
              <span className="text-gray-500 w-8">{(val * 100).toFixed(0)}%</span>
            </div>
          ))}
          <div className="pt-2 border-t border-gray-800 mt-2">
            <p className="text-gray-400">{dna.metadata.location || "Unknown location"}</p>
            <p className="text-gray-500">{dna.metadata.characters.join(", ")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Dialog Search
// =============================================================================
function DialogSearchPanel() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DialogResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function doSearch() {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await dialogSearch(query);
      setResults(data.results);
      setSearched(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function highlight(text: string): React.ReactNode {
    if (!query.trim()) return text;
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return text;
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + query.length);
    const after = text.slice(idx + query.length);
    return (
      <>
        <span>{before}</span>
        <mark className="bg-simpsons-yellow/30 text-simpsons-yellow rounded px-0.5">{match}</mark>
        <span>{after}</span>
      </>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-semibold mb-3">Dialog Search</h3>
      <div className="flex gap-2 mb-4">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          placeholder={"Search dialog... e.g. \"D'oh\" or \"Excellent\""}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:border-simpsons-yellow focus:outline-none"
        />
        <button
          onClick={doSearch}
          disabled={loading}
          className="bg-simpsons-yellow text-black font-medium px-5 py-2 rounded-lg hover:bg-yellow-400 transition disabled:opacity-50"
        >
          {loading ? "..." : "Search"}
        </button>
      </div>

      {results.length > 0 && (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {results.map((r) => (
            <div
              key={`${r.scene_id}-${r.episode_id}`}
              className="bg-gray-900 border border-gray-800 rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-simpsons-yellow">
                  {r.episode_label} — {r.episode_title}
                </span>
                <span className="text-[10px] text-gray-600">
                  Scene #{r.scene_id} &middot; {formatTime(r.start_timestamp)}
                </span>
              </div>
              {r.matching_lines.map((line, i) => (
                <div key={i} className="flex gap-2 mb-1">
                  <span className="text-xs text-blue-400 font-medium w-24 flex-shrink-0 truncate">
                    {line.speaker}:
                  </span>
                  <span className="text-xs text-gray-300">
                    {highlight(line.quote)}
                  </span>
                </div>
              ))}
              {r.location && (
                <p className="text-[10px] text-gray-600 mt-1">📍 {r.location}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {searched && results.length === 0 && (
        <p className="text-gray-500 text-sm text-center py-6">No dialog matches found</p>
      )}
    </div>
  );
}

// =============================================================================
// Similar Scenes / AI Recommender
// =============================================================================
function SimilarScenesPanel() {
  const [sceneId, setSceneId] = useState("");
  const [similar, setSimilar] = useState<SimilarScene[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function doFind() {
    const id = Number(sceneId);
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getSimilarScenes(id);
      setSimilar(data.similar);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
      setSimilar([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h3 className="text-lg font-semibold mb-3">AI Recommender</h3>
      <p className="text-xs text-gray-500 mb-3">
        Enter a scene ID to find similar scenes using vector similarity
      </p>
      <div className="flex gap-2 mb-4">
        <input
          value={sceneId}
          onChange={(e) => setSceneId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doFind()}
          placeholder="Scene ID (e.g. 35)"
          type="number"
          className="w-32 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-simpsons-yellow focus:outline-none"
        />
        <button
          onClick={doFind}
          disabled={loading}
          className="bg-simpsons-yellow text-black font-medium px-4 py-2 rounded-lg hover:bg-yellow-400 transition disabled:opacity-50"
        >
          {loading ? "..." : "Find Similar"}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm mb-2">{error}</p>}

      {similar.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {similar.map((s) => (
            <div
              key={s.scene_id}
              className="bg-gray-900 border border-gray-800 rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono text-simpsons-yellow">
                  {s.episode_label} &middot; Scene #{s.scene_id}
                </span>
                <span className="text-[10px] bg-green-900/50 text-green-400 px-2 py-0.5 rounded-full">
                  {(s.similarity * 100).toFixed(1)}%
                </span>
              </div>
              <p className="text-xs text-gray-300 line-clamp-2">{s.description}</p>
              <div className="flex items-center gap-2 mt-2 text-[10px] text-gray-500">
                {s.location && <span>📍 {s.location}</span>}
                {s.tone && (
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: getToneColor(s.tone) }} />
                    {s.tone}
                  </span>
                )}
                <span>{formatTime(s.start_timestamp)}</span>
              </div>
              <p className="text-[10px] text-gray-600 mt-1">{s.characters.join(", ")}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Episode Overview Stats
// =============================================================================
function EpisodeOverviewPanel({ overview }: { overview: EpisodeOverview }) {
  return (
    <div>
      <h3 className="text-lg font-semibold mb-3">
        {overview.episode_label} — {overview.episode_title}
      </h3>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-simpsons-yellow">{overview.scene_count}</p>
          <p className="text-[10px] text-gray-500">Scenes</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-400">{overview.unique_characters}</p>
          <p className="text-[10px] text-gray-500">Characters</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-400">{overview.total_dialog_lines}</p>
          <p className="text-[10px] text-gray-500">Dialog Lines</p>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-purple-400">{overview.location_count}</p>
          <p className="text-[10px] text-gray-500">Locations</p>
        </div>
      </div>

      {/* Tone distribution */}
      {Object.keys(overview.tone_distribution).length > 0 && (
        <div className="mb-4">
          <span className="text-xs text-gray-400 block mb-2">Tone Distribution</span>
          <div className="flex flex-wrap gap-2">
            {Object.entries(overview.tone_distribution).map(([tone, count]) => (
              <span
                key={tone}
                className="px-2 py-1 rounded-full text-[10px] font-medium border"
                style={{
                  borderColor: getToneColor(tone),
                  color: getToneColor(tone),
                  backgroundColor: `${getToneColor(tone)}15`,
                }}
              >
                {tone} ({count})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Top locations */}
      {overview.top_locations.length > 0 && (
        <div>
          <span className="text-xs text-gray-400 block mb-2">Top Locations</span>
          <div className="flex flex-wrap gap-2">
            {overview.top_locations.map(([loc, count]) => (
              <span
                key={loc}
                className="px-2 py-1 bg-gray-800 rounded-full text-[10px] text-gray-400"
              >
                📍 {loc} ({count})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Analytics Page
// =============================================================================
export default function AnalyticsPage() {
  const [showId, setShowId] = useState<number | null>(null);
  const [episodeId, setEpisodeId] = useState<number | null>(null);
  const [episodeLabel, setEpisodeLabel] = useState("");

  // Data states
  const [overview, setOverview] = useState<EpisodeOverview | null>(null);
  const [timeline, setTimeline] = useState<MoodTimelineEntry[]>([]);
  const [screenTime, setScreenTime] = useState<ScreenTimeChar[]>([]);
  const [dna, setDna] = useState<SceneDNAType | null>(null);
  const [dnaSceneId, setDnaSceneId] = useState("");
  const [loading, setLoading] = useState(false);

  function handleEpisodeSelect(sId: number, eId: number, label: string) {
    setShowId(sId);
    setEpisodeId(eId);
    setEpisodeLabel(label);
  }

  // Load analytics when episode is selected
  useEffect(() => {
    if (!episodeId || !showId) return;
    setLoading(true);

    Promise.all([
      getEpisodeOverview(episodeId).then(setOverview).catch(() => setOverview(null)),
      getMoodTimeline(episodeId).then((d) => setTimeline(d.timeline)).catch(() => setTimeline([])),
      getScreenTime(showId).then((d) => setScreenTime(d.characters)).catch(() => setScreenTime([])),
    ]).finally(() => setLoading(false));
  }, [episodeId, showId]);

  // Scene DNA lookup
  async function loadDNA() {
    const id = Number(dnaSceneId);
    if (!id) return;
    try {
      const data = await getSceneDNA(id);
      setDna(data);
    } catch {
      setDna(null);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-simpsons-yellow">Analytics</h1>
        <p className="text-gray-400 text-sm mt-1">
          Scene DNA, mood timelines, screen time, dialog search, AI recommendations
        </p>
      </div>

      {/* Episode picker */}
      <EpisodePicker onSelect={handleEpisodeSelect} />

      {loading && (
        <div className="text-center py-8">
          <p className="text-gray-500 animate-pulse">Loading analytics for {episodeLabel}...</p>
        </div>
      )}

      {/* Episode overview */}
      {overview && !loading && (
        <section className="bg-gray-950 border border-gray-800 rounded-xl p-6">
          <EpisodeOverviewPanel overview={overview} />
        </section>
      )}

      {/* Mood Timeline */}
      {timeline.length > 0 && !loading && (
        <section className="bg-gray-950 border border-gray-800 rounded-xl p-6">
          <MoodTimeline data={timeline} onSceneClick={(id) => {
            setDnaSceneId(String(id));
            getSceneDNA(id).then(setDna).catch(() => setDna(null));
          }} />
        </section>
      )}

      {/* Screen Time */}
      {screenTime.length > 0 && !loading && (
        <section className="bg-gray-950 border border-gray-800 rounded-xl p-6">
          <ScreenTimeChart characters={screenTime} />
        </section>
      )}

      {/* Scene DNA */}
      <section className="bg-gray-950 border border-gray-800 rounded-xl p-6">
        <div className="flex items-end gap-3 mb-4">
          <div>
            <h3 className="text-lg font-semibold">Scene DNA</h3>
            <p className="text-xs text-gray-500">Enter a scene ID for its radar fingerprint</p>
          </div>
          <input
            value={dnaSceneId}
            onChange={(e) => setDnaSceneId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadDNA()}
            placeholder="Scene ID"
            type="number"
            className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm focus:border-simpsons-yellow focus:outline-none"
          />
          <button
            onClick={loadDNA}
            className="bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-sm transition"
          >
            Load
          </button>
        </div>
        {dna && <SceneDNARadar dna={dna} />}
      </section>

      {/* Dialog Search + AI Recommender side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-gray-950 border border-gray-800 rounded-xl p-6">
          <DialogSearchPanel />
        </section>
        <section className="bg-gray-950 border border-gray-800 rounded-xl p-6">
          <SimilarScenesPanel />
        </section>
      </div>
    </div>
  );
}
