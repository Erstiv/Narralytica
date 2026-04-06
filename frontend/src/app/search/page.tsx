"use client";

import { useState, useRef, useEffect } from "react";
import {
  searchScenes,
  getSearchFacets,
  getShows,
  type SearchResult,
  type Scene,
  type MetadataDensity,
  type SearchFacets,
  type SearchRequest,
  type ShowSummary,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

// --- Density Slider ---
function DensitySlider({ value, onChange }: { value: MetadataDensity; onChange: (v: MetadataDensity) => void }) {
  const levels: MetadataDensity[] = ["essential", "standard", "maximum"];
  const labels = { essential: "Essential", standard: "Standard", maximum: "Maximum" };
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-gray-500 text-xs">Density:</span>
      <div className="flex bg-gray-800 rounded-lg overflow-hidden">
        {levels.map((level) => (
          <button
            key={level}
            onClick={() => onChange(level)}
            className={`px-2.5 py-1 text-xs font-medium transition ${
              level === value ? "bg-simpsons-yellow text-black" : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {labels[level]}
          </button>
        ))}
      </div>
    </div>
  );
}

// --- Filter Chip ---
function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 bg-blue-900/60 text-blue-300 px-2.5 py-1 rounded-full text-xs">
      {label}
      <button onClick={onRemove} className="hover:text-white ml-0.5">&times;</button>
    </span>
  );
}

// --- Faceted Sidebar ---
function FilterSidebar({
  facets,
  filters,
  onFilterChange,
}: {
  facets: SearchFacets | null;
  filters: Partial<SearchRequest>;
  onFilterChange: (key: string, value: string | number | undefined) => void;
}) {
  const [charSearch, setCharSearch] = useState("");

  if (!facets) return null;

  const filteredChars = facets.characters.filter((c) =>
    c.toLowerCase().includes(charSearch.toLowerCase())
  );

  return (
    <div className="w-56 flex-shrink-0 space-y-5 text-sm">
      <h3 className="font-semibold text-gray-300 uppercase text-xs tracking-wider">Filters</h3>

      {/* Characters */}
      <div>
        <label className="text-gray-400 text-xs font-medium block mb-1">Character</label>
        <input
          type="text"
          placeholder="Search characters..."
          value={charSearch}
          onChange={(e) => setCharSearch(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs mb-1"
        />
        <div className="max-h-32 overflow-y-auto space-y-0.5">
          {(charSearch ? filteredChars : filteredChars.slice(0, 15)).map((c) => (
            <button
              key={c}
              onClick={() => onFilterChange("characters", c)}
              className={`block w-full text-left text-xs px-2 py-1 rounded hover:bg-gray-800 transition truncate ${
                (filters.characters || []).includes(c) ? "text-simpsons-yellow bg-gray-800" : "text-gray-400"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Tone */}
      <div>
        <label className="text-gray-400 text-xs font-medium block mb-1">Tone</label>
        <select
          value={filters.tone || ""}
          onChange={(e) => onFilterChange("tone", e.target.value || undefined)}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs"
        >
          <option value="">Any</option>
          {facets.tones.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {/* Plot Significance */}
      <div>
        <label className="text-gray-400 text-xs font-medium block mb-1">Plot Significance</label>
        <select
          value={filters.plot_significance || ""}
          onChange={(e) => onFilterChange("plot_significance", e.target.value || undefined)}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs"
        >
          <option value="">Any</option>
          {facets.plot_significance.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {/* Setting */}
      <div>
        <label className="text-gray-400 text-xs font-medium block mb-1">Setting</label>
        <select
          value={filters.setting_type || ""}
          onChange={(e) => onFilterChange("setting_type", e.target.value || undefined)}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs"
        >
          <option value="">Any</option>
          {facets.setting_types.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Explicitness cap */}
      <div>
        <label className="text-gray-400 text-xs font-medium block mb-1">
          Max Violence: {filters.max_explicitness_violence !== undefined ? `${Math.round((filters.max_explicitness_violence ?? 1) * 100)}%` : "Any"}
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={filters.max_explicitness_violence ?? 1}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            onFilterChange("max_explicitness_violence", v >= 1 ? undefined : v);
          }}
          className="w-full accent-simpsons-yellow"
        />
      </div>
    </div>
  );
}

// --- Explicitness Bar ---
function ExplicitnessBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct <= 20 ? "bg-green-500" : pct <= 50 ? "bg-yellow-500" : pct <= 75 ? "bg-orange-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400 w-20">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-gray-500 w-8 text-right">{pct}%</span>
    </div>
  );
}

// --- Scene Detail Panel ---
function SceneDetail({ scene, density }: { scene: Scene; density: MetadataDensity }) {
  return (
    <div className="mt-3 pt-3 border-t border-gray-800 space-y-4 text-sm">
      {density !== "essential" && (
        <>
          {(scene.location || scene.time_of_day || scene.setting_type) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Location</h4>
              <p className="text-gray-300">{[scene.location, scene.setting_type, scene.time_of_day].filter(Boolean).join(" · ")}</p>
            </div>
          )}
          {(scene.mood_ambience || scene.tone || scene.scene_pacing) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Mood & Tone</h4>
              <div className="flex flex-wrap gap-1">
                {[scene.mood_ambience, scene.tone, scene.scene_pacing].filter(Boolean).map((tag, i) => (
                  <span key={i} className="bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded text-xs">{tag}</span>
                ))}
              </div>
            </div>
          )}
          {(scene.actions || scene.visual_gags || scene.dialog_based_humor) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Actions & Humor</h4>
              {scene.actions && <p className="text-gray-300">{scene.actions}</p>}
              {scene.visual_gags && <p className="text-gray-400 mt-1"><span className="text-yellow-400">Visual gags:</span> {scene.visual_gags}</p>}
              {scene.dialog_based_humor && <p className="text-gray-400 mt-1"><span className="text-yellow-400">Dialog humor:</span> {scene.dialog_based_humor}</p>}
            </div>
          )}
          {(scene.tropes_memes ?? []).length > 0 && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Tropes</h4>
              <div className="flex flex-wrap gap-1">
                {scene.tropes_memes.map((t, i) => <span key={i} className="bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded text-xs">{t}</span>)}
              </div>
            </div>
          )}
          {(scene.explicitness_language > 0 || scene.explicitness_violence > 0 || scene.explicitness_substance > 0) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Explicitness</h4>
              <div className="space-y-1">
                <ExplicitnessBar label="Language" value={scene.explicitness_language} />
                <ExplicitnessBar label="Violence" value={scene.explicitness_violence} />
                <ExplicitnessBar label="Sexual" value={scene.explicitness_sexual} />
                <ExplicitnessBar label="Substance" value={scene.explicitness_substance} />
                <ExplicitnessBar label="Thematic" value={scene.explicitness_thematic} />
              </div>
            </div>
          )}
          {scene.plot_significance && (
            <div className="flex items-center gap-2">
              <span className="text-gray-400 text-xs">Plot:</span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                scene.plot_significance === "critical" ? "bg-red-900 text-red-300" :
                scene.plot_significance === "high" ? "bg-orange-900 text-orange-300" :
                scene.plot_significance === "medium" ? "bg-yellow-900 text-yellow-300" : "bg-gray-800 text-gray-400"
              }`}>{scene.plot_significance}</span>
            </div>
          )}
        </>
      )}
      {density === "maximum" && (
        <>
          {(scene.camera_shot_type || scene.camera_movement || scene.lighting) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Cinematography</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                {scene.camera_shot_type && <p><span className="text-gray-500">Shot:</span> <span className="text-gray-300">{scene.camera_shot_type}</span></p>}
                {scene.camera_movement && <p><span className="text-gray-500">Movement:</span> <span className="text-gray-300">{scene.camera_movement}</span></p>}
                {scene.lighting && <p><span className="text-gray-500">Lighting:</span> <span className="text-gray-300">{scene.lighting}</span></p>}
                {scene.scene_composition && <p><span className="text-gray-500">Composition:</span> <span className="text-gray-300">{scene.scene_composition}</span></p>}
              </div>
            </div>
          )}
          {(scene.music_present || scene.sound_effects) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Audio</h4>
              {scene.music_description && <p className="text-gray-300 text-xs"><span className="text-green-400">&#9834;</span> {scene.music_description}</p>}
              {scene.sound_effects && <p className="text-gray-400 text-xs">SFX: {scene.sound_effects}</p>}
            </div>
          )}
          {scene.emotional_arc && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Emotional Arc</h4>
              <p className="text-gray-300 text-xs">{scene.emotional_arc}</p>
            </div>
          )}
          {(scene.cultural_references ?? []).length > 0 && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Cultural References</h4>
              <div className="flex flex-wrap gap-1">
                {scene.cultural_references.map((ref, i) => <span key={i} className="bg-emerald-900/50 text-emerald-300 px-2 py-0.5 rounded text-xs">{ref}</span>)}
              </div>
            </div>
          )}
          {(scene.color_palette ?? []).length > 0 && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Color Palette</h4>
              <div className="flex gap-1">
                {scene.color_palette.map((color, i) => (
                  <div key={i} className="w-6 h-6 rounded border border-gray-700" style={{ backgroundColor: color.startsWith("#") ? color : `#${color}` }} title={color} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// --- Download Menu ---
function DownloadMenu({ sceneId, episodeId }: { sceneId: number; episodeId: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition"
      >
        Export &#9662;
      </button>
      {open && (
        <div className="absolute top-full mt-1 right-0 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 z-20 min-w-[160px]">
          <a
            href={`${API_URL}/api/export/${episodeId}/metadata-csv`}
            className="block px-3 py-1.5 text-xs hover:bg-gray-700 transition"
            onClick={() => setOpen(false)}
          >
            Metadata CSV
          </a>
          <a
            href={`${API_URL}/api/export/${episodeId}/script-json`}
            className="block px-3 py-1.5 text-xs hover:bg-gray-700 transition"
            onClick={() => setOpen(false)}
          >
            Script JSON
          </a>
          <a
            href={`${API_URL}/api/export/${episodeId}/metadata-json`}
            className="block px-3 py-1.5 text-xs hover:bg-gray-700 transition"
            onClick={() => setOpen(false)}
          >
            Full Metadata JSON
          </a>
          <a
            href={`${API_URL}/api/export/${episodeId}/srt`}
            className="block px-3 py-1.5 text-xs hover:bg-gray-700 transition"
            onClick={() => setOpen(false)}
          >
            SRT Subtitles
          </a>
          <a
            href={`${API_URL}/api/export/${episodeId}/script-docx`}
            className="block px-3 py-1.5 text-xs hover:bg-gray-700 transition"
            onClick={() => setOpen(false)}
          >
            Script DOCX
          </a>
          <a
            href={`${API_URL}/api/export/${episodeId}/vtt`}
            className="block px-3 py-1.5 text-xs hover:bg-gray-700 transition"
            onClick={() => setOpen(false)}
          >
            VTT Subtitles
          </a>
          <hr className="border-gray-700 my-1" />
          <a
            href={`${API_URL}/api/export/${episodeId}/metadata-pdf`}
            className="block px-3 py-1.5 text-xs hover:bg-gray-700 transition text-simpsons-yellow font-medium"
            onClick={() => setOpen(false)}
          >
            Metadata Script PDF
          </a>
        </div>
      )}
    </div>
  );
}

// --- Main Search Page ---
export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [facets, setFacets] = useState<SearchFacets | null>(null);
  const [filters, setFilters] = useState<Partial<SearchRequest>>({});
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [playingScene, setPlayingScene] = useState<number | null>(null);
  const [expandedScene, setExpandedScene] = useState<number | null>(null);
  const [density, setDensity] = useState<MetadataDensity>("standard");
  const [showFilters, setShowFilters] = useState(false);
  const [shows, setShows] = useState<ShowSummary[]>([]);
  const [scopeShowId, setScopeShowId] = useState<number | undefined>(undefined);
  const [scopeLabel, setScopeLabel] = useState("All Shows");
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    getSearchFacets().then(setFacets).catch(() => {});
    getShows().then(setShows).catch(() => {});
  }, []);

  function handleFilterChange(key: string, value: string | number | undefined) {
    setFilters((prev) => {
      const next = { ...prev };
      if (key === "characters") {
        const chars = [...(next.characters || [])];
        const strVal = String(value);
        const idx = chars.indexOf(strVal);
        if (idx >= 0) chars.splice(idx, 1);
        else chars.push(strVal);
        next.characters = chars.length > 0 ? chars : undefined;
      } else {
        (next as Record<string, unknown>)[key] = value;
      }
      return next;
    });
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setPlayingScene(null);
    setExpandedScene(null);
    try {
      const request: SearchRequest = { query, limit: 30, ...filters, show_id: scopeShowId };
      const scenes = await searchScenes(request);
      setResults(scenes);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
      setSearched(true);
    }
  }

  function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  // Active filter chips
  const activeFilters: { label: string; key: string; value?: string }[] = [];
  if (filters.characters) {
    filters.characters.forEach((c) => activeFilters.push({ label: c, key: "characters", value: c }));
  }
  if (filters.tone) activeFilters.push({ label: `Tone: ${filters.tone}`, key: "tone" });
  if (filters.plot_significance) activeFilters.push({ label: `Plot: ${filters.plot_significance}`, key: "plot_significance" });
  if (filters.setting_type) activeFilters.push({ label: `Setting: ${filters.setting_type}`, key: "setting_type" });
  if (filters.max_explicitness_violence !== undefined) activeFilters.push({ label: `Violence ≤ ${Math.round(filters.max_explicitness_violence * 100)}%`, key: "max_explicitness_violence" });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-3xl font-bold text-simpsons-yellow">Search Scenes</h1>
        <div className="flex items-center gap-3">
          <DensitySlider value={density} onChange={setDensity} />
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded transition"
          >
            {showFilters ? "Hide Filters" : "Show Filters"}
          </button>
        </div>
      </div>

      {/* Scope selector */}
      <div className="flex items-center gap-3 text-sm">
        <span className="text-gray-500">Searching:</span>
        <div className="flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => { setScopeShowId(undefined); setScopeLabel("All Shows"); }}
            className={`px-3 py-1.5 text-xs font-medium transition ${
              !scopeShowId ? "bg-simpsons-yellow text-black" : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            All Shows
          </button>
          {shows.filter(s => (s.episode_count ?? 0) > 0).map((s) => (
            <button
              key={s.id}
              onClick={() => { setScopeShowId(s.id); setScopeLabel(s.name); }}
              className={`px-3 py-1.5 text-xs font-medium transition border-l border-gray-700 ${
                scopeShowId === s.id ? "bg-simpsons-yellow text-black" : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>
        {scopeShowId && (
          <span className="text-xs text-gray-500 italic">
            Filtering to {scopeLabel} only
          </span>
        )}
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={scopeShowId ? `Search within ${scopeLabel}...` : "Search across all shows..."}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-simpsons-yellow transition"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-simpsons-yellow text-black font-semibold px-6 py-3 rounded-lg hover:bg-yellow-400 transition disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Active filter chips */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {activeFilters.map((f, i) => (
            <FilterChip
              key={i}
              label={f.label}
              onRemove={() => handleFilterChange(f.key, f.key === "characters" ? f.value : undefined)}
            />
          ))}
          <button
            onClick={() => setFilters({})}
            className="text-xs text-gray-500 hover:text-gray-300 transition"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Video overlay */}
      {playingScene !== null && (() => {
        const playResult = results.find((r) => r.scene.id === playingScene);
        return (
          <div className="fixed inset-0 bg-black/90 z-50 flex flex-col items-center justify-center p-8">
            <div className="relative max-w-4xl w-full">
              <div className="flex items-center justify-between mb-4">
                <div className="text-white text-sm">
                  <span className="text-simpsons-yellow font-semibold">Scene Preview</span>
                  {playResult && (
                    <span className="text-gray-400 ml-3">
                      {formatTime(playResult.scene.start_timestamp)} &ndash; {formatTime(playResult.scene.end_timestamp)}
                      {playResult.scene.location && <span className="ml-2 text-gray-500">| {playResult.scene.location}</span>}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setPlayingScene(null)}
                  className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
                >
                  &larr; Back to Results
                </button>
              </div>
              {playResult?.scene.description_text && (
                <p className="text-gray-300 text-sm mb-3 italic">{playResult.scene.description_text}</p>
              )}
              <video
                ref={videoRef}
                controls
                autoPlay
                className="w-full rounded-lg bg-black"
                src={`${API_URL}/api/media/clip/${playResult?.scene.id}`}
              >
                <p className="text-gray-500 text-center p-8">Video preview not available</p>
              </video>
            </div>
          </div>
        );
      })()}

      {/* Main content: sidebar + results */}
      <div className="flex gap-6">
        {/* Sidebar */}
        {showFilters && (
          <FilterSidebar facets={facets} filters={filters} onFilterChange={handleFilterChange} />
        )}

        {/* Results */}
        <div className="flex-1 space-y-4">
          {searched && results.length === 0 && (
            <p className="text-gray-500 text-center py-8">No scenes found. Try a different query or adjust filters.</p>
          )}

          {searched && results.length > 0 && (
            <p className="text-xs text-gray-500">{results.length} results</p>
          )}

          {results.map((result) => {
            const isExpanded = expandedScene === result.scene.id;
            return (
              <div key={result.scene.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <div className="flex gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs text-blue-400 bg-blue-900/40 px-2 py-0.5 rounded font-medium">
                        {result.episode_label || `Ep ${result.scene.episode_id}`}
                        {result.episode_title && <span className="text-blue-300/60 ml-1">{result.episode_title}</span>}
                      </span>
                      <span className="text-sm text-gray-400">
                        {formatTime(result.scene.start_timestamp)} &ndash; {formatTime(result.scene.end_timestamp)}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-900 text-blue-300">
                        {(result.similarity * 100).toFixed(0)}% match
                      </span>
                      {result.scene.overall_confidence != null && (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          result.scene.overall_confidence >= 0.8 ? "bg-green-900 text-green-300" :
                          result.scene.overall_confidence >= 0.5 ? "bg-yellow-900 text-yellow-300" : "bg-red-900 text-red-300"
                        }`}>
                          {(result.scene.overall_confidence * 100).toFixed(0)}% conf
                        </span>
                      )}
                      {density !== "essential" && result.scene.location && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-400">{result.scene.location}</span>
                      )}
                      {density !== "essential" && result.scene.tone && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-purple-900/50 text-purple-300">{result.scene.tone}</span>
                      )}
                    </div>

                    {(result.scene.characters_present ?? []).length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-1">
                        {result.scene.characters_present.map((c) => (
                          <span key={c.name} className="bg-gray-800 text-gray-300 px-2 py-0.5 rounded text-xs">{c.name}</span>
                        ))}
                      </div>
                    )}

                    {(result.scene.key_dialog ?? []).length > 0 && (
                      <p className="text-sm text-gray-300 truncate">
                        <span className="text-simpsons-yellow">{result.scene.key_dialog[0].speaker}:</span>{" "}
                        &ldquo;{result.scene.key_dialog[0].exact_quote}&rdquo;
                      </p>
                    )}

                    {result.scene.description_text && (
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">{result.scene.description_text}</p>
                    )}

                    {result.match_reason && (
                      <p className="text-xs text-amber-600/80 mt-1 italic">
                        Match: {result.match_reason}
                      </p>
                    )}

                    <div className="flex gap-2 mt-2 flex-wrap">
                      <button onClick={() => setPlayingScene(result.scene.id)} className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition">Preview</button>
                      {density !== "essential" && (
                        <button onClick={() => setExpandedScene(isExpanded ? null : result.scene.id)} className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition">
                          {isExpanded ? "Hide Details" : "Show Details"}
                        </button>
                      )}
                      <DownloadMenu sceneId={result.scene.id} episodeId={result.scene.episode_id} />
                    </div>
                  </div>
                </div>

                {isExpanded && density !== "essential" && (
                  <SceneDetail scene={result.scene} density={density} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
