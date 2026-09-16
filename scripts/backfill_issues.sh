#!/usr/bin/env bash
# One-time: rebuild the 7 originally-seeded issues so they gain the council
# contact and member-travel sections. Maps each issue to its SVDLS site_code.
# Safe to re-run (it just refreshes each body from current data).
#
# Usage:  ./scripts/backfill_issues.sh
set -euo pipefail
cd "$(dirname "$0")/.."

CODES="8445387 NL008491903 NL008491906 2829 1560 8410235 6153"

echo "Generating housing-proximity images..."
for c in $CODES; do python3 analysis/site_proximity.py --code "$c" >/dev/null; done
git add outputs/proximity
git commit -q -m "Add/refresh housing-proximity images for shortlist" || echo "(images unchanged)"
git push -q

./scripts/refresh_issue.sh 1 8445387       # Former Blaes Pitch, Cambuslang
./scripts/refresh_issue.sh 2 NL008491903   # Former Recreation Ground, Glenmavis
./scripts/refresh_issue.sh 3 NL008491906   # Wheatholme Park North, Airdrie
./scripts/refresh_issue.sh 4 2829          # East of Lochgoin Avenue, Nitshill
./scripts/refresh_issue.sh 5 1560          # Rear of Gardenside Crescent
./scripts/refresh_issue.sh 6 8410235       # Northern Site, Alexandria
./scripts/refresh_issue.sh 7 6153          # Stoner Crescent, Auchinleck
echo "Backfill complete."
