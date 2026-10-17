#!/bin/bash
# Run Praxis Studio as a macOS login service: starts at login, restarts if it crashes.
# Usage: bash tools/studio-service.sh install | uninstall | restart | status | logs
set -euo pipefail
LABEL=com.praxis.studio
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

case "${1:-status}" in
  install)
    if lsof -nP -iTCP:8800 -sTCP:LISTEN >/dev/null 2>&1; then
      echo "Port 8800 is already in use (probably the 'Praxis Studio' terminal tab). Stop it with Ctrl-C, then rerun."
      exit 1
    fi
    mkdir -p "$ROOT/logs" "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/prototype/.venv/bin/python</string>
    <string>-m</string><string>praxis.cli</string><string>studio</string>
    <string>--no-browser</string><string>--port</string><string>8800</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT/prototype</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>$ROOT/logs/studio.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/studio.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
</dict>
</plist>
EOF
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST"
    echo "Installed. Studio will be at http://127.0.0.1:8800 in about 30 s, and after every login."
    ;;
  uninstall)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Removed. Studio no longer starts at login."
    ;;
  restart)
    launchctl kickstart -k "$DOMAIN/$LABEL"
    echo "Restarted (picks up code changes)."
    ;;
  status)
    launchctl print "$DOMAIN/$LABEL" 2>/dev/null | grep -E '^\s*(state|pid) =' || echo "Not installed."
    ;;
  logs)
    tail -n 50 -f "$ROOT/logs/studio.log"
    ;;
  *)
    echo "usage: $0 install | uninstall | restart | status | logs"
    exit 2
    ;;
esac
