"use client";

import { useState, useRef } from "react";
import { searchScenes, type SearchResult, type Scene, type MetadataDensity } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

// --- Metadata Density Slider ---
function DensitySlider({
  value,
  onChange,
}: {
  value: MetadataDensity;
  onChange: (v: MetadataDensity) => void;
}) {
  const levels: MetadataDensity[] = ["essential", "standard", "maximum"];
  const labels = { essential: "Essential", standard: "Standard", maximum: "Maximum" };
  const idx = levels.indexOf(value);

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-gray-400">Density:</span>
      <div className="flex bg-gray-800 rounded-lg overflow-hidden">
        {levels.map((level, i) => (
          <button
            key={level}
            onClick={() => onChange(level)}
            className={`px-3 py-1.5 text-xs font-medium transition ${
              i === idx
                ? "bg-simpsons-yellow text-black"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {labels[level]}
          </button>
        ))}
      </div>
    </div>
  );
}

// --- Explicitness Bar ---
function ExplicitnessBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct <= 20 ? "bg-green-500" : pct <= 50 ? "bg-yellow-500" : pct <= 75 ? "bg-orange-500" : "bg-red-500";
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
      {/* --- STANDARD fields --- */}
      {density !== "essential" && (
        <>
          {/* Location & Setting */}
          {(scene.location || scene.time_of_day || scene.setting_type) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Location</h4>
              <p className="text-gray-300">
                {[scene.location, scene.setting_type, scene.time_of_day].filter(Boolean).join(" · ")}
              </p>
            </div>
          )}

          {/* Mood & Tone */}
          {(scene.mood_ambience || scene.tone || scene.scene_pacing) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Mood & Tone</h4>
              <div className="flex flex-wrap gap-1">
                {[scene.mood_ambience, scene.tone, scene.scene_pacing].filter(Boolean).map((tag, i) => (
                  <span key={i} className="bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded text-xs">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions & Humor */}
          {(scene.actions || scene.visual_gags || scene.dialog_based_humor) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Actions & Humor</h4>
              {scene.actions && <p className="text-gray-300">{scene.actions}</p>}
              {scene.visual_gags && (
                <p className="text-gray-400 mt-1">
                  <span className="text-yellow-400">Visual gags:</span> {scene.visual_gags}
                </p>
              )}
              {scene.dialog_based_humor && (
                <p className="text-gray-400 mt-1">
                  <span className="text-yellow-400">Dialog humor:</span> {scene.dialog_based_humor}
                </p>
              )}
            </div>
          )}

          {/* Tropes */}
          {(scene.tropes_memes ?? []).length > 0 && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Tropes & Memes</h4>
              <div className="flex flex-wrap gap-1">
                {scene.tropes_memes.map((t, i) => (
                  <span key={i} className="bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded text-xs">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Explicitness */}
          {(scene.explicitness_language > 0 ||
            scene.explicitness_violence > 0 ||
            scene.explicitness_sexual > 0 ||
            scene.explicitness_substance > 0 ||
            scene.explicitness_thematic > 0) && (
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

          {/* Plot Significance */}
          {scene.plot_significance && (
            <div className="flex items-center gap-2">
              <span className="text-gray-400 text-xs">Plot:</span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  scene.plot_significance === "critical"
                    ? "bg-red-900 text-red-300"
                    : scene.plot_significance === "high"
                      ? "bg-orange-900 text-orange-300"
                      : scene.plot_significance === "medium"
                        ? "bg-yellow-900 text-yellow-300"
                        : "bg-gray-800 text-gray-400"
                }`}
              >
                {scene.plot_significance}
              </span>
            </div>
          )}
        </>
      )}

      {/* --- MAXIMUM fields --- */}
      {density === "maximum" && (
        <>
          {/* Camera & Cinematography */}
          {(scene.camera_shot_type || scene.camera_movement || scene.scene_composition || scene.lighting) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Cinematography</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                {scene.camera_shot_type && (
                  <p><span className="text-gray-500">Shot:</span> <span className="text-gray-300">{scene.camera_shot_type}</span></p>
                )}
                {scene.camera_movement && (
                  <p><span className="text-gray-500">Movement:</span> <span className="text-gray-300">{scene.camera_movement}</span></p>
                )}
                {scene.lighting && (
                  <p><span className="text-gray-500">Lighting:</span> <span className="text-gray-300">{scene.lighting}</span></p>
                )}
                {scene.scene_composition && (
                  <p><span className="text-gray-500">Composition:</span> <span className="text-gray-300">{scene.scene_composition}</span></p>
                )}
              </div>
              {scene.visual_style_notes && (
                <p className="text-gray-400 mt-1 text-xs italic">{scene.visual_style_notes}</p>
              )}
            </div>
          )}

          {/* Audio & Music */}
          {(scene.music_present || scene.sound_effects || scene.ambient_audio) && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Audio</h4>
              {scene.music_present && scene.music_description && (
                <p className="text-gray-300 text-xs">
                  <span className="text-green-400">&#9834;</span> {scene.music_description}
                </p>
              )}
              {scene.sound_effects && (
                <p className="text-gray-400 text-xs">SFX: {scene.sound_effects}</p>
              )}
              {scene.ambient_audio && (
                <p className="text-gray-400 text-xs">Ambient: {scene.ambient_audio}</p>
              )}
            </div>
          )}

          {/* Emotional Arc */}
          {scene.emotional_arc && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Emotional Arc</h4>
              <p className="text-gray-300 text-xs">{scene.emotional_arc}</p>
            </div>
          )}

          {/* Cultural References */}
          {(scene.cultural_references ?? []).length > 0 && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Cultural References</h4>
              <div className="flex flex-wrap gap-1">
                {scene.cultural_references.map((ref, i) => (
                  <span key={i} className="bg-emerald-900/50 text-emerald-300 px-2 py-0.5 rounded text-xs">
                    {ref}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Continuity */}
          {scene.continuity_notes && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Continuity</h4>
              <p className="text-gray-300 text-xs">{scene.continuity_notes}</p>
            </div>
          )}

          {/* Scene Transitions & Text */}
          {(scene.scene_transitions || scene.text_on_screen) && (
            <div className="flex flex-wrap gap-4 text-xs">
              {scene.scene_transitions && (
                <p><span className="text-gray-500">Transitions:</span> <span className="text-gray-300">{scene.scene_transitions}</span></p>
              )}
              {scene.text_on_screen && (
                <p><span className="text-gray-500">On-screen text:</span> <span className="text-gray-300">{scene.text_on_screen}</span></p>
              )}
            </div>
          )}

          {/* Color Palette */}
          {(scene.color_palette ?? []).length > 0 && (
            <div>
              <h4 className="text-gray-400 text-xs font-semibold uppercase mb-1">Color Palette</h4>
              <div className="flex gap-1">
                {scene.color_palette.map((color, i) => (
                  <div
                    key={i}
                    className="w-6 h-6 rounded border border-gray-700"
                    style={{ backgroundColor: color.startsWith("#") ? color : `#${color}` }}
                    title={color}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// --- Main Search Page ---
export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [playingScene, setPlayingScene] = useState<number | null>(null);
  const [expandedScene, setExpandedScene] = useState<number | null>(null);
  const [density, setDensity] = useState<MetadataDensity>("standard");
  const videoRef = useRef<HTMLVideoElement>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setPlayingScene(null);
    setExpandedScene(null);
    try {
      const scenes = await searchScenes({ query, limit: 20 });
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

  function getSceneNum(result: SearchResult): string {
    const sorted = [...results].sort(
      (a, b) => a.scene.start_timestamp - b.scene.start_timestamp
    );
    const idx = sorted.findIndex((r) => r.scene.id === result.scene.id);
    return String(idx + 1).padStart(2, "0");
  }

  function thumbUrl(result: SearchResult): string {
    return `${API_URL}/api/media/thumbs/scene_${getSceneNum(result)}.jpg`;
  }

  function clipUrl(result: SearchResult): string {
    return `${API_URL}/api/media/clips/scene_${getSceneNum(result)}.mp4`;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-3xl font-bold text-simpsons-yellow">Search Scenes</h1>
        <DensitySlider value={density} onChange={setDensity} />
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='e.g. "Homer frustrated with Mr. Burns in a union meeting"'
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

      {/* Video player overlay */}
      {playingScene !== null && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8">
          <div className="relative max-w-4xl w-full">
            <button
              onClick={() => setPlayingScene(null)}
              className="absolute -top-10 right-0 text-white hover:text-simpsons-yellow text-xl"
            >
              Close
            </button>
            <video
              ref={videoRef}
              controls
              autoPlay
              className="w-full rounded-lg"
              src={(() => {
                const r = results.find((r) => r.scene.id === playingScene);
                return r ? clipUrl(r) : "";
              })()}
            />
          </div>
        </div>
      )}

      {/* Results */}
      <div className="space-y-4">
        {searched && results.length === 0 && (
          <p className="text-gray-500 text-center py-8">
            No scenes found. Try a different query or index an episode first.
          </p>
        )}

        {results.map((result) => {
          const isExpanded = expandedScene === result.scene.id;

          return (
            <div
              key={result.scene.id}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4"
            >
              <div className="flex gap-4">
                {/* Thumbnail */}
                <img
                  src={thumbUrl(result)}
                  alt={`Scene at ${formatTime(result.scene.start_timestamp)}`}
                  className="w-40 h-24 object-cover rounded flex-shrink-0 bg-gray-800 cursor-pointer hover:opacity-80 transition"
                  onClick={() => setPlayingScene(result.scene.id)}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-sm text-gray-400">
                      {formatTime(result.scene.start_timestamp)} &ndash;{" "}
                      {formatTime(result.scene.end_timestamp)}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-900 text-blue-300">
                      {(result.similarity * 100).toFixed(0)}% match
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        result.scene.overall_confidence >= 0.8
                          ? "bg-green-900 text-green-300"
                          : result.scene.overall_confidence >= 0.5
                            ? "bg-yellow-900 text-yellow-300"
                            : "bg-red-900 text-red-300"
                      }`}
                    >
                      {(result.scene.overall_confidence * 100).toFixed(0)}% conf
                    </span>
                    {/* Standard+ badges */}
                    {density !== "essential" && result.scene.location && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-gray-800 text-gray-400">
                        {result.scene.location}
                      </span>
                    )}
                    {density !== "essential" && result.scene.tone && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-purple-900/50 text-purple-300">
                        {result.scene.tone}
                      </span>
                    )}
                  </div>

                  {/* Characters */}
                  {(result.scene.characters_present ?? []).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-1">
                      {result.scene.characters_present.map((c) => (
                        <span
                          key={c.name}
                          className="bg-gray-800 text-gray-300 px-2 py-0.5 rounded text-xs"
                        >
                          {c.name}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Dialog snippet */}
                  {(result.scene.key_dialog ?? []).length > 0 && (
                    <p className="text-sm text-gray-300 truncate">
                      <span className="text-simpsons-yellow">
                        {result.scene.key_dialog[0].speaker}:
                      </span>{" "}
                      &ldquo;
                      {result.scene.key_dialog[0].exact_quote}
                      &rdquo;
                    </p>
                  )}

                  {result.scene.description_text && (
                    <p className="text-sm text-gray-500 mt-1 truncate">
                      {result.scene.description_text}
                    </p>
                  )}

                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => setPlayingScene(result.scene.id)}
                      className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition"
                    >
                      Preview
                    </button>
                    <a
                      href={clipUrl(result)}
                      download
                      className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition"
                    >
                      Download Clip
                    </a>
                    {density !== "essential" && (
                      <button
                        onClick={() =>
                          setExpandedScene(isExpanded ? null : result.scene.id)
                        }
                        className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition"
                      >
                        {isExpanded ? "Hide Details" : "Show Details"}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Expanded detail panel */}
              {isExpanded && density !== "essential" && (
                <SceneDetail scene={result.scene} density={density} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
