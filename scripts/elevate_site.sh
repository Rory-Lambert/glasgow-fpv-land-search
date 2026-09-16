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

# 1. Pull the issue title (site name) and council label slug from the scored CSV.
#    All other details are added by analysis/issue_body.py at step 4.
eval "$(python3 - "$CODE" <<'PY'
import csv, sys, shlex
code = sys.argv[1]
row = next((r for r in csv.DictReader(open("outputs/all_scored_sites.csv"))
            if r["site_code"] == code), None)
if not row:
    sys.exit(f"Site code {code} not found in outputs/all_scored_sites.csv "
             "(run analysis/find_sites.py first, or check the code).")
name = row["site_name"].strip() or row["address"].strip() or code
print(f"NAME={shlex.quote(name)}")
print(f"CSLUG={shlex.quote(row['council'].lower().replace(' ', '-'))}")
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

# Assemble the issue body (details + council contact + member travel + checklist).
python3 analysis/issue_body.py --code "$CODE" --image-url "$RAW" \
  | gh issue create --title "[Site] $NAME" \
      --label "status:shortlisted" --label "council:$CSLUG" \
      --body-file -
