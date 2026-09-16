#!/usr/bin/env bash
# Elevate one site to a tracked outreach issue, end to end:
#   1. read the site's details from outputs/all_scored_sites.csv
#   2. generate its annotated satellite view
#   3. commit & push the image (so its raw URL resolves)
#   4. create a labelled GitHub issue with the image, details and checklist
#
# Usage:  ./scripts/elevate_site.sh <SVDLS_site_code>
# Find a code in outputs/all_scored_sites.csv (the `site_code` column) or REPORT.md.
#
# Requires: gh (authenticated), python3 with requests + Pillow (pip install -r requirements.txt).
set -euo pipefail

CODE="${1:-}"
if [ -z "$CODE" ]; then
  echo "Usage: ./scripts/elevate_site.sh <SVDLS_site_code>" >&2
  exit 1
fi
cd "$(dirname "$0")/.."

# 1. Pull the site's details from the scored CSV (python does the CSV parsing).
eval "$(python3 - "$CODE" <<'PY'
import csv, sys, shlex
code = sys.argv[1]
row = next((r for r in csv.DictReader(open("outputs/all_scored_sites.csv"))
            if r["site_code"] == code), None)
if not row:
    sys.exit(f"Site code {code} not found in outputs/all_scored_sites.csv "
             "(run analysis/find_sites.py first, or check the code).")
name = row["site_name"].strip() or row["address"].strip() or code
def q(k, v): print(f"{k}={shlex.quote(v)}")
q("NAME", name)
q("COUNCIL", row["council"])
q("CSLUG", row["council"].lower().replace(" ", "-"))
q("SIZE", row["size_ha"]); q("STYPE", row["site_type"])
q("DEV", row["development_potential"]); q("PREV", row["previous_use"])
q("SCORE", row["score"]); q("MAP", row["map_url"]); q("FRZ", row["in_airport_frz"])
PY
)"

# Refuse to create a duplicate if an issue for this code already exists.
if gh issue list --state all --search "$CODE in:body" --json number -q '.[].number' | grep -q .; then
  echo "An issue already mentions code $CODE — not creating a duplicate." >&2
  exit 1
fi

# 2. Generate the satellite image (prints the repo-relative path on its last line).
IMG_REL=$(python3 analysis/fetch_satellite.py --code "$CODE" | tail -n1)
echo "Image: $IMG_REL"

# 3. Commit & push so the raw URL resolves before the issue references it.
git add "$IMG_REL"
git commit -q -m "Add satellite view for site $CODE ($NAME)"
git push -q

# 4. Build the raw image URL from the actual repo + default branch.
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
BRANCH=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
RAW="https://raw.githubusercontent.com/$REPO/$BRANCH/$IMG_REL"

# Make sure the labels exist (idempotent).
gh label create "status:shortlisted" --color ededed --force >/dev/null
gh label create "council:$CSLUG" --color c5def5 --force >/dev/null

FRZ_NOTE=""
[ "$FRZ" = "True" ] && FRZ_NOTE="

**Warning: inside an airport flight-restriction zone — likely unflyable. Confirm before pursuing.**"

BODY="![Satellite view]($RAW)
*Red crosshair = site centroid · 100 m scale bar · imagery © Esri/Maxar.*

---

**Council:** $COUNCIL · **Size:** $SIZE ha · Score $SCORE
**SVDLS code:** $CODE
**Type / potential / former use:** $STYPE · $DEV · $PREV
**Map:** $MAP$FRZ_NOTE

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

gh issue create --title "[Site] $NAME" \
  --label "status:shortlisted" --label "council:$CSLUG" \
  --body "$BODY"
