"use client";

import { useState } from "react";
import { searchScenes, type SearchResult } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
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

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-simpsons-yellow">Search Scenes</h1>

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

      {/* Results */}
      <div className="space-y-4">
        {searched && results.length === 0 && (
          <p className="text-gray-500 text-center py-8">
            No scenes found. Try a different query or index an episode first.
          </p>
        )}

        {results.map((result) => (
          <div
            key={result.scene.id}
            className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex gap-4"
          >
            {/* Thumbnail placeholder */}
            <div className="w-40 h-24 bg-gray-800 rounded flex-shrink-0 flex items-center justify-center text-gray-600 text-xs">
              {formatTime(result.scene.start_timestamp)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
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
                  &ldquo;{result.scene.key_dialog[0].exact_quote || result.scene.key_dialog[0].quote}&rdquo;
                </p>
              )}

              {result.scene.description_text && (
                <p className="text-sm text-gray-500 mt-1 truncate">
                  {result.scene.description_text}
                </p>
              )}

              <div className="flex gap-2 mt-2">
                <button className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition">
                  Preview
                </button>
                <button className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition">
                  Extract Full-Res
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
