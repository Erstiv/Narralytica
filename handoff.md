# Narralytica Handoff — Phases 1–3 Complete

## What's Done

Narralytica is live at **https://captainofindustries.com** with all 4 Docker containers running on Hetzner (178.156.251.26, SSH alias: `filou`). The POC episode (Simpsons S04E17 "Last Exit to Springfield") is fully indexed, searchable, and exportable.

### Architecture on Hetzner (`/var/www/narralytica/`)
- **narralytica-frontend**: Next.js 15 + React 19, port 3020 → proxied through nginx
- **narralytica-backend**: FastAPI, port 8005 → proxied at `/api/`
- **narralytica-db**: PostgreSQL 16 + pgvector, port 5433
- **narralytica-worker**: Celery (stub, ready for background tasks)
- **Nginx**: SSL via Let's Encrypt, auto-renewing
- **Media**: Thumbnails + clips served from `/api/media/` via Docker volume

### GitHub
Repo: https://github.com/Erstiv/Narralytica

### M5 Mac (`~/narralytica/`)
Processing machine for heavy work (FFmpeg, Whisper, Gemini uploads). Contains:
- `input/simpsons_s04e17.ogm` — original episode (175.5 MB)
- `processing/output/compressed.mp4` — 720p 1fps version (80.9 MB)
- `processing/output/scenes.json` — 9 scene boundaries
- `processing/output/scenes_gemini.json` — Gemini analysis with objects
- `processing/output/whisper_transcript.json` — word-level transcript (1,997 words)
- `processing/output/scenes_merged.json` — merged transcript with named speakers
- `processing/output/scenes_final.json` — final with 768-dim embeddings
- `processing/output/media/thumbs/` — 9 JPG thumbnails
- `processing/output/media/clips/` — 9 MP4 clips (204 MB total)

---

## What's Working

### Frontend Pages
- `/` — Dashboard (episode pipeline status, quick stats)
- `/search` — Semantic search with real thumbnails, video preview overlay, clip downloads
- `/tweak` — Tweak Studio placeholder (Phase 4)
- `/admin` — Admin panel (re-index, export, usage stats)

### API Endpoints
```
GET  /api/health                         — health check
GET  /api/episodes/                      — list episodes
GET  /api/episodes/{id}                  — get episode
PATCH /api/episodes/{id}/status          — update episode status
GET  /api/scenes/episode/{id}            — list scenes for episode
GET  /api/scenes/{id}                    — get scene
POST /api/scenes/episode/{id}/bulk       — bulk ingest (scenes + objects + embeddings + transcript)
POST /api/search/                        — hybrid vector + SQL search (returns {scene, similarity})
GET  /api/export/{id}/srt                — diarized SRT subtitles
GET  /api/export/{id}/script-json        — rich transcript JSON
GET  /api/export/{id}/metadata-json      — full scene metadata JSON
GET  /api/export/{id}/metadata-csv       — Excel-friendly CSV
GET  /api/export/{id}/script-docx        — formatted Word script
GET  /api/media/thumbs/scene_XX.jpg      — scene thumbnails
GET  /api/media/clips/scene_XX.mp4       — scene video clips
```

### Database Tables
- `shows` — show metadata
- `episodes` — episode tracking with status
- `scenes` — 9 indexed scenes with characters, dialog, actions, mood, objects, embeddings, merged transcript
- `scene_objects` — normalized object tags (food, vehicle, prop, etc.)
- `search_history` — search analytics
- `tweaks` — Phase 4 stub

### Processing Scripts (M5 Mac)
```
processing/scripts/
├── compress.py              — FFmpeg 720p/1fps compression
├── detect_scenes.py         — PySceneDetect content-aware boundaries
├── whisper_transcribe.py    — faster-whisper large-v3 word-level transcription
├── gemini_index.py          — Gemini 2.5 Flash scene analysis + object tagging
├── merge_transcript.py      — reconcile Whisper verbatim + Gemini speaker names
├── generate_embeddings.py   — gemini-embedding-001, 768-dim, truncated
├── push_scenes.py           — POST to /api/scenes/episode/{id}/bulk
├── extract_media.py         — FFmpeg thumbnails + clips per scene
└── run_pipeline.py          — orchestrator (Whisper+Gemini parallel → merge → embed → push)
```

### Full Pipeline Command (M5 Mac)
```bash
export GEMINI_API_KEY=your_key
cd ~/narralytica
python3 processing/scripts/run_pipeline.py input/simpsons_s04e17.ogm processing/output/scenes.json
```
Takes ~24 minutes. Steps 4 (Whisper) and 5 (Gemini) run in parallel.

---

## Key Technical Details

### Search Architecture
- Query text → embedded via `gemini-embedding-001` (768-dim, RETRIEVAL_QUERY task type)
- pgvector cosine similarity against stored scene embeddings (RETRIEVAL_DOCUMENT at index time)
- SQL filters (characters, min_confidence) applied on top
- Falls back to text ILIKE search if embedding fails
- Returns `SearchResult` = `{scene: SceneOut, similarity: float}`

### Database Credentials (Server .env)
The PostgreSQL data directory was initialized with user/db `narrowlitics` (pre-rename). The `.env` on Hetzner keeps `POSTGRES_USER=narrowlitics` and `POSTGRES_DB=narrowlitics` to match the existing data. Don't change these — Docker Compose templates reference them via `${POSTGRES_USER:-narralytica}` defaults that get overridden.

### Python Architecture Issues (M5 Mac)
The system Python 3.14 has x86_64/arm64 architecture conflicts. Key fixes applied:
- `pydantic-core` arm64 .so manually copied from `--platform macosx_11_0_arm64` download
- FFmpeg is at `/opt/homebrew/bin/ffmpeg` — needs `PATH="/opt/homebrew/bin:$PATH"`
- faster-whisper, rapidfuzz, google-genai all installed and working

### Transcript Merge Quality
The merge uses timestamp alignment + fuzzy string matching (rapidfuzz). Current results:
- 346 total transcript segments across 9 scenes
- 147 speakers auto-identified, 199 flagged for manual review
- This is expected with Option B (simple alignment). Option A (pyannote-audio) would improve this.

### Renamed from Narrowlitics
The project was renamed from "Narrowlitics" to "Narralytica" on 2026-03-27. The old repo at `github.com/Erstiv/Narrowlitics` still exists but is stale. All work is in `github.com/Erstiv/Narralytica`.

---

## Coexisting Services on Hetzner (DO NOT DISTURB)
- Cassian: port 8003, planterpruner.com
- Googloid: port 3000, googloid.com
- SONIX: Docker (internal)
- Plus: lucidnidra (3001), marilynstivers (3002), the-sighs (3003), plinkatron (3005), snap-and-grab (3010), and the full *arr stack

---

## What's Next: Phase 4 (Tweak Studio)

The remaining planned work:
1. **Tweak Studio** — AI-generated scene transitions via Veo 3.1
2. **Batch processing** — scale to full season ingestion (multi-episode)
3. **pyannote-audio** — improved speaker diarization for transcript accuracy
4. **Client dashboard** — usage analytics and billing
5. **Scene detection tuning** — the 892s first scene suggests threshold needs adjustment

---

## Important Rules for This Server
- **NEVER kill processes** without being explicitly asked
- Use `systemctl` for service management
- Prefer Python file-write scripts over heredoc blocks (heredocs break with Jinja2)
- Push to GitHub regularly: `github.com/Erstiv/Narralytica`
- Elliot is a beginner with server management — explain commands clearly
- Port map: backend=8005, frontend=3020, db=5433
- Deploy pattern: `ssh filou "cd /var/www/narralytica && git pull && docker compose up --build -d"`
