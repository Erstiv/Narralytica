"use client";

import { useEffect, useState } from "react";
import {
  getShows,
  getShowDetail,
  generateReportPreview,
  downloadReport,
  type ShowSummary,
  type ShowEpisode,
  type ReportRequest,
  type ReportPreview,
  type ReportSection,
} from "@/lib/api";

// ─── Report Type Definitions ───────────────────────────────

const REPORT_TYPES = [
  { id: "plot_summary", label: "Plot Summary", desc: "Narrative summary of events from scene descriptions" },
  { id: "character_summaries", label: "Character Summaries", desc: "Profiles with scene count, duration, motivations, speaking lines" },
  { id: "character_motivations", label: "Character Motivations", desc: "What drives each character, scene by scene" },
  { id: "two_column_script", label: "Two-Column Script", desc: "Dialog/audio LEFT, visuals/action RIGHT" },
  { id: "scene_breakdown", label: "Scene Breakdown", desc: "Full metadata per scene: tone, mood, camera, music, explicitness" },
  { id: "dialog_only", label: "Dialog Only", desc: "Clean transcript with speaker names and timestamps" },
  { id: "visual_descriptions", label: "Visual Descriptions", desc: "What's on screen: actions, camera, lighting, color palette" },
  { id: "content_critic", label: "Content Critic", desc: "Fair but harsh data-driven critique: pacing, tone, character balance, dialog density" },
  { id: "marketing_editor", label: "Marketing Editor", desc: "AI-powered marketing analysis with neuroscience citations, audience targeting, clip recommendations" },
];

// ─── Scope Picker ──────────────────────────────────────────

function ScopePicker({ onSelect }: {
  onSelect: (scope: "episode" | "season", showId: number, seasonNum: number, episodeId: number | null, label: string) => void;
}) {
  const [shows, setShows] = useState<ShowSummary[]>([]);
  const [selectedShow, setSelectedShow] = useState<number | null>(null);
  const [seasons, setSeasons] = useState<Record<string, ShowEpisode[]>>({});
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const [scopeMode, setScopeMode] = useState<"episode" | "season">("episode");

  useEffect(() => {
    getShows().then(s => setShows(s.filter(x => (x.episode_count ?? 0) > 0))).catch(() => {});
  }, []);

  function handleShowSelect(showId: number) {
    setSelectedShow(showId);
    setSelectedSeason(null);
    getShowDetail(showId).then(d => setSeasons(d.seasons || {})).catch(() => {});
  }

  const showName = shows.find(s => s.id === selectedShow)?.name || "";

  return (
    <div className="space-y-3">
      {/* Scope toggle */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-400">Scope:</span>
        <div className="flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          {(["episode", "season"] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setScopeMode(mode)}
              className={`px-4 py-1.5 text-xs font-medium transition capitalize ${
                scopeMode === mode ? "bg-simpsons-yellow text-black" : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Show selector */}
      <div className="flex flex-wrap gap-2">
        {shows.map(s => (
          <button
            key={s.id}
            onClick={() => handleShowSelect(s.id)}
            className={`px-3 py-1.5 text-xs rounded-lg transition border ${
              selectedShow === s.id
                ? "bg-simpsons-yellow text-black border-simpsons-yellow"
                : "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* Season selector */}
      {selectedShow && Object.keys(seasons).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.keys(seasons).sort().map(s => (
            <button
              key={s}
              onClick={() => {
                setSelectedSeason(s);
                if (scopeMode === "season") {
                  onSelect("season", selectedShow, Number(s), null, `${showName} Season ${s}`);
                }
              }}
              className={`px-3 py-1.5 text-xs rounded transition ${
                selectedSeason === s ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              Season {s}
            </button>
          ))}
        </div>
      )}

      {/* Episode selector (only in episode mode) */}
      {scopeMode === "episode" && selectedSeason && seasons[selectedSeason] && (
        <div className="flex flex-wrap gap-2">
          {seasons[selectedSeason]
            .filter(ep => ep.status === "ready")
            .map(ep => (
              <button
                key={ep.id}
                onClick={() => onSelect("episode", selectedShow!, Number(selectedSeason), ep.id, `${showName} S${selectedSeason.padStart(2,"0")}E${String(ep.episode_number).padStart(2,"0")} ${ep.title}`)}
                className="px-3 py-1.5 text-xs bg-gray-800 text-gray-300 hover:bg-gray-700 rounded transition"
              >
                E{String(ep.episode_number).padStart(2, "0")} {ep.title}
              </button>
            ))}
        </div>
      )}
    </div>
  );
}

// ─── Preview Renderers ─────────────────────────────────────

function PlotSummaryPreview({ section }: { section: ReportSection }) {
  const episodes = (section as any).episodes || [];
  return (
    <div className="space-y-6">
      {episodes.map((ep: any) => (
        <div key={ep.episode_label}>
          <h4 className="font-semibold text-blue-400 mb-3">{ep.episode_label} — {ep.episode_title}</h4>

          {/* Narrative summary */}
          {ep.narrative && (
            <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-line mb-4">
              {ep.narrative}
            </div>
          )}

          {/* Scene-by-scene summaries */}
          {ep.scene_summaries?.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
                Scene-by-scene ({ep.scene_summaries.length} scenes)
              </summary>
              <div className="mt-2 space-y-1 pl-3 border-l border-gray-800">
                {ep.scene_summaries.map((s: string, i: number) => (
                  <p key={i} className="text-xs text-gray-400">
                    <span className="text-gray-600 mr-1">Scene {i + 1}:</span> {s}
                  </p>
                ))}
              </div>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}

function CharacterSummariesPreview({ section }: { section: ReportSection }) {
  const characters = (section as any).characters || [];
  return (
    <div className="space-y-4">
      {characters.map((c: any) => (
        <div key={c.name} className="bg-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-simpsons-yellow text-lg">{c.name}</h4>
            <span className="text-xs text-gray-500">
              {c.scene_count} scenes | {c.duration_formatted} | {c.speaking_lines} lines
            </span>
          </div>
          {c.description && (
            <p className="text-sm text-gray-300 mb-2 leading-relaxed">{c.description}</p>
          )}
          <div className="flex flex-wrap gap-2 text-xs">
            {c.dominant_tone && <span className="bg-purple-900/40 text-purple-300 px-2 py-0.5 rounded">{c.dominant_tone}</span>}
            {c.episodes?.map((ep: string) => (
              <span key={ep} className="bg-gray-700 text-gray-400 px-2 py-0.5 rounded">{ep}</span>
            ))}
          </div>
          {c.key_quotes?.length > 0 && (
            <div className="mt-2 pl-3 border-l border-gray-700">
              {c.key_quotes.map((q: string, i: number) => (
                <p key={i} className="text-xs text-gray-400 italic">&ldquo;{q}&rdquo;</p>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function TwoColumnScriptPreview({ section }: { section: ReportSection }) {
  const episodes = (section as any).episodes || [];
  return (
    <div className="space-y-6">
      {episodes.map((ep: any) => (
        <div key={ep.episode_label}>
          <h4 className="font-semibold text-blue-400 mb-3">{ep.episode_label} — {ep.episode_title}</h4>
          {ep.rows?.map((row: any) => (
            <div key={row.scene_number} className="mb-4">
              <div className="text-xs text-gray-500 mb-1 font-medium">
                Scene {row.scene_number} — {row.time} | {row.location} | {row.tone}
              </div>
              <div className="grid grid-cols-2 gap-0 border border-gray-700 rounded overflow-hidden text-xs">
                <div className="bg-gray-900 p-3 border-r border-gray-700">
                  <div className="text-gray-500 font-bold mb-2 text-[10px] uppercase">Dialog / Audio</div>
                  {row.left.dialog.map((d: any, i: number) => (
                    <p key={i} className="text-gray-300 mb-1">
                      <span className="text-simpsons-yellow font-semibold">{d.speaker}:</span> {d.text}
                    </p>
                  ))}
                  {row.left.audio.map((a: string, i: number) => (
                    <p key={i} className="text-gray-500 italic mt-1">{a}</p>
                  ))}
                  {row.left.dialog.length === 0 && row.left.audio.length === 0 && (
                    <p className="text-gray-600 italic">No dialog</p>
                  )}
                </div>
                <div className="bg-gray-950 p-3">
                  <div className="text-gray-500 font-bold mb-2 text-[10px] uppercase">Visuals / Action</div>
                  {row.right.description && <p className="text-gray-300 mb-1">{row.right.description}</p>}
                  {row.right.actions && <p className="text-gray-400 italic mb-1">{row.right.actions}</p>}
                  <p className="text-gray-600 text-[10px] mt-1">
                    {[row.right.camera, row.right.lighting, row.right.composition].filter(Boolean).join(" | ")}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function DialogOnlyPreview({ section }: { section: ReportSection }) {
  const episodes = (section as any).episodes || [];
  return (
    <div className="space-y-4">
      {episodes.map((ep: any) => (
        <div key={ep.episode_label}>
          <h4 className="font-semibold text-blue-400 mb-2">{ep.episode_label} — {ep.episode_title}</h4>
          {ep.scenes?.map((scene: any, i: number) => (
            <div key={i} className="mb-3">
              <div className="text-xs text-blue-400 font-medium mb-1">[{scene.scene_time}] {scene.location}</div>
              {scene.dialog.map((d: any, j: number) => (
                <p key={j} className="text-sm text-gray-300 ml-2">
                  <span className="font-semibold">{d.speaker}:</span> {d.text}
                </p>
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function CharacterMotivationsPreview({ section }: { section: ReportSection }) {
  const characters = (section as any).characters || {};
  return (
    <div className="space-y-4">
      {Object.entries(characters).map(([name, entries]: [string, any]) => (
        <div key={name} className="bg-gray-800 rounded-lg p-4">
          <h4 className="font-semibold text-simpsons-yellow mb-3">{name} <span className="text-xs text-gray-500 font-normal">({entries.length} scenes)</span></h4>
          {entries.map((e: any, i: number) => (
            <div key={i} className="mb-2 pl-3 border-l-2 border-gray-700">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-0.5">
                <span className="text-blue-400">{e.episode} Scene {e.scene}</span>
                <span>{e.time}</span>
                <span className="bg-gray-700 px-1.5 py-0.5 rounded">{e.tone}</span>
                <span className="text-gray-600">{e.location}</span>
              </div>
              <p className="text-sm text-gray-300">{e.motivation}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function SceneBreakdownPreview({ section }: { section: ReportSection }) {
  const episodes = (section as any).episodes || [];
  return (
    <div className="space-y-4">
      {episodes.map((ep: any) => (
        <div key={ep.episode_label}>
          <h4 className="font-semibold text-blue-400 mb-3">{ep.episode_label} — {ep.episode_title}</h4>
          {ep.scenes?.map((s: any) => (
            <div key={s.scene_number} className="mb-4 bg-gray-900 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className="text-sm font-semibold text-gray-200">Scene {s.scene_number}</span>
                <span className="text-xs text-gray-500">{s.time} ({s.duration})</span>
                {s.tone && <span className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded">{s.tone}</span>}
                {s.pacing && <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{s.pacing}</span>}
                {s.plot_significance && <span className="text-xs bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded">{s.plot_significance}</span>}
              </div>
              {s.characters?.length > 0 && (
                <p className="text-xs text-gray-500 mb-1">Characters: {s.characters.join(", ")}</p>
              )}
              {s.location && <p className="text-xs text-gray-500 mb-1">Location: {s.location}</p>}
              {s.description && <p className="text-sm text-gray-300 mb-1">{s.description}</p>}
              {s.actions && <p className="text-sm text-gray-400 italic mb-1">{s.actions}</p>}
              {s.mood && <p className="text-xs text-gray-500">Mood: {s.mood}</p>}
              {s.music && <p className="text-xs text-gray-500">Music: {s.music}</p>}
              {s.motivations && <p className="text-xs text-gray-500">Motivations: {s.motivations}</p>}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function VisualDescriptionsPreview({ section }: { section: ReportSection }) {
  const episodes = (section as any).episodes || [];
  return (
    <div className="space-y-4">
      {episodes.map((ep: any) => (
        <div key={ep.episode_label}>
          <h4 className="font-semibold text-blue-400 mb-3">{ep.episode_label} — {ep.episode_title}</h4>
          {ep.scenes?.map((s: any) => (
            <div key={s.scene_number} className="mb-3 pl-3 border-l-2 border-gray-700">
              <div className="text-xs text-gray-500 mb-1">
                Scene {s.scene_number} — {s.time} | {s.location || "Unknown location"}
              </div>
              {s.description && <p className="text-sm text-gray-300 mb-1">{s.description}</p>}
              {s.actions && <p className="text-sm text-gray-400 italic mb-1">{s.actions}</p>}
              <p className="text-xs text-gray-600">
                {[s.camera, s.lighting, s.composition, s.visual_style].filter(Boolean).join(" | ")}
              </p>
              {s.color_palette?.length > 0 && (
                <div className="flex gap-1 mt-1">
                  {s.color_palette.map((c: string, i: number) => (
                    <div key={i} className="w-4 h-4 rounded" style={{ backgroundColor: c }} title={c} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function ContentCriticPreview({ section }: { section: ReportSection }) {
  const s = section as any;
  const gradeColor = s.overall_grade?.startsWith("A") ? "text-green-400" : s.overall_grade?.startsWith("C") ? "text-red-400" : "text-blue-400";
  const severityStyles: Record<string, string> = {
    strength: "border-green-600 bg-green-900/20",
    warning: "border-red-600 bg-red-900/20",
    note: "border-yellow-600 bg-yellow-900/20",
  };
  const severityLabels: Record<string, string> = {
    strength: "STRENGTH",
    warning: "CONCERN",
    note: "NOTE",
  };
  const severityColors: Record<string, string> = {
    strength: "text-green-400",
    warning: "text-red-400",
    note: "text-yellow-400",
  };

  return (
    <div className="space-y-6">
      {/* Grade */}
      <div className="text-center">
        <div className={`text-6xl font-bold ${gradeColor}`}>{s.overall_grade}</div>
        <p className="text-sm text-gray-500 mt-2">
          {s.summary?.total_episodes} episodes | {s.summary?.total_scenes} scenes | {s.summary?.total_duration_formatted} |
          {s.summary?.unique_characters} characters
        </p>
        <p className="text-xs text-gray-600 mt-1">
          {s.summary?.strengths} strengths, {s.summary?.warnings} concerns, {s.summary?.notes} notes
        </p>
      </div>

      {/* Critiques */}
      {s.critiques?.map((c: any, i: number) => (
        <div key={i} className={`border-l-4 rounded-lg p-4 ${severityStyles[c.severity] || "border-gray-600"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-bold uppercase ${severityColors[c.severity] || "text-gray-400"}`}>
              {severityLabels[c.severity] || c.severity}
            </span>
            <span className="text-sm font-semibold text-gray-200">{c.category}</span>
          </div>
          <p className="text-sm text-gray-300">{c.finding}</p>
          {c.data && (
            <details className="mt-2">
              <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-400">Show data</summary>
              <pre className="text-xs text-gray-500 mt-1 bg-gray-900 p-2 rounded overflow-x-auto">
                {JSON.stringify(c.data, null, 2)}
              </pre>
            </details>
          )}
        </div>
      ))}

      {/* Per-episode table */}
      {s.episode_breakdown?.length > 1 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-300 mb-2">Per-Episode Breakdown</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-gray-400">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-1 px-2">Episode</th>
                  <th className="text-right py-1 px-2">Scenes</th>
                  <th className="text-right py-1 px-2">Chars</th>
                  <th className="text-right py-1 px-2">Dialog</th>
                  <th className="text-left py-1 px-2">Tone</th>
                  <th className="text-right py-1 px-2">Shifts</th>
                </tr>
              </thead>
              <tbody>
                {s.episode_breakdown.map((ep: any) => (
                  <tr key={ep.label} className="border-b border-gray-800">
                    <td className="py-1 px-2 text-gray-300">{ep.label} {ep.title}</td>
                    <td className="py-1 px-2 text-right">{ep.scene_count}</td>
                    <td className="py-1 px-2 text-right">{ep.unique_chars}</td>
                    <td className="py-1 px-2 text-right">{ep.dialog_lines}</td>
                    <td className="py-1 px-2">{ep.dominant_tone}</td>
                    <td className="py-1 px-2 text-right">{ep.pacing_shifts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function MarketingEditorPreview({ section }: { section: ReportSection }) {
  const s = section as any;
  if (s.error) return <p className="text-red-400">{s.error}</p>;
  const a = s.analysis || {};

  const typeStyles: Record<string, string> = {
    strength: "border-green-600 bg-green-900/20",
    opportunity: "border-blue-600 bg-blue-900/20",
    concern: "border-red-600 bg-red-900/20",
  };
  const typeColors: Record<string, string> = {
    strength: "text-green-400",
    opportunity: "text-blue-400",
    concern: "text-red-400",
  };

  return (
    <div className="space-y-8">
      {/* Overall assessment */}
      {a.overall_assessment && (
        <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 border border-blue-800/50 rounded-xl p-6">
          <p className="text-lg text-gray-200 italic leading-relaxed">{a.overall_assessment}</p>
        </div>
      )}

      {/* Target audiences */}
      {a.target_audiences?.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Target Audiences</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {a.target_audiences.map((aud: any, i: number) => (
              <div key={i} className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-gray-200">{aud.segment}</span>
                  <span className={`text-sm font-bold ${aud.appeal_score >= 0.7 ? "text-green-400" : "text-yellow-400"}`}>
                    {Math.round(aud.appeal_score * 100)}%
                  </span>
                </div>
                <p className="text-sm text-gray-400">{aud.reasoning}</p>
                {aud.hook && <p className="text-sm text-blue-400 mt-2 font-medium">Hook: {aud.hook}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Observations */}
      {a.observations?.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Observations & Recommendations</h4>
          <div className="space-y-4">
            {a.observations.map((obs: any, i: number) => (
              <div key={i} className={`border-l-4 rounded-lg p-4 ${typeStyles[obs.type] || "border-gray-600 bg-gray-900"}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs font-bold uppercase ${typeColors[obs.type] || "text-gray-400"}`}>
                    {obs.type}
                  </span>
                  <span className="text-sm font-semibold text-gray-200">{obs.category}</span>
                </div>
                <p className="text-sm text-gray-300 mb-2">{obs.observation}</p>
                {obs.marketing_implication && (
                  <p className="text-sm text-gray-400 mb-2">
                    <span className="font-semibold text-gray-300">Marketing: </span>{obs.marketing_implication}
                  </p>
                )}
                {obs.evidence && (
                  <p className="text-xs text-purple-400 italic mb-2">
                    Evidence: {obs.evidence}
                  </p>
                )}
                {obs.recommendation && (
                  <p className="text-sm text-blue-400">
                    Recommendation: {obs.recommendation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clip recommendations */}
      {a.clip_recommendations?.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Social Media Clip Recommendations</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {a.clip_recommendations.map((clip: any, i: number) => (
              <div key={i} className="bg-gray-900 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-simpsons-yellow">{clip.purpose}</span>
                  <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{clip.platform}</span>
                </div>
                <p className="text-sm text-gray-300 mb-1">{clip.description}</p>
                {clip.timestamp_hint && <p className="text-xs text-gray-500">Timestamp: {clip.timestamp_hint}</p>}
                {clip.psychological_hook && (
                  <p className="text-xs text-purple-400 italic mt-1">Why: {clip.psychological_hook}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Binge analysis */}
      {a.binge_analysis && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Binge-Watching Analysis</h4>
          <div className="text-center mb-4">
            <span className="text-4xl font-bold text-simpsons-yellow">
              {Math.round((a.binge_analysis.binge_score || 0) * 100)}%
            </span>
            <span className="text-sm text-gray-500 ml-2">Binge Score</span>
          </div>
          {a.binge_analysis.cliffhanger_effectiveness && (
            <p className="text-sm text-gray-300 mb-2"><span className="font-semibold">Cliffhangers:</span> {a.binge_analysis.cliffhanger_effectiveness}</p>
          )}
          {a.binge_analysis.pacing_for_retention && (
            <p className="text-sm text-gray-300 mb-2"><span className="font-semibold">Retention:</span> {a.binge_analysis.pacing_for_retention}</p>
          )}
          {a.binge_analysis.drop_off_risks?.length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-red-400 font-semibold">Drop-off risks:</span>
              {a.binge_analysis.drop_off_risks.map((r: string, i: number) => (
                <p key={i} className="text-xs text-gray-400 ml-3 mt-1">- {r}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Competitive positioning */}
      {a.competitive_positioning && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-2">Competitive Positioning</h4>
          <p className="text-sm text-gray-300">{a.competitive_positioning}</p>
        </div>
      )}
    </div>
  );
}

function SectionRenderer({ section }: { section: ReportSection }) {
  const renderers: Record<string, React.FC<{ section: ReportSection }>> = {
    plot_summary: PlotSummaryPreview,
    character_summaries: CharacterSummariesPreview,
    character_motivations: CharacterMotivationsPreview,
    two_column_script: TwoColumnScriptPreview,
    scene_breakdown: SceneBreakdownPreview,
    dialog_only: DialogOnlyPreview,
    visual_descriptions: VisualDescriptionsPreview,
    content_critic: ContentCriticPreview,
    marketing_editor: MarketingEditorPreview,
  };
  const Comp = renderers[section.type];
  if (!Comp) return null;
  return <Comp section={section} />;
}

// ─── Main Page ─────────────────────────────────────────────

export default function ReportsPage() {
  const [scope, setScope] = useState<"episode" | "season" | null>(null);
  const [showId, setShowId] = useState<number | null>(null);
  const [seasonNum, setSeasonNum] = useState<number | null>(null);
  const [episodeId, setEpisodeId] = useState<number | null>(null);
  const [scopeLabel, setScopeLabel] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [nlQuery, setNlQuery] = useState("");
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleScopeSelect(s: "episode" | "season", sid: number, season: number, eid: number | null, label: string) {
    setScope(s);
    setShowId(sid);
    setSeasonNum(season);
    setEpisodeId(eid);
    setScopeLabel(label);
    setPreview(null);
    setError(null);
  }

  function toggleType(id: string) {
    setSelectedTypes(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setPreview(null);  // Clear preview when selections change
  }

  function buildRequest(format: "preview" | "docx"): ReportRequest {
    const req: ReportRequest = {
      scope: scope!,
      report_types: Array.from(selectedTypes),
      format,
    };
    if (scope === "episode") {
      req.episode_id = episodeId!;
    } else {
      req.show_id = showId!;
      req.season = seasonNum!;
    }
    if (nlQuery.trim()) req.nl_query = nlQuery.trim();
    return req;
  }

  async function handleGenerate() {
    if (!scope || selectedTypes.size === 0) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const data = await generateReportPreview(buildRequest("preview"));
      setPreview(data);
    } catch (e: any) {
      setError(e.message || "Failed to generate report");
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload() {
    if (!scope || selectedTypes.size === 0) return;
    setDownloading(true);
    try {
      await downloadReport(buildRequest("docx"));
    } catch (e: any) {
      setError(e.message || "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-simpsons-yellow">Reports</h1>
        <p className="text-gray-400 text-sm mt-1">
          Generate custom documents from indexed scene data — summaries, scripts, breakdowns
        </p>
      </div>

      {/* Scope Picker */}
      <section className="bg-gray-950 border border-gray-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">1. Select Scope</h3>
        <ScopePicker onSelect={handleScopeSelect} />
        {scopeLabel && (
          <div className="mt-3 text-sm text-simpsons-yellow font-medium">
            Selected: {scopeLabel}
          </div>
        )}
      </section>

      {/* Report Types */}
      {scope && (
        <section className="bg-gray-950 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">2. Choose Report Sections</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {REPORT_TYPES.map(rt => (
              <button
                key={rt.id}
                onClick={() => toggleType(rt.id)}
                className={`text-left p-3 rounded-lg border transition ${
                  selectedTypes.has(rt.id)
                    ? "border-simpsons-yellow bg-simpsons-yellow/10"
                    : "border-gray-700 hover:border-gray-500"
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                    selectedTypes.has(rt.id) ? "border-simpsons-yellow bg-simpsons-yellow" : "border-gray-600"
                  }`}>
                    {selectedTypes.has(rt.id) && <span className="text-black text-xs font-bold">&#10003;</span>}
                  </div>
                  <span className="text-sm font-medium text-gray-200">{rt.label}</span>
                </div>
                <p className="text-xs text-gray-500 mt-1 ml-6">{rt.desc}</p>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Natural Language Input */}
      {scope && selectedTypes.size > 0 && (
        <section className="bg-gray-950 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
            3. Refine (Optional)
          </h3>
          <textarea
            value={nlQuery}
            onChange={e => setNlQuery(e.target.value)}
            placeholder='Describe what you want to focus on... e.g. "Only scenes where Jenna argues with Jeff" or "Focus on action sequences with gunfire"'
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-200 placeholder-gray-500 focus:border-simpsons-yellow focus:outline-none resize-none h-20"
          />
        </section>
      )}

      {/* Actions */}
      {scope && selectedTypes.size > 0 && (
        <div className="flex gap-3">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="bg-simpsons-yellow text-black font-semibold px-6 py-3 rounded-lg hover:bg-yellow-400 transition disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate Preview"}
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="bg-blue-600 text-white font-semibold px-6 py-3 rounded-lg hover:bg-blue-500 transition disabled:opacity-50"
          >
            {downloading ? "Preparing DOCX..." : "Download DOCX"}
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">{error}</div>
      )}

      {/* Preview */}
      {preview && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-gray-200">{preview.title}</h2>
          {preview.sections.map((section, i) => (
            <section key={i} className="bg-gray-950 border border-gray-800 rounded-xl p-5">
              <h3 className="text-lg font-semibold text-simpsons-yellow mb-4">{section.title}</h3>
              <SectionRenderer section={section} />
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
