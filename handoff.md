# Narralytica Handoff — Phase 1 Complete

## What's Done

Narralytica is live at **https://captainofindustries.com** with all 4 Docker containers running on Hetzner (178.156.251.26, SSH alias: `filou`).

### Architecture on Hetzner (`/var/www/narralytica/`)
- **narralytica-frontend**: Next.js 15, port 3020 → proxied through nginx
- **narralytica-backend**: FastAPI, port 8005 → proxied at `/api/`
- **narralytica-db**: PostgreSQL 16 + pgvector, port 5433
- **narralytica-worker**: Celery (stub, ready for Phase 2 tasks)
- **Nginx**: SSL via Let's Encrypt, auto-renewing

### GitHub
Repo: https://github.com/Erstiv/Narralytica — all code is there.

### Frontend Pages (all working)
- `/` — Dashboard (shows episode pipeline status, quick stats)
- `/search` — Natural language scene search
- `/tweak` — Tweak Studio placeholder (Phase 4)
- `/admin` — Admin panel (re-index, export, usage stats)

### API Endpoints (all working)
- `GET /api/health` — health check
- `GET /api/episodes/` — list episodes
- `GET /api/episodes/{id}` — get episode
- `PATCH /api/episodes/{id}/status` — update episode status
- `GET /api/scenes/episode/{id}` — list scenes for episode
- `GET /api/scenes/{id}` — get scene
- `POST /api/scenes/episode/{id}/bulk` — bulk ingest Gemini scene data
- `POST /api/search/` — hybrid search (SQL filters now, vector in Phase 2)

### Database
Pre-seeded with The Simpsons show + S04E17 "Last Exit to Springfield" (status: pending).

### Coexisting Services (untouched)
- Cassian: port 8003, planterpruner.com (just fixed SSL today)
- Googloid: port 3000, googloid.com
- SONIX: Docker (internal)
- Plus: lucidnidra (3001), marilynstivers (3002), the-sighs (3003), plinkatron (3005), snap-and-grab (3010), and the full *arr stack

---

## What Elliot Needs Help With Next

### Step 1: Add Gemini API Key to Server

Elliot has the key but needs help adding it to the `.env` file on Hetzner.

The file is at `/var/www/narralytica/.env` on the server (SSH alias: `filou`).

The line to update is `GEMINI_API_KEY=` — put the key after the equals sign.

After updating, restart the backend:
```bash
ssh filou "cd /var/www/narralytica && docker compose restart narralytica-backend narralytica-worker"
```

### Step 2: Get the Simpsons Episode to M5 Mac

The episode file lives on Elliot's local Plex server. He needs to:
1. Find the file on Plex (likely an `.mkv` in Plex's media directory)
2. Copy it to somewhere on the M5 Mac (e.g., `~/narralytica/input/`)

Plex media is typically stored in a path like `/Volumes/...` or wherever Elliot configured it. He may need help locating the exact file path.

### Step 3: Compress the Episode (on M5 Mac)

The compression script is in the repo. Elliot needs to:

1. Clone the repo on the M5 Mac (if not already):
```bash
git clone https://github.com/Erstiv/Narralytica.git ~/narralytica
```

2. Make sure FFmpeg is installed:
```bash
brew install ffmpeg
```

3. Run the compression script:
```bash
cd ~/narralytica
python3 processing/scripts/compress.py /path/to/simpsons_s04e17.mkv processing/output/compressed.mp4
```

This takes the original file (1-4 GB), shrinks it to 720p at 1 FPS, and outputs a 50-150 MB file optimized for Gemini analysis.

### Step 4: Detect Scene Boundaries (on M5 Mac)

1. Install PySceneDetect:
```bash
pip3 install scenedetect[opencv]
```

2. Run detection on the compressed file:
```bash
python3 processing/scripts/detect_scenes.py processing/output/compressed.mp4 processing/output/scenes.json
```

This outputs a JSON file with start/end timestamps for each scene.

---

## Phase 1 Status: COMPLETE (2026-03-26)

All 4 steps done from M5 Mac:
- ✅ Gemini API key added to `/var/www/narralytica/.env` on Hetzner, backend + worker restarted
- ✅ Episode located on Plex (`ssh plex`, chaos drive): `Simpsons 04x17 - Last Exit to Springfield .ogm`
- ✅ Episode copied to M5 Mac: `~/narralytica/input/simpsons_s04e17.ogm` (175.5 MB)
- ✅ Compressed to `~/narralytica/processing/output/compressed.mp4` (80.9 MB, 720p 1fps)
- ✅ Scene detection: `~/narralytica/processing/output/scenes.json` — 9 scenes (17s–892s, avg 154s)
- ✅ Homebrew reinstalled for ARM (was broken Intel version), FFmpeg 8.1, PySceneDetect 0.6.7.1

Note: The 892s longest scene suggests the detection threshold (27.0) may need tuning in Phase 2.

## Phase 2: Ready to Start

Now that scenes are detected and the Gemini key is set:
1. Build the Gemini indexing script (upload compressed video, get structured scene JSON)
2. Generate vector embeddings for each scene description
3. Wire up the bulk ingest endpoint to store everything in Postgres
4. Enable real hybrid search (vector similarity + SQL filters)

---

## Important Rules for This Server
- **NEVER kill processes** without being explicitly asked
- Use `systemctl` for service management
- Prefer Python file-write scripts over heredoc blocks (heredocs break with Jinja2)
- Push to GitHub regularly: `github.com/Erstiv/Narralytica`
- Elliot is a beginner with server management — explain commands clearly
- Port map: backend=8005, frontend=3020, db=5433
