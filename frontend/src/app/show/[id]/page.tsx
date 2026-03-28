"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getShowDetail, startProcessing, type ShowDetail, type ShowEpisode } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

// --- Episode Row ---
function EpisodeRow({
  episode,
  seasonNum,
  onProcess,
}: {
  episode: ShowEpisode;
  seasonNum: number;
  onProcess: (id: number) => void;
}) {
  const statusColors: Record<string, string> = {
    pending: "bg-gray-700 text-gray-400",
    processing: "bg-blue-900 text-blue-300",
    ready: "bg-green-900 text-green-300",
    error: "bg-red-900 text-red-300",
  };

  return (
    <div className="flex items-center gap-4 py-3 px-4 hover:bg-white/5 rounded-lg transition group">
      {/* Episode number */}
      <span className="text-2xl font-bold text-gray-700 w-10 text-right flex-shrink-0">
        {episode.episode_number}
      </span>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-medium truncate">{episode.title}</h4>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[episode.status] || "bg-gray-700"}`}>
            {episode.status}
          </span>
        </div>
        {episode.overview && (
          <p className="text-sm text-gray-500 truncate mt-0.5">{episode.overview}</p>
        )}
        <div className="flex gap-3 text-xs text-gray-600 mt-1">
          {episode.air_date && <span>{episode.air_date}</span>}
          {episode.duration_seconds && (
            <span>{Math.round(episode.duration_seconds / 60)} min</span>
          )}
          {!episode.has_file && <span className="text-red-500">No file</span>}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition">
        {episode.status === "ready" ? (
          <a
            href={`/search?episode=${episode.id}`}
            className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded transition"
          >
            Browse Scenes
          </a>
        ) : episode.status === "pending" && episode.has_file ? (
          <button
            onClick={() => onProcess(episode.id)}
            className="text-xs bg-[var(--show-primary,#FFD521)] text-black px-3 py-1.5 rounded hover:opacity-80 transition font-medium"
          >
            Process
          </button>
        ) : null}
      </div>
    </div>
  );
}

// --- Main Show Detail Page ---
export default function ShowDetailPage() {
  const params = useParams();
  const showId = Number(params.id);
  const [show, setShow] = useState<ShowDetail | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<string>("1");
  const [processing, setProcessing] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!showId) return;
    getShowDetail(showId).then((data) => {
      setShow(data);
      // Default to first available season
      const seasons = Object.keys(data.seasons).sort((a, b) => Number(a) - Number(b));
      if (seasons.length > 0) setSelectedSeason(seasons[0]);
    });
  }, [showId]);

  async function handleProcess(episodeId: number) {
    setProcessing((prev) => new Set(prev).add(episodeId));
    try {
      await startProcessing(episodeId);
    } catch {
      // Error handling
    }
  }

  if (!show) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  const seasons = Object.keys(show.seasons).sort((a, b) => Number(a) - Number(b));
  const currentEpisodes = show.seasons[selectedSeason] || [];
  const primary = show.theme_config?.primary_color || "#FFD521";
  const secondary = show.theme_config?.secondary_color || "#000000";

  return (
    <div
      className="-mt-8 -mx-4"
      style={{
        "--show-primary": primary,
        "--show-secondary": secondary,
      } as React.CSSProperties}
    >
      {/* Hero backdrop */}
      <div className="relative w-full h-[450px] overflow-hidden">
        {show.fanart_url ? (
          <img
            src={show.fanart_url}
            alt={show.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-r from-gray-900 to-gray-800" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/50 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-gray-950/90 via-gray-950/40 to-transparent" />

        <div className="absolute bottom-8 left-8 right-8 flex gap-8 items-end">
          {/* Poster */}
          {show.poster_url && (
            <img
              src={show.poster_url}
              alt={show.name}
              className="w-36 h-52 object-cover rounded-lg shadow-2xl flex-shrink-0 hidden sm:block"
            />
          )}

          {/* Info */}
          <div className="flex-1">
            {show.clearlogo_url ? (
              <img
                src={show.clearlogo_url}
                alt={show.name}
                className="h-16 mb-2 object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            ) : (
              <h1 className="text-4xl font-bold mb-2" style={{ color: primary }}>
                {show.name}
              </h1>
            )}

            <div className="flex items-center gap-3 text-sm text-gray-300 mb-2">
              {show.year && <span>{show.year}</span>}
              {show.network && (
                <span className="bg-gray-800/80 px-2 py-0.5 rounded">{show.network}</span>
              )}
              {show.rating_value && (
                <span className="text-yellow-400">
                  &#9733; {show.rating_value.toFixed(1)}
                </span>
              )}
              <span>{show.total_episodes} episodes</span>
              {show.cutprint && (
                <span className="bg-purple-900/60 text-purple-300 px-2 py-0.5 rounded text-xs">
                  CutPrint: {show.cutprint.genre}
                </span>
              )}
            </div>

            <div className="flex gap-1.5 mb-3">
              {show.genres.map((g) => (
                <span key={g} className="bg-gray-800/80 px-2 py-0.5 rounded text-xs text-gray-300">
                  {g}
                </span>
              ))}
            </div>

            {show.overview && (
              <p className="text-sm text-gray-400 max-w-2xl line-clamp-3">
                {show.overview}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Season selector + Episodes */}
      <div className="px-8 py-6 space-y-4">
        {/* Season tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {seasons.map((s) => (
            <button
              key={s}
              onClick={() => setSelectedSeason(s)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition whitespace-nowrap ${
                s === selectedSeason
                  ? "text-black"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200"
              }`}
              style={
                s === selectedSeason ? { backgroundColor: primary, color: secondary } : {}
              }
            >
              Season {s}
            </button>
          ))}
        </div>

        {/* Episode list */}
        <div className="space-y-1">
          {currentEpisodes.map((ep) => (
            <EpisodeRow
              key={ep.id}
              episode={ep}
              seasonNum={Number(selectedSeason)}
              onProcess={handleProcess}
            />
          ))}
          {currentEpisodes.length === 0 && (
            <p className="text-gray-500 text-center py-8">
              No episodes in Season {selectedSeason}
            </p>
          )}
        </div>

        {/* Batch process button */}
        {currentEpisodes.some((ep) => ep.status === "pending" && ep.has_file) && (
          <div className="pt-4 border-t border-gray-800">
            <button
              onClick={async () => {
                const res = await fetch(
                  `${API_URL}/api/process/season/${show.id}/${selectedSeason}`,
                  {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ skip_indexed: true }),
                  }
                );
                const data = await res.json();
                if (res.ok) {
                  alert(`Queued ${data.queued} episodes for processing`);
                  getShowDetail(showId).then(setShow);
                }
              }}
              className="px-6 py-2.5 rounded-lg font-semibold text-sm transition hover:opacity-80"
              style={{ backgroundColor: primary, color: secondary }}
            >
              Process All Pending in Season {selectedSeason}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
