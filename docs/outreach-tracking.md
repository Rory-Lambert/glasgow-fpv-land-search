# Tracking site outreach

We track which sites we've approached, and where each conversation stands, using
**GitHub Issues** — one issue per site. It keeps the whole club's outreach in one
place, gives every site a comment thread for notes and correspondence, and shows
status at a glance on the [Issues tab](../../issues).

## How it works

- **One issue per site** we decide to pursue. Use the *Site outreach* issue template (New issue → Site outreach) so every issue captures the same details: site name, council, size, map link, and SVDLS site code.
- **Labels track status** — each issue carries exactly one `status:` label. Move it along as things progress.
- **The comment thread is the log** — record calls, emails, names, and dates as comments. Attach photos from site visits.
- **Close the issue** when a site is secured (🎉) or ruled out. A closed issue with the `outcome:secured` or `outcome:rejected` label is our record of the decision.

### Status labels

| Label | Meaning |
|---|---|
| `status:shortlisted` | On the list, not yet contacted |
| `status:contacted` | We've made first contact with the council/owner |
| `status:awaiting-reply` | Ball's in their court |
| `status:visit-arranged` | Site visit or meeting booked |
| `status:negotiating` | In active discussion about terms/lease |
| `outcome:secured` | 🎉 We can use it — close the issue |
| `outcome:rejected` | Not available / unsuitable — close the issue |

### Council labels

Each issue also gets a council label (e.g. `council:south-lanarkshire`) so we can
filter by authority — handy when one contact covers several sites.

## Getting started

The original shortlist from [REPORT.md](../REPORT.md) was seeded by
[`scripts/create_issues.sh`](../scripts/create_issues.sh) (run once).

To pursue **another** site, elevate it with one command — this generates its
satellite view and opens the issue for you:

```bash
./scripts/elevate_site.sh <SVDLS_site_code>
```

Find the `site_code` in [`outputs/all_scored_sites.csv`](all_scored_sites.csv).
See [AGENTS.md](../AGENTS.md) for details.

## Why not a spreadsheet?

We could — but issues give us a threaded history per site, @-mentions to pull in
whoever's handling a council, labels and filtering for free, and it lives next to
the analysis rather than in someone's Google Drive. If we outgrow it, a GitHub
**Project board** (Kanban view over these same issues) is a one-click upgrade.
