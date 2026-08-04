#!/usr/bin/env bash
#
# Mirror this checkout into the Arduino App folder that arduino-app-cli runs.
#
# arduino-app-cli bind-mounts only the App folder to /app inside the container,
# so src/ and config/ must exist as real files under the App folder's python/
# directory. Symlinks pointing back at the repo resolve to paths that do not
# exist in the container's namespace: they look valid over SSH and dangle at
# runtime, so real copies are used instead.
#
# Invoked automatically by the board's .git/hooks/post-merge, and safe to run
# by hand at any time. Idempotent.
#
# Usage: scripts/sync_led_app.sh [app-folder]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${1:-${PITWALL_APP_DIR:-$HOME/ArduinoApps/pitwall-led}}"

SOURCE_APP="$REPO_ROOT/mcu/pitwall_led_app"

if [ ! -f "$SOURCE_APP/app.yaml" ]; then
  echo "sync_led_app: no app.yaml under $SOURCE_APP" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "sync_led_app: rsync is required but not installed" >&2
  exit 1
fi

mkdir -p "$APP_DIR"

# App scaffolding (app.yaml, python/main.py, sketch/*). --delete removes files
# deleted in git, which a plain copy would leave behind as stale imports.
#
# Protected from --delete:
#   .cache/     arduino-app-cli's own build state, not ours to manage
#   python/src, python/config, python/data
#               synced separately below, or owned by the recorder
rsync -a --delete \
  --exclude '.cache/' \
  --exclude '__pycache__/' \
  --exclude 'python/src/' \
  --exclude 'python/config/' \
  --exclude 'python/data/' \
  "$SOURCE_APP/" "$APP_DIR/"

# PROJECT_ROOT in bridge_client.py resolves to the parent of src/, so placing
# src/ and config/ side by side under python/ makes its existing imports work
# unchanged with PROJECT_ROOT = /app/python.
rsync -a --delete --exclude '__pycache__/' "$REPO_ROOT/src/" "$APP_DIR/python/src/"
rsync -a --delete --exclude '__pycache__/' "$REPO_ROOT/config/" "$APP_DIR/python/config/"

# Git cannot track an empty directory, so the recording directory shared by the
# containerised LED app and the host-side recorder is created here. Never
# rsynced, so recordings are not deleted by a sync.
mkdir -p "$APP_DIR/python/data/raw"

echo "sync_led_app: $REPO_ROOT -> $APP_DIR"
echo "sync_led_app: recordings directory is $APP_DIR/python/data/raw"
