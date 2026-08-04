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

# rsync is preferred but not assumed: a stock UNO Q Debian image does not ship
# it. The cp fallback uses coreutils only, so the board needs no extra packages.
if command -v rsync >/dev/null 2>&1; then
  USE_RSYNC=yes
else
  USE_RSYNC=no
fi

# Entries under the App folder that a sync must never touch:
#   .cache/          arduino-app-cli's own build state, not ours to manage
#   python/data/     telemetry recordings, shared with the host-side recorder
#   python/src/      mirrored from the repo separately, below
#   python/config/   likewise
is_protected() {
  case "$1" in
    .cache | python/data | python/src | python/config) return 0 ;;
    *) return 1 ;;
  esac
}

# Replace $2 with an exact copy of $1, deleting whatever else was there.
# Updates in place rather than swapping directories: while the App is running,
# Docker holds a bind mount on the App folder, and replacing a directory inode
# under a live mount leaves the container reading the old one.
mirror_tree() {
  local src="$1" dest="$2"

  if [ "$USE_RSYNC" = yes ]; then
    mkdir -p "$dest"
    rsync -a --delete --exclude '__pycache__/' "$src/" "$dest/"
    return
  fi

  rm -rf "$dest"
  mkdir -p "$(dirname "$dest")"
  cp -a "$src" "$dest"
  find "$dest" -type d -name '__pycache__' -prune -exec rm -rf {} +
}

# Delete anything in $2 that is neither protected nor still present in $1, so a
# file removed in git does not linger on the board as a stale import.
prune_removed() {
  local src="$1" dest="$2" prefix="$3" path name

  [ -d "$dest" ] || return 0

  for path in "$dest"/*; do
    [ -e "$path" ] || continue
    name="$(basename "$path")"
    is_protected "$prefix$name" && continue
    [ -e "$src/$name" ] || rm -rf "$path"
  done
}

mkdir -p "$APP_DIR" "$APP_DIR/python"

# App scaffolding: app.yaml, sketch/*, python/main.py, python/requirements.txt.
# Driven by whatever is in the repo rather than a hardcoded file list, so adding
# a file to the App does not require editing this script.
prune_removed "$SOURCE_APP" "$APP_DIR" ""
prune_removed "$SOURCE_APP/python" "$APP_DIR/python" "python/"

for entry in "$SOURCE_APP"/*; do
  name="$(basename "$entry")"
  [ "$name" = python ] && continue

  if [ -d "$entry" ]; then
    mirror_tree "$entry" "$APP_DIR/$name"
  else
    cp -a "$entry" "$APP_DIR/$name"
  fi
done

for entry in "$SOURCE_APP/python"/*; do
  name="$(basename "$entry")"
  is_protected "python/$name" && continue

  if [ -d "$entry" ]; then
    mirror_tree "$entry" "$APP_DIR/python/$name"
  else
    cp -a "$entry" "$APP_DIR/python/$name"
  fi
done

# PROJECT_ROOT in bridge_client.py resolves to the parent of src/, so placing
# src/ and config/ side by side under python/ makes its existing imports work
# unchanged with PROJECT_ROOT = /app/python.
mirror_tree "$REPO_ROOT/src" "$APP_DIR/python/src"
mirror_tree "$REPO_ROOT/config" "$APP_DIR/python/config"

# Git cannot track an empty directory, so the recording directory shared by the
# containerised LED app and the host-side recorder is created here. Never
# mirrored, so recordings are not deleted by a sync.
mkdir -p "$APP_DIR/python/data/raw"

if [ "$USE_RSYNC" = yes ]; then
  echo "sync_led_app: $REPO_ROOT -> $APP_DIR (rsync)"
else
  echo "sync_led_app: $REPO_ROOT -> $APP_DIR (cp; rsync not installed)"
fi
echo "sync_led_app: recordings directory is $APP_DIR/python/data/raw"
