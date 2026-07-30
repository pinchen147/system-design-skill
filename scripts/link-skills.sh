#!/usr/bin/env bash
# Symlink every skill in this repo into the local agent skill directories.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
for dest in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  mkdir -p "$dest"
  for skill in "$repo"/skills/*/; do
    name="$(basename "$skill")"
    ln -sfn "$skill" "$dest/$name"
    echo "linked $dest/$name"
  done
done
