# Narralytica Phase 1 Runbook

Run these steps in order from your **M5 Mac terminal**. Each step tells you where commands run (your Mac, Plex server, or Hetzner).

---

## Step 1: Add Gemini API Key to Hetzner

**Where:** Your Mac terminal (SSHs into Hetzner)

```bash
# Replace YOUR_KEY_HERE with your actual Gemini API key
ssh filou "sed -i 's/^GEMINI_API_KEY=.*/GEMINI_API_KEY=YOUR_KEY_HERE/' /var/www/narralytica/.env"
```

Then restart the backend and worker so they pick up the new key:

```bash
ssh filou "cd /var/www/narralytica && docker compose restart narralytica-backend narralytica-worker"
```

**Verify it worked:**
```bash
ssh filou "grep GEMINI_API_KEY /var/www/narralytica/.env"
```
You should see your key printed back (not blank).

---

## Step 2: Find and Copy the Simpsons Episode from Plex

**Where:** Your Mac terminal (SSHs into Plex server)

First, find the file:
```bash
ssh plex "find /Volumes/chaos -path '*TV*Simpsons*' -name '*S04E17*' -o -path '*TV*Simpsons*' -name '*s04e17*' 2>/dev/null"
```

If that doesn't find it, try a broader search:
```bash
ssh plex "find /Volumes/chaos -iname '*simpsons*last*exit*' -o -iname '*simpsons*s04e17*' 2>/dev/null"
```

Once you see the file path, copy it to your Mac:
```bash
# Replace FULL_PATH_FROM_ABOVE with the actual path you found
mkdir -p ~/narralytica/input
scp plex:"FULL_PATH_FROM_ABOVE" ~/narralytica/input/simpsons_s04e17.mkv
```

---

## Step 3: Compress the Episode

**Where:** Your M5 Mac

First, make sure the repo is cloned and FFmpeg is installed:
```bash
# Clone repo (skip if you already have it)
git clone https://github.com/Erstiv/Narralytica.git ~/narralytica 2>/dev/null || echo "Repo already exists, pulling latest..." && cd ~/narralytica && git pull

# Install FFmpeg (skip if already installed)
brew install ffmpeg
```

Now run the compression:
```bash
cd ~/narralytica
mkdir -p processing/output
python3 processing/scripts/compress.py ~/narralytica/input/simpsons_s04e17.mkv processing/output/compressed.mp4
```

This shrinks the file to 720p at 1 FPS — expect it to go from ~1-4 GB down to ~50-150 MB. Takes a few minutes.

**Verify:** Check the output file exists and is reasonable size:
```bash
ls -lh ~/narralytica/processing/output/compressed.mp4
```

---

## Step 4: Detect Scene Boundaries

**Where:** Your M5 Mac

Install PySceneDetect:
```bash
pip3 install scenedetect[opencv]
```

Run scene detection:
```bash
cd ~/narralytica
python3 processing/scripts/detect_scenes.py processing/output/compressed.mp4 processing/output/scenes.json
```

**Verify:** Check the scenes file:
```bash
cat processing/output/scenes.json | python3 -m json.tool | head -30
```
You should see a JSON array with start/end timestamps for each detected scene.

---

## Done!

Once all 4 steps complete, you're ready for **Phase 2** — hand back to Claude Code and it can:
1. Build the Gemini indexing script
2. Generate vector embeddings
3. Wire up bulk ingest
4. Enable hybrid search

---

## Troubleshooting

**"Permission denied" on SSH:** Make sure your SSH keys are set up for `filou` and `plex` aliases (check `~/.ssh/config`).

**FFmpeg not found:** Run `brew install ffmpeg` — if Homebrew isn't installed, run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Python module not found:** Try `pip3 install --user scenedetect[opencv]` or use `python3 -m pip install`.

**Repo clone fails:** Check your GitHub auth — you may need `gh auth login` first.
