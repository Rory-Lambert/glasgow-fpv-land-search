#!/usr/bin/env bash
# Seed the outreach tracker: creates status/council labels and one issue per
# shortlisted site. Idempotent-ish — labels are created with --force; re-running
# will create duplicate issues, so run it once.
#
# Requires: gh CLI, authenticated, run from inside the repo.
#   ./scripts/create_issues.sh
set -euo pipefail

echo "Creating labels..."
label() { gh label create "$1" --color "$2" --description "$3" --force >/dev/null; }

label "status:shortlisted"   "ededed" "On the list, not yet contacted"
label "status:contacted"     "1d76db" "First contact made"
label "status:awaiting-reply" "fbca04" "Waiting on the council/owner"
label "status:visit-arranged" "0e8a16" "Site visit or meeting booked"
label "status:negotiating"    "5319e7" "In active discussion about terms"
label "outcome:secured"       "0e8a16" "We can use it"
label "outcome:rejected"      "b60205" "Not available / unsuitable"
label "council:south-lanarkshire" "c5def5" ""
label "council:north-lanarkshire" "c5def5" ""
label "council:glasgow-city"      "c5def5" ""
label "council:west-dunbartonshire" "c5def5" ""
label "council:east-ayrshire"     "c5def5" ""

echo "Creating issues..."
# create_issue <title> <council-label> <body>
create_issue() {
  gh issue create --title "$1" --label "status:shortlisted" --label "$2" --body "$3" >/dev/null
  echo "  + $1"
}

create_issue "[Site] Former Blaes Pitch, Westburn Road, Cambuslang" "council:south-lanarkshire" \
"**Council:** South Lanarkshire · **Size:** 1.25 ha · **Tier 1 (top pick)** · Score +11
**SVDLS code:** 8445387
**Map:** https://www.google.com/maps/search/?api=1&query=55.820998,-4.151503

Former ash football pitch — right shape and size, open recreational land with no firm development plan, 7.7 km from the city centre and clear of both airport zones.

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

create_issue "[Site] Former Recreation Ground, MacArthur Avenue, Glenmavis" "council:north-lanarkshire" \
"**Council:** North Lanarkshire · **Size:** 1.63 ha · **Tier 1** · Score +11
**SVDLS code:** NL008491903
**Map:** https://www.google.com/maps/search/?api=1&query=55.883586,-4.002923

Open former recreation ground on the semi-rural edge of Glenmavis. Note: 7.3 km from Cumbernauld Airport — outside the FRZ but check airspace carefully.

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

create_issue "[Site] Wheatholme Park North, Rawyards, Airdrie" "council:north-lanarkshire" \
"**Council:** North Lanarkshire · **Size:** 0.73 ha · **Tier 1** · Score +11
**SVDLS code:** NL008491906
**Map:** https://www.google.com/maps/search/?api=1&query=55.874173,-3.970852

Bang-on football-pitch size, former recreation ground. Limited room to expand.

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

create_issue "[Site] East of Lochgoin Avenue, Darnley/Nitshill" "council:glasgow-city" \
"**Council:** Glasgow City · **Size:** 1.07 ha · **Tier 2** · Score +11
**Map:** https://www.google.com/maps/search/?api=1&query=55.917933,-4.372224

Former passive open space on the SW edge of the city, within Glasgow itself.

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

create_issue "[Site] Rear of 42-78 Gardenside Crescent, Cambuslang area" "council:glasgow-city" \
"**Council:** Glasgow City · **Size:** 0.78 ha · **Tier 2** · Score +10
**Map:** https://www.google.com/maps/search/?api=1&query=55.827945,-4.161786

Former agricultural land, open, close to the Cambuslang blaes pitch (combine site visits).

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

create_issue "[Site] Northern Site, Lomond Ind. Estate, Alexandria" "council:west-dunbartonshire" \
"**Council:** West Dunbartonshire · **Size:** 1.98 ha · **Tier 2** · Score +10
**SVDLS code:** 8410235
**Map:** https://www.google.com/maps/search/?api=1&query=55.996137,-4.574884

Largest strong candidate — former agricultural land with room for a bigger course. 25 km from the centre.

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

create_issue "[Site] Former Residential Development, Stoner Crescent, Auchinleck" "council:east-ayrshire" \
"**Council:** East Ayrshire (home council) · **Size:** 1.56 ha · Score +9
**Map:** https://www.google.com/maps/search/?api=1&query=55.474799,-4.292637

Best pitch-sized council-owned option in our home council. Cleared housing site rather than open recreation land — site visit matters more here.

- [ ] Satellite view checked
- [ ] Airspace checked in a drone app
- [ ] First contact made
- [ ] Site visit"

echo "Done. See the Issues tab."
