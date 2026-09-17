#!/usr/bin/env bash
# Generate the annotated housing-proximity overlay (approx site extent + 50 m line
# + homes) for every open [Site] issue that doesn't have one yet, push the images,
# and refresh those issues so the overlay appears.
#
# Needs Overpass (OpenStreetMap building geometry). Safe to re-run — it skips
# sites whose overlay already exists.
#
# Usage:  ./scripts/add_proximity.sh
set -euo pipefail
cd "$(dirname "$0")/.."

declare -a REFRESH
while IFS=$'\t' read -r n; do
  [ -z "$n" ] && continue
  code=$(gh issue view "$n" --json body -q .body | grep -oP 'SVDLS code:\*\*\s*\K[A-Za-z0-9]+' | head -1)
  [ -z "$code" ] && { echo "#$n: no SVDLS code in body, skipping"; continue; }
  if ls outputs/proximity/${code}_*.jpg >/dev/null 2>&1; then
    echo "#$n ($code): overlay already exists"
  else
    echo "#$n ($code): generating overlay..."
    if ! python3 analysis/site_proximity.py --code "$code" >/dev/null 2>&1; then
      echo "   Overpass unavailable — skipping $code (re-run later)"; continue
    fi
  fi
  REFRESH+=("$n:$code")
done < <(gh issue list --state open --json number,title -q '.[] | select(.title|startswith("[Site]")) | .number')

# Push any new overlays so their raw URLs resolve before refreshing the bodies.
git add outputs/proximity/*.jpg 2>/dev/null || true
if ! git diff --cached --quiet; then
  git commit -q -m "Add housing-proximity overlays for open leaderboard issues"
  git push -q
  echo "pushed new overlays"
fi

for pair in "${REFRESH[@]}"; do
  ./scripts/refresh_issue.sh "${pair%%:*}" "${pair##*:}"
done
echo "Done — ${#REFRESH[@]} issue(s) have overlays."
