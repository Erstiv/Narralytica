"use client";

import { useEffect, useState } from "react";
import { getShows, getHealth, type ShowSummary } from "@/lib/api";

// --- Show Card ---
function ShowCard({ show }: { show: ShowSummary }) {
  return (
    <a
      href={`/show/${show.id}`}
      className="flex-shrink-0 w-48 group cursor-pointer"
    >
      <div className="relative aspect-[2/3] rounded-lg overflow-hidden bg-gray-800 shadow-lg group-hover:ring-2 group-hover:ring-simpsons-yellow transition-all group-hover:scale-105 duration-200">
        {show.poster_url ? (
          <img
            src={show.poster_url}
            alt={show.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600 text-sm">
            No Poster
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/80 to-transparent" />
        <div className="absolute bottom-2 left-2 right-2">
          <p className="text-sm font-semibold truncate">{show.name}</p>
          <p className="text-xs text-gray-400">
            {show.year} &middot; {show.episode_count} eps
          </p>
        </div>
      </div>
    </a>
  );
}

// --- Horizontal Scroll Row ---
function ShowRow({ title, shows }: { title: string; shows: ShowSummary[] }) {
  if (shows.length === 0) return null;
  return (
    <section>
      <h2 className="text-xl font-semibold mb-3">{title}</h2>
      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
        {shows.map((show) => (
          <ShowCard key={show.id} show={show} />
        ))}
      </div>
    </section>
  );
}

// --- Hero Banner ---
function HeroBanner({ show }: { show: ShowSummary }) {
  return (
    <div className="relative w-full h-[400px] rounded-xl overflow-hidden mb-8">
      {show.fanart_url ? (
        <img
          src={show.fanart_url}
          alt={show.name}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full bg-gradient-to-r from-gray-900 to-gray-800" />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/40 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-r from-gray-950/80 to-transparent" />

      <div className="absolute bottom-8 left-8 max-w-lg">
        <h1 className="text-4xl font-bold mb-2">{show.name}</h1>
        <div className="flex items-center gap-3 text-sm text-gray-300 mb-4">
          {show.year && <span>{show.year}</span>}
          {show.network && <span>{show.network}</span>}
          <span>{show.episode_count} episodes</span>
        </div>
        <div className="flex gap-2 mb-3">
          {show.genres.map((g) => (
            <span key={g} className="bg-gray-800/80 px-2 py-1 rounded text-xs text-gray-300">
              {g}
            </span>
          ))}
        </div>
        <div className="flex gap-3">
          <a
            href={`/show/${show.id}`}
            className="bg-simpsons-yellow text-black font-semibold px-6 py-2.5 rounded-lg hover:bg-yellow-400 transition text-sm"
          >
            View Show
          </a>
          <a
            href="/search"
            className="bg-gray-800/80 text-white px-6 py-2.5 rounded-lg hover:bg-gray-700 transition text-sm"
          >
            Search Scenes
          </a>
        </div>
      </div>
    </div>
  );
}

// --- Main Splash Page ---
export default function SplashPage() {
  const [shows, setShows] = useState<ShowSummary[]>([]);
  const [health, setHealth] = useState<string>("checking...");

  useEffect(() => {
    getHealth()
      .then(() => setHealth("connected"))
      .catch(() => setHealth("offline"));
    getShows()
      .then(setShows)
      .catch(() => {});
  }, []);

  const animated = shows.filter((s) =>
    s.genres.some((g) => g.toLowerCase().includes("animation"))
  );
  const liveAction = shows.filter(
    (s) => !s.genres.some((g) => g.toLowerCase().includes("animation"))
  );

  const hero = shows.length > 0
    ? shows.reduce((a, b) => (a.episode_count > b.episode_count ? a : b))
    : null;

  return (
    <div className="space-y-8 -mt-4">
      <div className="flex justify-end">
        <span className={`text-xs ${health === "connected" ? "text-green-500" : "text-red-500"}`}>
          {health === "connected" ? "API Connected" : "API Offline"}
        </span>
      </div>

      {hero && <HeroBanner show={hero} />}

      <ShowRow title="All Shows" shows={shows} />
      <ShowRow title="Animation" shows={animated} />
      <ShowRow title="Live Action" shows={liveAction} />

      {shows.length === 0 && health === "connected" && (
        <div className="text-center py-16">
          <p className="text-2xl text-gray-400 mb-4">No shows yet</p>
          <p className="text-gray-500">
            Import a show from the{" "}
            <a href="/admin" className="text-simpsons-yellow hover:underline">
              Admin page
            </a>{" "}
            to get started.
          </p>
        </div>
      )}
    </div>
  );
}
