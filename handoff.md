# Narralytica v2 — Handoff (Updated 2026-04-05)

## Quick Start
```bash
# Read this file first, then check the Master Brief and Errata in ~/Downloads/
# The project is live at https://weftwarp.com (also https://captainofindustries.com)
# GitHub: https://github.com/Erstiv/Narralytica
```

---

## What's Done (Phases 1–3 + Session 3)

### Session 3 Accomplishments (2026-03-28)
1. **DB renamed**: `narrowlitics` → `narralytica` (user, database, .env all updated)
2. **35+ field metadata schema**: Migration 005 added 29 columns. Gemini prompt rewritten for full extraction. Scene data now includes cinematography, audio, humor classification, cultural references, 5-dimensional explicitness, location details, emotional arc, and more.
3. **CutPrint™ scene detection**: Two-pass algorithm — ContentDetector finds raw camera cuts, then merge algorithm groups them into story-level scenes. Results went from 9 garbage scenes (one was 15 minutes) to **25 proper scenes** (median 52s).
4. **CutPrint calibration script**: `cutprint_calibrate.py` auto-picks 3 episodes, sweeps thresholds + min_scene_durations, scores distributions, outputs optimal profile. 6 genre presets.
5. **Plex Mac setup**: Homebrew, Python 3.12, FFmpeg 8.1, venv with scenedetect+opencv. Passwordless sudo for `jers`.
6. **Tailscale confirmed**: Hetzner ↔ Plex Mac tunnel working.
7. **Semantic search verified**: "dental plan" → correct union scene (0.762 similarity).

### What Was Already Working
- Frontend: Dashboard, Search, Admin pages at captainofindustries.com
- Backend: FastAPI + Celery + Postgres/pgvector
- Full processing pipeline: compress → detect → transcribe → analyze → embed → ingest
- Export: SRT, script JSON, metadata CSV/JSON, DOCX
- Library management: Sonarr/Radarr integration for show import

---

## Architecture

### Servers
| Machine | Role | IP | Access |
|---------|------|----|--------|
| **Hetzner (Filou)** | Backend, DB, Sonarr/Radarr, Nginx | 178.156.251.26 / Tailscale: 100.71.72.6 | `ssh filou` (root) |
| **Plex Mac** | Media storage, processing | LAN: 192.168.0.147 / Tailscale: 100.108.190.10 | `ssh filou` then `ssh jers@100.108.190.10` |
| **M5 Mac** | Development | local | Elliot's work machine |

### Services on Hetzner (`/var/www/narralytica/`)
| Service | Port | Container |
|---------|------|-----------|
| Narralytica Backend (FastAPI) | 8005 | `narralytica-backend` |
| Narralytica Frontend (React) | 3020 | `narralytica-frontend` |
| Narralytica Worker (Celery) | — | `narralytica-worker` |
| Narralytica DB (Postgres+pgvector) | 5433 | `narralytica-db` |
| Sonarr | 8989 | standalone |
| Radarr | 7878 | standalone |
| Thea Panel | 3005 | PM2: `thea-panel` |
| Nginx | 80/443 | system |

**DO NOT TOUCH:** Sonarr, Radarr, Thea, Nginx, or any non-Narralytica service.

### Coexisting Services (ports to avoid)
Cassian (8003), Googloid (3000), lucidnidra (3001), marilynstivers (3002), the-sighs (3003), plinkatron (3005), snap-and-grab (3010), SONIX (Docker internal), full *arr stack.

### Credentials
```
# Narralytica DB (UPDATED - was narrowlitics)
POSTGRES_USER=narralytica
POSTGRES_PASSWORD=017c23c0ab7c64f144057c85d09a2efe
POSTGRES_DB=narralytica

# APIs
GEMINI_API_KEY=AIzaSyDqUVSt2T9yEla1tniElj2UY-JsGINUNXU
SONARR_API_KEY=e068e976a5704fd0a74a4abc7bbb393c
RADARR_API_KEY=9008a9c7473d47d3a43e026731568f06
PLEX_TOKEN=PQAmJ4YXSKexz1ubB-Cb
```

### Media Paths
| Location | Path | Contents |
|----------|------|----------|
| Hetzner (downloads) | `/data/media/tv/`, `/data/media/movies/` | Sonarr/Radarr download staging |
| Plex Mac - Chaos | `/Volumes/Chaos/TV Shows/`, `/Volumes/Chaos/Movies/` | 20TB, ~6000 movies |
| Plex Mac - Luchagaido | `/Volumes/Luchagaido/TV Shows/`, `/Volumes/Luchagaido/Movies/` | 12TB, newer content |

---

## API Endpoints (port 8005)
```
GET  /api/health
GET  /api/episodes/
GET  /api/episodes/{id}
PATCH /api/episodes/{id}/status
POST /api/scenes/episode/{id}/bulk          — Ingest scenes (with embeddings)
GET  /api/scenes/episode/{id}               — List scenes for episode
GET  /api/scenes/{id}                       — Single scene
POST /api/search/                           — Semantic search {query, limit}
GET  /api/export/{id}/srt                   — SRT subtitles
GET  /api/export/{id}/script-json           — Transcript JSON
GET  /api/export/{id}/metadata-json         — Full metadata JSON
GET  /api/export/{id}/metadata-csv          — CSV export
GET  /api/export/{id}/script-docx           — Word document
GET  /api/library/sonarr/shows              — Browse Sonarr
GET  /api/library/sonarr/shows/{id}/episodes
POST /api/library/import/{sonarr_id}        — Import show from Sonarr
GET  /api/library/shows                     — List imported shows
GET  /api/library/shows/{id}                — Show detail + cutprint
POST /api/library/shows/{id}/cutprint       — Save CutPrint profile
GET  /api/library/shows/{id}/cutprint       — Get CutPrint profile
GET  /api/media/thumbs/scene_XX.jpg         — Thumbnails
GET  /api/media/clips/scene_XX.mp4          — Video clips
```

---

## Processing Scripts

### On Plex Mac (`/Users/jers/narralytica/processing/scripts/`)
Run with `/Users/jers/narralytica-venv/bin/python3.12`

| Script | Purpose | Status |
|--------|---------|--------|
| `cutprint_calibrate.py` | CutPrint™ auto-calibration (3 episodes, threshold + min_scene sweep) | ✅ NEW |
| `detect_scenes.py` | Scene detection with CutPrint merge (`--threshold`, `--min-scene`, `--profile`) | ✅ UPDATED |
| `gemini_index.py` | Gemini 2.5 Flash analysis (35+ field prompt, show-agnostic) | ✅ UPDATED |
| `generate_embeddings.py` | text-embedding-004, 1536-dim embeddings with enriched text | ✅ UPDATED |
| `compress.py` | FFmpeg 720p 1fps compression | ✅ |
| `transcribe_whisper.py` | faster-whisper large-v3 word-level | ✅ |
| `merge_transcript.py` | Merge Whisper + Gemini speaker names | ✅ |
| `push_scenes.py` | POST to bulk ingest API | ✅ |
| `extract_media.py` | Thumbnails + clips per scene | ✅ |
| `run_pipeline.py` | Full orchestrator | ✅ |

### Plex Mac Venv Status
Installed: scenedetect, opencv-python
**Still needs:** faster-whisper, google-genai, rapidfuzz, fastapi, uvicorn, httpx

```bash
/Users/jers/narralytica-venv/bin/pip install faster-whisper google-genai rapidfuzz fastapi uvicorn httpx
```

---

## CutPrint™ System

### How It Works
1. **Raw detection**: `ContentDetector(threshold=T)` finds every camera cut (~17/min for animation)
2. **Merge**: Groups consecutive cuts into story-level scenes by enforcing `min_scene_duration`
3. **Two-pass merge**: Forward accumulation pass + cleanup pass for tail scenes

### Genre Presets
| Genre | Threshold Range | Min Scene Range | Target Median |
|-------|----------------|-----------------|---------------|
| classic_animation | 18-30 | 40-70s | 50s |
| modern_animation | 22-35 | 35-60s | 45s |
| anime | 20-32 | 50-90s | 65s |
| live_action_comedy | 28-42 | 35-60s | 50s |
| live_action_drama | 28-42 | 50-90s | 65s |
| reality | 30-45 | 30-60s | 45s |

### Calibration Status
- **The Simpsons**: Manual calibration validated (threshold=22, min_scene=50 → 25 scenes). Formal auto-calibration was IN PROGRESS when session ended. Check `/tmp/cutprint_simpsons.json` on Plex Mac.
- **Danger 5**: Not yet calibrated. Available at `/Volumes/Chaos/TV Shows/Danger 5/Season 1`. Use `--genre live_action_comedy`.

### DB Storage
Shows table has: `cutprint_threshold`, `cutprint_min_scene`, `cutprint_genre`, `cutprint_calibrated_at`, `cutprint_profile` (JSONB).

---

## Database Tables
- `shows` — show metadata + CutPrint profile (migration 006)
- `episodes` — episode tracking with status
- `scenes` — **25 indexed scenes** with 42+ fields each, 1536-dim embeddings (migrations 005, 006)
- `scene_objects` — normalized object tags
- `search_history` — search analytics
- `tweaks` — Phase 4 stub

---

## Deploy Pattern
```bash
# From M5 Mac:
cd ~/narralytica && git add -A && git commit -m "message" && git push origin main

# Hetzner:
ssh filou 'cd /var/www/narralytica && git pull && docker compose up -d --force-recreate narralytica-backend'

# Plex Mac:
ssh filou "ssh jers@100.108.190.10 'cd /Users/jers/narralytica && git pull'"
```

---

## What's Next

### Immediate Priority
1. **Video previews don't play** — Homestead (333 scenes), Wayfinders (386), and Wingfeather (200) all have full Gemini analysis + embeddings but NO thumbnails or video clips extracted. The `extract_media.py` script needs to be run for each show. This requires access to the original video files on the Plex Mac.
2. Check CutPrint calibration result on Plex Mac (`/tmp/cutprint_simpsons.json`), save to DB
3. Calibrate Danger 5 (proves cross-genre CutPrint)
4. Install remaining pip packages on Plex Mac venv

### Current State of All Shows
| Show | Episodes | Scenes | Status | Video Clips |
|------|----------|--------|--------|-------------|
| Homestead | 8/8 ready | 333 | ✅ Fully indexed | ❌ No clips/thumbs |
| Wayfinders | 6/6 ready | 386 | ✅ Fully indexed | ❌ No clips/thumbs |
| Wingfeather Saga | 6/6 ready | 200 | ✅ Fully indexed | ❌ No clips/thumbs |
| Simpsons | 1/801 ready | 25 | POC only | ❌ No clips/thumbs |
| Danger 5 | 0/13 ready | 0 | Not started | ❌ |

### Domain Setup
- **weftwarp.com** — Primary domain, SSL via Let's Encrypt, nginx on Filou
- **captainofindustries.com** — Also works (legacy domain)
- Frontend env `BACKEND_URL` is set to `https://weftwarp.com` in `.env` on Hetzner
- CORS allows both domains

### Stage C (from Master Brief)
- Build Plex-side FastAPI processing server (receives jobs from Hetzner via Tailscale)
- Whisper transcript merge into expanded scene data
- Frontend updates for 35+ field display
- Batch processing (queue full seasons)

### Stage D (Tweak Studio)
- AI-generated scene transitions via Veo 3.1
- Client dashboard with usage analytics

---

## Gotchas
- **OGM/AVI files** need FFmpeg conversion before OpenCV/PySceneDetect. `convert_if_needed()` handles this automatically.
- **Gemini returns inconsistent types** — `_to_str()` helper in `scenes.py` coerces lists to semicolon-joined strings.
- **Double SSH hop** to Plex Mac — output is buffered until command finishes.
- **Another Claude instance** may be working on Thea (Project Thea, plex media center) on the Plex Mac. Different project/language/ports — no conflict.
- **Elliot is a beginner** with server management — explain commands clearly.
- **Prefer Python scripts** over heredocs (heredocs break with Jinja2).
- **Never kill processes** without being asked.
