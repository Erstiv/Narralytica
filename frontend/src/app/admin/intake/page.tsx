"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  browseSonarrShows,
  browseSonarrEpisodes,
  importShowFromSonarr,
  startSeasonProcessing,
  uploadVideo,
  type SonarrShow,
  type SonarrEpisode,
} from "@/lib/api";

// =============================================================================
// Tab selector
// =============================================================================
type Tab = "library" | "upload";

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "library", label: "Plex Library", icon: "📺" },
    { id: "upload", label: "Upload Files", icon: "📤" },
  ];
  return (
    <div className="flex gap-1 bg-gray-900 rounded-lg p-1 mb-6">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition ${
            active === t.id
              ? "bg-simpsons-yellow text-black"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
          }`}
        >
          <span>{t.icon}</span> {t.label}
        </button>
      ))}
    </div>
  );
}

// =============================================================================
// Library Browser — Browse Sonarr, import into Narralytica, batch process
// =============================================================================
function LibraryBrowser() {
  const [shows, setShows] = useState<SonarrShow[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected show drill-down
  const [selected, setSelected] = useState<SonarrShow | null>(null);
  const [episodes, setEpisodes] = useState<SonarrEpisode[]>([]);
  const [epLoading, setEpLoading] = useState(false);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);

  // Import / process state
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<string | null>(null);

  const fetchShows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await browseSonarrShows(query || undefined);
      setShows(data.shows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load library");
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    const t = setTimeout(fetchShows, 300);
    return () => clearTimeout(t);
  }, [fetchShows]);

  // Fetch episodes when a show is selected
  const selectShow = useCallback(async (show: SonarrShow) => {
    setSelected(show);
    setEpisodes([]);
    setEpLoading(true);
    setImportResult(null);
    setProcessResult(null);
    setSelectedSeason(null);
    try {
      const data = await browseSonarrEpisodes(show.sonarr_id);
      setEpisodes(data.episodes);
      // Auto-select first season
      const seasons = [...new Set(data.episodes.map((e) => e.season))].sort((a, b) => a - b);
      if (seasons.length > 0) setSelectedSeason(seasons[0]);
    } catch {
      setEpisodes([]);
    } finally {
      setEpLoading(false);
    }
  }, []);

  async function handleImport() {
    if (!selected) return;
    setImporting(true);
    setImportResult(null);
    try {
      const res = await importShowFromSonarr(selected.sonarr_id);
      setImportResult(res.message);
    } catch (e) {
      setImportResult(`Error: ${e instanceof Error ? e.message : "Import failed"}`);
    } finally {
      setImporting(false);
    }
  }

  async function handleProcessSeason() {
    if (!selected || selectedSeason == null) return;
    setProcessing(true);
    setProcessResult(null);
    try {
      // First import to ensure records exist, then get the show_id
      const imp = await importShowFromSonarr(selected.sonarr_id);
      const res = await startSeasonProcessing(imp.show_id, selectedSeason);
      setProcessResult(res.message);
    } catch (e) {
      setProcessResult(`Error: ${e instanceof Error ? e.message : "Processing failed"}`);
    } finally {
      setProcessing(false);
    }
  }

  const seasons = [...new Set(episodes.map((e) => e.season))].sort((a, b) => a - b);
  const filteredEps = selectedSeason != null
    ? episodes.filter((e) => e.season === selectedSeason)
    : episodes;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left: Show list */}
      <div className="lg:col-span-1">
        <div className="sticky top-24">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your library..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm mb-4 placeholder-gray-500 focus:border-simpsons-yellow focus:outline-none"
          />

          {loading && <p className="text-gray-500 text-sm">Loading library...</p>}
          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="space-y-2 max-h-[calc(100vh-14rem)] overflow-y-auto pr-1">
            {shows.map((show) => (
              <button
                key={show.sonarr_id}
                onClick={() => selectShow(show)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition ${
                  selected?.sonarr_id === show.sonarr_id
                    ? "bg-gray-800 border border-simpsons-yellow/40"
                    : "bg-gray-900 border border-gray-800 hover:border-gray-700"
                }`}
              >
                {show.poster_url ? (
                  <img
                    src={show.poster_url}
                    alt=""
                    className="w-10 h-14 rounded object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-10 h-14 rounded bg-gray-700 flex-shrink-0 flex items-center justify-center text-xs text-gray-500">
                    ?
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{show.title}</p>
                  <p className="text-xs text-gray-500">
                    {show.year} &middot; {show.season_count} seasons &middot;{" "}
                    {show.episode_file_count}/{show.episode_count} files
                  </p>
                </div>
              </button>
            ))}
            {!loading && shows.length === 0 && (
              <p className="text-gray-500 text-sm text-center py-8">
                No shows found. Is Sonarr running?
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Right: Show detail & episodes */}
      <div className="lg:col-span-2">
        {!selected ? (
          <div className="flex items-center justify-center h-64 text-gray-500">
            <div className="text-center">
              <p className="text-4xl mb-3">📺</p>
              <p className="text-lg">Select a show from your Plex/Sonarr library</p>
              <p className="text-sm text-gray-600 mt-1">
                Import it into Narralytica, then batch-process entire seasons
              </p>
            </div>
          </div>
        ) : (
          <div>
            {/* Show header */}
            <div className="flex items-start gap-4 mb-6">
              {selected.poster_url && (
                <img
                  src={selected.poster_url}
                  alt=""
                  className="w-24 h-36 rounded-lg object-cover flex-shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <h2 className="text-2xl font-bold">{selected.title}</h2>
                <p className="text-sm text-gray-400 mt-1">
                  {selected.year} &middot; {selected.network} &middot;{" "}
                  {selected.genres.join(", ")}
                </p>
                <p className="text-sm text-gray-500 mt-2 line-clamp-3">
                  {selected.overview}
                </p>

                <div className="flex gap-3 mt-4">
                  <button
                    onClick={handleImport}
                    disabled={importing}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg text-sm transition disabled:opacity-50"
                  >
                    {importing ? "Importing..." : "Import to Narralytica"}
                  </button>

                  {selectedSeason != null && (
                    <button
                      onClick={handleProcessSeason}
                      disabled={processing}
                      className="bg-simpsons-yellow hover:bg-yellow-400 text-black font-medium px-4 py-2 rounded-lg text-sm transition disabled:opacity-50"
                    >
                      {processing
                        ? "Queuing..."
                        : `Process Season ${selectedSeason}`}
                    </button>
                  )}
                </div>

                {importResult && (
                  <p className={`text-sm mt-2 ${importResult.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
                    {importResult}
                  </p>
                )}
                {processResult && (
                  <p className={`text-sm mt-1 ${processResult.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
                    {processResult}
                  </p>
                )}
              </div>
            </div>

            {/* Season tabs */}
            {seasons.length > 0 && (
              <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
                {seasons.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSelectedSeason(s)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition ${
                      selectedSeason === s
                        ? "bg-simpsons-yellow text-black"
                        : "bg-gray-800 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    Season {s}
                  </button>
                ))}
              </div>
            )}

            {/* Episode list */}
            {epLoading ? (
              <p className="text-gray-500 text-sm">Loading episodes...</p>
            ) : (
              <div className="space-y-1">
                {filteredEps.map((ep) => (
                  <div
                    key={ep.sonarr_episode_id}
                    className="flex items-center gap-3 p-3 bg-gray-900 rounded-lg border border-gray-800"
                  >
                    <span className="text-xs font-mono text-gray-500 w-16 flex-shrink-0">
                      S{String(ep.season).padStart(2, "0")}E
                      {String(ep.episode_number).padStart(2, "0")}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{ep.title}</p>
                      {ep.overview && (
                        <p className="text-xs text-gray-500 truncate">{ep.overview}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {ep.file_size_mb && (
                        <span className="text-xs text-gray-500">
                          {ep.file_size_mb > 1000
                            ? `${(ep.file_size_mb / 1024).toFixed(1)} GB`
                            : `${ep.file_size_mb} MB`}
                        </span>
                      )}
                      <span
                        className={`w-2 h-2 rounded-full ${
                          ep.has_file ? "bg-green-500" : "bg-gray-600"
                        }`}
                        title={ep.has_file ? "File available" : "No file"}
                      />
                    </div>
                  </div>
                ))}
                {filteredEps.length === 0 && (
                  <p className="text-gray-500 text-sm text-center py-4">
                    No episodes found for this season.
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Drag & Drop Upload Zone
// =============================================================================
interface UploadItem {
  file: File;
  showName: string;
  season: number;
  episodeNumber: number;
  episodeTitle: string;
  status: "pending" | "uploading" | "done" | "error";
  progress: number;
  message?: string;
}

function UploadZone() {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [autoProcess, setAutoProcess] = useState(true);
  const [showName, setShowName] = useState("");
  const [season, setSeason] = useState(1);
  const [startEp, setStartEp] = useState(1);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function addFiles(files: FileList) {
    const newItems: UploadItem[] = [];
    let epNum = items.length > 0 ? Math.max(...items.map((i) => i.episodeNumber)) + 1 : startEp;
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      const ext = f.name.split(".").pop()?.toLowerCase() || "";
      if (!["mp4", "mkv", "avi", "mov", "webm", "ts"].includes(ext)) continue;
      newItems.push({
        file: f,
        showName: showName || "Untitled Show",
        season,
        episodeNumber: epNum++,
        episodeTitle: f.name.replace(/\.[^.]+$/, ""),
        status: "pending",
        progress: 0,
      });
    }
    setItems((prev) => [...prev, ...newItems]);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }

  function updateItem(idx: number, patch: Partial<UploadItem>) {
    setItems((prev) => prev.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  }

  function removeItem(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  async function uploadAll() {
    for (let i = 0; i < items.length; i++) {
      if (items[i].status !== "pending") continue;
      updateItem(i, { status: "uploading", progress: 50 });
      try {
        const res = await uploadVideo(
          items[i].file,
          items[i].showName || showName || "Untitled Show",
          items[i].season,
          items[i].episodeNumber,
          items[i].episodeTitle,
          autoProcess,
        );
        updateItem(i, {
          status: "done",
          progress: 100,
          message: res.message,
        });
      } catch (e) {
        updateItem(i, {
          status: "error",
          progress: 0,
          message: e instanceof Error ? e.message : "Upload failed",
        });
      }
    }
  }

  const pendingCount = items.filter((i) => i.status === "pending").length;

  return (
    <div>
      {/* Upload settings */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Show Name</label>
          <input
            type="text"
            value={showName}
            onChange={(e) => setShowName(e.target.value)}
            placeholder="e.g. Breaking Bad"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-simpsons-yellow focus:outline-none"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Season</label>
          <input
            type="number"
            value={season}
            onChange={(e) => setSeason(Number(e.target.value))}
            min={1}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-simpsons-yellow focus:outline-none"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Starting Episode #</label>
          <input
            type="number"
            value={startEp}
            onChange={(e) => setStartEp(Number(e.target.value))}
            min={1}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-simpsons-yellow focus:outline-none"
          />
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition ${
          dragging
            ? "border-simpsons-yellow bg-simpsons-yellow/5"
            : "border-gray-700 hover:border-gray-500 bg-gray-900/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".mp4,.mkv,.avi,.mov,.webm,.ts"
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
        <div className="text-4xl mb-3">{dragging ? "📥" : "🎬"}</div>
        <p className="text-lg font-medium">
          {dragging ? "Drop files here" : "Drag & drop video files"}
        </p>
        <p className="text-sm text-gray-500 mt-1">
          MP4, MKV, AVI, MOV, WebM, TS &middot; or click to browse
        </p>
      </div>

      {/* File queue */}
      {items.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">
              Upload Queue ({items.length} file{items.length !== 1 && "s"})
            </h3>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={autoProcess}
                  onChange={(e) => setAutoProcess(e.target.checked)}
                  className="rounded"
                />
                <span className="text-gray-400">Auto-process after upload</span>
              </label>
              {pendingCount > 0 && (
                <button
                  onClick={uploadAll}
                  className="bg-simpsons-yellow text-black font-medium px-4 py-1.5 rounded-lg text-sm hover:bg-yellow-400 transition"
                >
                  Upload {pendingCount} File{pendingCount !== 1 && "s"}
                </button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {items.map((item, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-3 bg-gray-900 rounded-lg border border-gray-800"
              >
                {/* Status indicator */}
                <div className="flex-shrink-0">
                  {item.status === "pending" && (
                    <span className="w-2 h-2 rounded-full bg-gray-500 block" />
                  )}
                  {item.status === "uploading" && (
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse block" />
                  )}
                  {item.status === "done" && (
                    <span className="text-green-400 text-sm">&#10003;</span>
                  )}
                  {item.status === "error" && (
                    <span className="text-red-400 text-sm">&#10007;</span>
                  )}
                </div>

                {/* Episode number (editable) */}
                <input
                  type="number"
                  value={item.episodeNumber}
                  onChange={(e) =>
                    updateItem(idx, { episodeNumber: Number(e.target.value) })
                  }
                  className="w-14 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-center"
                  disabled={item.status !== "pending"}
                />

                {/* Title (editable) */}
                <input
                  type="text"
                  value={item.episodeTitle}
                  onChange={(e) => updateItem(idx, { episodeTitle: e.target.value })}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-1 text-sm min-w-0"
                  disabled={item.status !== "pending"}
                />

                {/* File size */}
                <span className="text-xs text-gray-500 flex-shrink-0 w-16 text-right">
                  {item.file.size > 1024 * 1024 * 1024
                    ? `${(item.file.size / (1024 * 1024 * 1024)).toFixed(1)} GB`
                    : `${Math.round(item.file.size / (1024 * 1024))} MB`}
                </span>

                {/* Message */}
                {item.message && (
                  <span
                    className={`text-xs truncate max-w-[200px] ${
                      item.status === "error" ? "text-red-400" : "text-green-400"
                    }`}
                    title={item.message}
                  >
                    {item.message}
                  </span>
                )}

                {/* Remove button */}
                {item.status === "pending" && (
                  <button
                    onClick={() => removeItem(idx)}
                    className="text-gray-500 hover:text-red-400 text-sm flex-shrink-0"
                  >
                    &#10005;
                  </button>
                )}
              </div>
            ))}
          </div>

          {items.every((i) => i.status === "done") && (
            <div className="mt-4 p-4 bg-green-900/20 border border-green-800/30 rounded-lg text-center">
              <p className="text-green-400 font-medium">
                All files uploaded successfully!
              </p>
              <a
                href="/admin"
                className="text-sm text-simpsons-yellow hover:underline mt-1 inline-block"
              >
                View processing queue &rarr;
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Intake Page
// =============================================================================
export default function IntakePage() {
  const [activeTab, setActiveTab] = useState<Tab>("library");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-simpsons-yellow">Intake</h1>
          <p className="text-gray-400 text-sm mt-1">
            Import from your Plex library or upload video files directly
          </p>
        </div>
        <a
          href="/admin"
          className="text-sm text-gray-400 hover:text-simpsons-yellow transition"
        >
          &larr; Processing Queue
        </a>
      </div>

      <TabBar active={activeTab} onChange={setActiveTab} />

      {activeTab === "library" ? <LibraryBrowser /> : <UploadZone />}
    </div>
  );
}
