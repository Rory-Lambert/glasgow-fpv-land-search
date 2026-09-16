#!/usr/bin/env bash
# Rebuild one site issue's body from current data (site details, council contact,
# member travel, checklist), preserving its existing satellite image. Re-run this
# after editing data/members.md to refresh the travel numbers on an issue.
#
# Usage:  ./scripts/refresh_issue.sh <issue_number> <SVDLS_site_code>
set -euo pipefail
ISSUE="${1:?Usage: refresh_issue.sh <issue_number> <site_code>}"
CODE="${2:?Usage: refresh_issue.sh <issue_number> <site_code>}"
cd "$(dirname "$0")/.."

BODY=$(gh issue view "$ISSUE" --json body -q .body)
IMG=$(grep -oP '!\[Satellite view\]\(\K[^)]+' <<<"$BODY" | head -1 || true)

python3 analysis/issue_body.py --code "$CODE" ${IMG:+--image-url "$IMG"} \
  | gh issue edit "$ISSUE" --body-file - >/dev/null
echo "refreshed #$ISSUE ($CODE)"
