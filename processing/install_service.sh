#!/bin/bash
# Narralytica: Install the processing server as a macOS LaunchAgent
# Run this ON THE PLEX MAC after installing Python packages.
#
# What it does:
#   - Creates a LaunchAgent plist that starts the processing server on login
#   - The server listens on port 8006 for job requests from Hetzner
#   - Logs go to ~/narralytica/processing/logs/
#
# Usage:
#   cd ~/narralytica
#   bash processing/install_service.sh

set -e

PLIST_NAME="com.narralytica.processing"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
WORK_DIR="$HOME/narralytica"
LOG_DIR="$WORK_DIR/processing/logs"
PYTHON="$HOME/narralytica-venv/bin/python3.12"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Find the Gemini API key from environment or prompt
GEMINI_KEY="${GEMINI_API_KEY:-}"
if [ -z "$GEMINI_KEY" ]; then
    echo "WARNING: GEMINI_API_KEY not set. Set it in the plist manually or export it."
fi

# Write the plist
cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>processing.server:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8006</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${WORK_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>GEMINI_API_KEY</key>
        <string>${GEMINI_KEY}</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/server.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/server.err</string>
</dict>
</plist>
PLIST

echo "Created: $PLIST_PATH"

# Load the service
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "Service loaded. Check status:"
echo "  launchctl list | grep narralytica"
echo ""
echo "View logs:"
echo "  tail -f $LOG_DIR/server.log"
echo "  tail -f $LOG_DIR/server.err"
echo ""
echo "Test:"
echo "  curl http://localhost:8006/health"
