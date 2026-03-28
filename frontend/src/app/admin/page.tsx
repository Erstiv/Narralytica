"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getProcessingHealth,
  getProcessingJobs,
  startProcessing,
  type ProcessingJob,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

// --- Processing Job Card ---
function JobCard({ job }: { job: ProcessingJob }) {
  const statusColors: Record<string, string> = {
    queued: "bg-gray-600",
    running: "bg-blue-600",
    completed: "bg-green-600",
    failed: "bg-red-600",
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-mono text-gray-400">Job {job.job_id}</span>
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[job.status] || "bg-gray-600"}`}
        >
          {job.status}
        </span>
      </div>

      <p className="text-sm text-gray-300">Episode #{job.episode_id}</p>

      {job.status === "running" && (
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>{job.current_step}</span>
            <span>{job.progress_pct}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div
              className="bg-simpsons-yellow h-2 rounded-full transition-all duration-500"
              style={{ width: `${job.progress_pct}%` }}
            />
          </div>
        </div>
      )}

      {job.status === "completed" && job.elapsed_seconds && (
        <p className="text-xs text-gray-500 mt-1">
          Completed in {Math.round(job.elapsed_seconds)}s
        </p>
      )}

      {job.status === "failed" && job.error && (
        <p className="text-xs text-red-400 mt-1 truncate" title={job.error}>
          {job.error}
        </p>
      )}
    </div>
  );
}

// --- Batch Season Form ---
function BatchForm({ onQueued }: { onQueued: () => void }) {
  const [showId, setShowId] = useState("1");
  const [season, setSeason] = useState("4");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function handleBatch() {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(
        `${API_URL}/api/process/season/${showId}/${season}`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ skip_indexed: true }) }
      );
      const data = await res.json();
      if (res.ok) {
        setResult(`Queued ${data.queued} episodes, skipped ${data.skipped}`);
        onQueued();
      } else {
        setResult(`Error: ${data.detail || "Unknown error"}`);
      }
    } catch {
      setResult("Failed to connect to API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
      <h3 className="font-semibold mb-3">Batch Process Season</h3>
      <div className="flex gap-3 items-end">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Show ID</label>
          <input
            type="number"
            value={showId}
            onChange={(e) => setShowId(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-20"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Season</label>
          <input
            type="number"
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm w-20"
          />
        </div>
        <button
          onClick={handleBatch}
          disabled={loading}
          className="bg-simpsons-yellow text-black font-semibold px-4 py-2 rounded hover:bg-yellow-400 transition disabled:opacity-50 text-sm"
        >
          {loading ? "Queuing..." : "Queue Season"}
        </button>
      </div>
      {result && (
        <p className={`text-sm mt-2 ${result.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
          {result}
        </p>
      )}
    </div>
  );
}

// --- Main Admin Page ---
export default function AdminPage() {
  const [plexHealth, setPlexHealth] = useState<Record<string, unknown> | null>(null);
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [pollKey, setPollKey] = useState(0);

  const refreshJobs = useCallback(() => {
    getProcessingJobs()
      .then((data) => setJobs(data.jobs || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    getProcessingHealth()
      .then(setPlexHealth)
      .catch(() => setPlexHealth(null));
    refreshJobs();
  }, [refreshJobs]);

  // Poll jobs every 5s when there are active ones
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === "running" || j.status === "queued");
    if (!hasActive) return;

    const interval = setInterval(refreshJobs, 5000);
    return () => clearInterval(interval);
  }, [jobs, refreshJobs]);

  const activeJobs = jobs.filter((j) => j.status === "running" || j.status === "queued");
  const completedJobs = jobs.filter((j) => j.status === "completed");
  const failedJobs = jobs.filter((j) => j.status === "failed");

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-simpsons-yellow">Admin</h1>

      {/* Plex Server Status */}
      <section>
        <h2 className="text-xl font-semibold mb-3">Processing Server</h2>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          {plexHealth ? (
            <div className="flex flex-wrap gap-6 text-sm">
              <div>
                <span className="text-gray-400">Status:</span>{" "}
                <span className="text-green-400">Connected</span>
              </div>
              <div>
                <span className="text-gray-400">Python:</span>{" "}
                <span className="text-gray-300">{String(plexHealth.python)}</span>
              </div>
              <div>
                <span className="text-gray-400">FFmpeg:</span>{" "}
                <span className={plexHealth.ffmpeg ? "text-green-400" : "text-red-400"}>
                  {plexHealth.ffmpeg ? "Yes" : "No"}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Gemini Key:</span>{" "}
                <span className={plexHealth.gemini_key_set ? "text-green-400" : "text-red-400"}>
                  {plexHealth.gemini_key_set ? "Set" : "Missing"}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Active:</span>{" "}
                <span className="text-gray-300">{String(plexHealth.active_jobs)}</span>
              </div>
              <div>
                <span className="text-gray-400">Queued:</span>{" "}
                <span className="text-gray-300">{String(plexHealth.queued_jobs)}</span>
              </div>
            </div>
          ) : (
            <p className="text-red-400 text-sm">
              Cannot reach Plex processing server. Is it running?
            </p>
          )}
        </div>
      </section>

      {/* Batch Processing */}
      <section>
        <h2 className="text-xl font-semibold mb-3">Batch Processing</h2>
        <BatchForm onQueued={refreshJobs} />
      </section>

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-3">
            Active Jobs ({activeJobs.length})
          </h2>
          <div className="grid gap-3">
            {activeJobs.map((job) => (
              <JobCard key={job.job_id} job={job} />
            ))}
          </div>
        </section>
      )}

      {/* Completed Jobs */}
      {completedJobs.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-3">
            Completed ({completedJobs.length})
          </h2>
          <div className="grid gap-3">
            {completedJobs.map((job) => (
              <JobCard key={job.job_id} job={job} />
            ))}
          </div>
        </section>
      )}

      {/* Failed Jobs */}
      {failedJobs.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-3">
            Failed ({failedJobs.length})
          </h2>
          <div className="grid gap-3">
            {failedJobs.map((job) => (
              <JobCard key={job.job_id} job={job} />
            ))}
          </div>
        </section>
      )}

      {/* Quick Stats */}
      <section>
        <h2 className="text-xl font-semibold mb-3">Stats</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-simpsons-yellow">{jobs.length}</p>
            <p className="text-sm text-gray-400">Total Jobs</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-green-400">{completedJobs.length}</p>
            <p className="text-sm text-gray-400">Completed</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-red-400">{failedJobs.length}</p>
            <p className="text-sm text-gray-400">Failed</p>
          </div>
        </div>
      </section>
    </div>
  );
}
