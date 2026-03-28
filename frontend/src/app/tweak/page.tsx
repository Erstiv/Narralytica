"use client";

import { useEffect, useState, useCallback } from "react";
import {
  searchScenes,
  createBridgeTweak,
  createRestyleTweak,
  createRedubTweak,
  getTweaks,
  getTweak,
  deleteTweak,
  getVoicePresets,
  type Scene,
  type SearchResult,
  type TweakOut,
  type VoicePreset,
} from "@/lib/api";

// =============================================================================
// Mode tabs
// =============================================================================
type Mode = "bridge" | "restyle" | "redub";

const MODE_INFO: Record<Mode, { label: string; icon: string; engine: string; desc: string }> = {
  bridge: {
    label: "Bridge",
    icon: "🎬",
    engine: "Veo 3.1",
    desc: "Generate a transition video between two scenes",
  },
  restyle: {
    label: "Restyle",
    icon: "🎨",
    engine: "Imagen 3",
    desc: "Apply a visual style to a scene frame",
  },
  redub: {
    label: "Redub",
    icon: "🎙️",
    engine: "Google TTS",
    desc: "Replace dialog audio with new voices",
  },
};

function ModeTabs({ active, onChange }: { active: Mode; onChange: (m: Mode) => void }) {
  return (
    <div className="flex gap-1 bg-gray-900 rounded-lg p-1">
      {(Object.keys(MODE_INFO) as Mode[]).map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition ${
            active === m
              ? "bg-simpsons-yellow text-black"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
          }`}
        >
          <span>{MODE_INFO[m].icon}</span>
          <span>{MODE_INFO[m].label}</span>
          <span className="text-[10px] opacity-60">({MODE_INFO[m].engine})</span>
        </button>
      ))}
    </div>
  );
}

// =============================================================================
// Scene Picker — inline search to select a scene
// =============================================================================
function ScenePicker({
  label,
  scene,
  onSelect,
  onClear,
}: {
  label: string;
  scene: Scene | null;
  onSelect: (s: Scene) => void;
  onClear: () => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [open, setOpen] = useState(false);

  async function doSearch() {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await searchScenes({ query, limit: 8 });
      setResults(res);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  function formatTime(s: number) {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  }

  if (scene) {
    const chars = (scene.characters_present || []).map((c) => c.name).join(", ");
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-simpsons-yellow font-medium">{label}</span>
          <button onClick={onClear} className="text-xs text-gray-500 hover:text-red-400">
            Clear
          </button>
        </div>
        <p className="text-sm font-medium">
          Scene #{scene.id} &middot; {formatTime(scene.start_timestamp)}–{formatTime(scene.end_timestamp)}
        </p>
        <p className="text-xs text-gray-400 mt-1">{scene.location || "Unknown location"}</p>
        {chars && <p className="text-xs text-gray-500 mt-0.5">{chars}</p>}
        <p className="text-xs text-gray-600 mt-1 line-clamp-2">{scene.description_text}</p>
        {scene.tone && (
          <span className="inline-block mt-2 px-2 py-0.5 bg-gray-800 rounded-full text-[10px] text-gray-400">
            {scene.tone}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="bg-gray-900 border border-gray-800 border-dashed rounded-lg p-4">
        <span className="text-xs text-gray-500 block mb-2">{label}</span>
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
            placeholder="Search scenes..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-simpsons-yellow focus:outline-none"
          />
          <button
            onClick={doSearch}
            disabled={searching}
            className="bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded text-sm transition disabled:opacity-50"
          >
            {searching ? "..." : "Search"}
          </button>
        </div>

        {open && results.length > 0 && (
          <div className="mt-3 space-y-1 max-h-48 overflow-y-auto">
            {results.map((r) => {
              const chars = (r.scene.characters_present || [])
                .slice(0, 3)
                .map((c) => c.name)
                .join(", ");
              return (
                <button
                  key={r.scene.id}
                  onClick={() => {
                    onSelect(r.scene);
                    setOpen(false);
                    setQuery("");
                    setResults([]);
                  }}
                  className="w-full text-left p-2 rounded hover:bg-gray-800 transition"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-gray-500">
                      #{r.scene.id} &middot; {formatTime(r.scene.start_timestamp)}
                    </span>
                    <span className="text-[10px] text-gray-600">
                      {(r.similarity * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <p className="text-xs text-gray-300 truncate">
                    {r.scene.location || "Unknown"} {chars ? `— ${chars}` : ""}
                  </p>
                </button>
              );
            })}
          </div>
        )}

        {open && results.length === 0 && !searching && (
          <p className="text-xs text-gray-600 mt-2 text-center">No scenes found</p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Bridge Mode Panel
// =============================================================================
function BridgePanel({ onCreated }: { onCreated: () => void }) {
  const [sceneA, setSceneA] = useState<Scene | null>(null);
  const [sceneB, setSceneB] = useState<Scene | null>(null);
  const [prompt, setPrompt] = useState("");
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function handleGenerate() {
    if (!sceneA || !sceneB || !prompt.trim()) return;
    setCreating(true);
    setResult(null);
    try {
      const tweak = await createBridgeTweak(sceneA.id, sceneB.id, prompt);
      setResult(`Bridge #${tweak.id} queued — generating transition...`);
      onCreated();
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : "Failed"}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ScenePicker
          label="Scene A (Start)"
          scene={sceneA}
          onSelect={setSceneA}
          onClear={() => setSceneA(null)}
        />
        <ScenePicker
          label="Scene B (End)"
          scene={sceneB}
          onSelect={setSceneB}
          onClear={() => setSceneB(null)}
        />
      </div>

      {sceneA && sceneB && (
        <div className="flex items-center gap-3 p-3 bg-gray-900/50 rounded-lg border border-gray-800">
          <span className="text-sm">🔗</span>
          <p className="text-xs text-gray-400">
            <strong className="text-gray-300">{sceneA.location || "Scene A"}</strong>
            {" → "}
            <strong className="text-gray-300">{sceneB.location || "Scene B"}</strong>
            {" "}
            (Veo will generate a 2-4s cinematic transition)
          </p>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Transition Direction
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Homer walks through a glowing donut portal from the nuclear plant to Moe's Tavern"
          className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm placeholder-gray-500 focus:outline-none focus:border-simpsons-yellow transition h-24 resize-none"
        />
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleGenerate}
          disabled={!sceneA || !sceneB || !prompt.trim() || creating}
          className="bg-simpsons-yellow text-black font-semibold px-6 py-3 rounded-lg hover:bg-yellow-400 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {creating ? "Generating..." : "Generate Bridge"}
        </button>
        {result && (
          <p className={`text-sm ${result.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
            {result}
          </p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Restyle Mode Panel
// =============================================================================
const STYLE_PRESETS = [
  { label: "Oil Painting", prompt: "classical oil painting with rich brushstrokes and warm tones" },
  { label: "Noir", prompt: "black and white film noir with dramatic shadows and high contrast" },
  { label: "Watercolor", prompt: "delicate watercolor painting with soft edges and translucent colors" },
  { label: "Pixel Art", prompt: "retro 16-bit pixel art with limited color palette" },
  { label: "Studio Ghibli", prompt: "Studio Ghibli animation style with lush backgrounds and soft lighting" },
  { label: "Cyberpunk", prompt: "cyberpunk neon aesthetic with rain-slicked streets and holographic signs" },
  { label: "Ukiyo-e", prompt: "traditional Japanese woodblock print style with flat colors and bold outlines" },
  { label: "Comic Book", prompt: "bold comic book illustration with halftone dots and thick outlines" },
];

function RestylePanel({ onCreated }: { onCreated: () => void }) {
  const [scene, setScene] = useState<Scene | null>(null);
  const [prompt, setPrompt] = useState("");
  const [strength, setStrength] = useState(0.7);
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function handleGenerate() {
    if (!scene || !prompt.trim()) return;
    setCreating(true);
    setResult(null);
    try {
      const tweak = await createRestyleTweak(scene.id, prompt, strength);
      setResult(`Restyle #${tweak.id} queued — generating image...`);
      onCreated();
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : "Failed"}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-5">
      <ScenePicker
        label="Source Scene"
        scene={scene}
        onSelect={setScene}
        onClear={() => setScene(null)}
      />

      {/* Style presets */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Style Presets
        </label>
        <div className="flex flex-wrap gap-2">
          {STYLE_PRESETS.map((s) => (
            <button
              key={s.label}
              onClick={() => setPrompt(s.prompt)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${
                prompt === s.prompt
                  ? "bg-simpsons-yellow text-black"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Style Prompt
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the visual style you want to apply..."
          className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm placeholder-gray-500 focus:outline-none focus:border-simpsons-yellow transition h-20 resize-none"
        />
      </div>

      {/* Strength slider */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-300">Style Strength</label>
          <span className="text-xs text-gray-500">{(strength * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={strength}
          onChange={(e) => setStrength(Number(e.target.value))}
          className="w-full accent-simpsons-yellow"
        />
        <div className="flex justify-between text-[10px] text-gray-600 mt-1">
          <span>Subtle</span>
          <span>Balanced</span>
          <span>Dramatic</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleGenerate}
          disabled={!scene || !prompt.trim() || creating}
          className="bg-simpsons-yellow text-black font-semibold px-6 py-3 rounded-lg hover:bg-yellow-400 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {creating ? "Generating..." : "Generate Restyle"}
        </button>
        {result && (
          <p className={`text-sm ${result.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
            {result}
          </p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Redub Mode Panel
// =============================================================================
interface RedubLine {
  character: string;
  text: string;
  voice_preset: string;
}

function RedubPanel({ onCreated }: { onCreated: () => void }) {
  const [scene, setScene] = useState<Scene | null>(null);
  const [lines, setLines] = useState<RedubLine[]>([]);
  const [voices, setVoices] = useState<VoicePreset[]>([]);
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    getVoicePresets()
      .then((d) => setVoices(d.voices))
      .catch(() => {});
  }, []);

  // Auto-populate lines from scene dialog when a scene is selected
  function handleSceneSelect(s: Scene) {
    setScene(s);
    const dialog = s.key_dialog || [];
    setLines(
      dialog.map((d) => ({
        character: d.speaker || "Unknown",
        text: d.exact_quote || "",
        voice_preset: "en-US-Studio-M",
      }))
    );
  }

  function updateLine(idx: number, patch: Partial<RedubLine>) {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  }

  function addLine() {
    setLines((prev) => [...prev, { character: "", text: "", voice_preset: "en-US-Studio-M" }]);
  }

  function removeLine(idx: number) {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleGenerate() {
    if (!scene || lines.length === 0) return;
    setCreating(true);
    setResult(null);
    try {
      const tweak = await createRedubTweak(scene.id, lines);
      setResult(`Redub #${tweak.id} queued — generating audio...`);
      onCreated();
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : "Failed"}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-5">
      <ScenePicker
        label="Source Scene"
        scene={scene}
        onSelect={handleSceneSelect}
        onClear={() => {
          setScene(null);
          setLines([]);
        }}
      />

      {scene && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-medium text-gray-300">
              Dialog Lines ({lines.length})
            </label>
            <button
              onClick={addLine}
              className="text-xs text-simpsons-yellow hover:underline"
            >
              + Add Line
            </button>
          </div>

          <div className="space-y-3">
            {lines.map((line, idx) => (
              <div
                key={idx}
                className="bg-gray-900 border border-gray-800 rounded-lg p-3 space-y-2"
              >
                <div className="flex items-center gap-3">
                  <input
                    value={line.character}
                    onChange={(e) => updateLine(idx, { character: e.target.value })}
                    placeholder="Character"
                    className="w-32 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs focus:border-simpsons-yellow focus:outline-none"
                  />
                  <select
                    value={line.voice_preset}
                    onChange={(e) => updateLine(idx, { voice_preset: e.target.value })}
                    className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs focus:border-simpsons-yellow focus:outline-none"
                  >
                    {voices.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.accent})
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => removeLine(idx)}
                    className="text-gray-500 hover:text-red-400 text-xs"
                  >
                    &#10005;
                  </button>
                </div>
                <textarea
                  value={line.text}
                  onChange={(e) => updateLine(idx, { text: e.target.value })}
                  placeholder="Dialog text..."
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:border-simpsons-yellow focus:outline-none h-16 resize-none"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-4">
        <button
          onClick={handleGenerate}
          disabled={!scene || lines.length === 0 || creating}
          className="bg-simpsons-yellow text-black font-semibold px-6 py-3 rounded-lg hover:bg-yellow-400 transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {creating ? "Generating..." : "Generate Redub"}
        </button>
        {result && (
          <p className={`text-sm ${result.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
            {result}
          </p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Gallery — Recent tweaks
// =============================================================================
function TweakGallery({ refreshKey }: { refreshKey: number }) {
  const [tweaks, setTweaks] = useState<TweakOut[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    getTweaks()
      .then(setTweaks)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh, refreshKey]);

  // Poll for active tweaks
  useEffect(() => {
    const hasActive = tweaks.some(
      (t) => t.status === "pending" || t.status === "generating"
    );
    if (!hasActive) return;

    const interval = setInterval(async () => {
      // Re-fetch individual active tweaks
      const updated = await Promise.all(
        tweaks.map(async (t) => {
          if (t.status === "pending" || t.status === "generating") {
            try {
              return await getTweak(t.id);
            } catch {
              return t;
            }
          }
          return t;
        })
      );
      setTweaks(updated);
    }, 3000);

    return () => clearInterval(interval);
  }, [tweaks]);

  async function handleDelete(id: number) {
    try {
      await deleteTweak(id);
      setTweaks((prev) => prev.filter((t) => t.id !== id));
    } catch {}
  }

  const statusColors: Record<string, string> = {
    pending: "bg-gray-600",
    generating: "bg-blue-600 animate-pulse",
    completed: "bg-green-600",
    failed: "bg-red-600",
  };

  const modeIcons: Record<string, string> = {
    bridge: "🎬",
    restyle: "🎨",
    redub: "🎙️",
  };

  if (loading) return <p className="text-gray-500 text-sm">Loading gallery...</p>;
  if (tweaks.length === 0)
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-3xl mb-2">🎭</p>
        <p>No tweaks yet. Create your first one above!</p>
      </div>
    );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {tweaks.map((t) => (
        <div
          key={t.id}
          className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span>{modeIcons[t.mode] || "?"}</span>
              <span className="text-sm font-medium capitalize">{t.mode}</span>
              <span className="text-xs text-gray-500">#{t.id}</span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${statusColors[t.status] || "bg-gray-600"}`}
              >
                {t.status}
              </span>
              <button
                onClick={() => handleDelete(t.id)}
                className="text-gray-600 hover:text-red-400 text-xs"
              >
                &#10005;
              </button>
            </div>
          </div>

          {/* Prompt preview */}
          <p className="text-xs text-gray-400 line-clamp-2 flex-1">
            {t.transition_prompt || t.restyle_prompt || `${(t.redub_config || []).length} dialog lines`}
          </p>

          {/* Details */}
          <div className="mt-3 pt-2 border-t border-gray-800 flex items-center justify-between text-[10px] text-gray-600">
            <span>Scene #{t.scene_a_id}{t.scene_b_id ? ` → #${t.scene_b_id}` : ""}</span>
            {t.generation_seconds && <span>{t.generation_seconds}s</span>}
            {t.cost_usd > 0 && <span>${t.cost_usd.toFixed(3)}</span>}
          </div>

          {t.status === "failed" && t.error && (
            <p className="text-[10px] text-red-400 mt-1 truncate" title={t.error}>
              {t.error}
            </p>
          )}

          {t.status === "completed" && t.output_url && (
            <a
              href={t.output_url}
              target="_blank"
              rel="noopener"
              className="mt-2 text-xs text-simpsons-yellow hover:underline text-center"
            >
              View Output &rarr;
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Main Tweak Studio Page
// =============================================================================
export default function TweakStudio() {
  const [mode, setMode] = useState<Mode>("bridge");
  const [galleryKey, setGalleryKey] = useState(0);

  const refreshGallery = () => setGalleryKey((k) => k + 1);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-simpsons-yellow">Tweak Studio</h1>
        <p className="text-gray-400 text-sm mt-1">
          AI-powered scene manipulation — bridge transitions, restyle visuals, redub dialog
        </p>
      </div>

      {/* Mode selector */}
      <ModeTabs active={mode} onChange={setMode} />

      {/* Mode description */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 flex items-start gap-3">
        <span className="text-2xl">{MODE_INFO[mode].icon}</span>
        <div>
          <p className="text-sm font-medium text-gray-200">
            {MODE_INFO[mode].label} Mode
            <span className="ml-2 text-xs text-gray-500">powered by {MODE_INFO[mode].engine}</span>
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{MODE_INFO[mode].desc}</p>
        </div>
      </div>

      {/* Mode-specific panel */}
      {mode === "bridge" && <BridgePanel onCreated={refreshGallery} />}
      {mode === "restyle" && <RestylePanel onCreated={refreshGallery} />}
      {mode === "redub" && <RedubPanel onCreated={refreshGallery} />}

      {/* Gallery */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Recent Tweaks</h2>
        <TweakGallery refreshKey={galleryKey} />
      </div>
    </div>
  );
}
