# lawtech-daily

One law-tech / reg-tech / AI-governance article a day, summarised and delivered
to my phone's home screen.

## Problem

AI governance, RegTech and legal technology are moving faster than any of them
can be passively absorbed. Frameworks (ISO 42001, NIST AI RMF, the EU AI Act,
Singapore's Model AI Governance Framework) and enforcement precedents shift
month to month. Newsletters get archived unread; RSS readers accumulate a
backlog that becomes its own deterrent.

The constraint isn't availability of information. It's **friction and volume**.

## Approach

Reduce the daily commitment to exactly one article, chosen for me, summarised
to two sentences, placed somewhere I already look dozens of times a day.

    RSS feeds ──> relevance scoring ──> LLM summary ──> JSON ──> widget
                       │                                  │
                       └── taxonomy tagging ──> archive ──┘

## Components

| Layer | Tech | Role |
|---|---|---|
| Ingestion | Python stdlib (`urllib`, `ElementTree`) | Fetch + parse RSS 2.0 and Atom |
| Selection | Weighted keyword scoring | Rank by relevance, suppress noise |
| Classification | Keyword taxonomy | Tag against governance frameworks |
| Enrichment | Anthropic API | 2-sentence summary + "why it matters" |
| Scheduling | GitHub Actions (cron) | Daily run, commits results |
| Storage | JSON in repo | `today.json` + append-only `archive.json` |
| Presentation | Scriptable (iOS, JavaScript) | Home-screen widget |

No servers, no database, no hosting cost.

## Design decisions

**Weighted scoring, not keyword matching.** Binary matching returns either
nothing or everything. Weights let "AI governance" + "Singapore" outrank a
passing mention of "compliance". Negative weights (`sponsored: -12`,
`webinar: -9`) suppress the funding announcements and marketing that dominate
legal-tech feeds.

**Headlines weighted 2x.** RSS `<description>` fields are frequently
boilerplate; the headline carries the signal.

**Dedup via `seen.json`.** Without it the same high-scoring story wins for a
week. An 800-entry rolling window guarantees genuinely new material daily.

**Graceful degradation at every layer.** A failed feed is skipped, not fatal.
A failed LLM call falls back to the raw snippet. The widget caches locally and
renders the last good article offline. A widget that shows an error state is a
widget that gets removed from the home screen.

**Taxonomy tagging.** Every article is classified against the frameworks I'm
studying. Over months `archive.json` becomes a dataset: which regulatory
topics actually dominate coverage, and how that shifts.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/lawtech-daily
cd lawtech-daily
python digest.py --dry-run     # fetch + rank, no writes
```

Then:

1. Push to GitHub
2. Settings → Secrets and variables → Actions → add `ANTHROPIC_API_KEY`
   (optional — without it the raw snippet is used)
3. Settings → Actions → General → Workflow permissions → **Read and write**
4. Actions tab → `daily-digest` → **Run workflow** to test immediately
5. Install [Scriptable](https://scriptable.app), paste `widget/LawTechDaily.js`,
   set `GITHUB_USER`, add a medium widget to the home screen

## Tuning

Everything adjustable lives in `config.py`. If junk gets through, add a
negative keyword. If the threshold is too strict, lower `MIN_SCORE`.

## Roadmap

- [ ] SQLite view over `archive.json` for topic-trend queries
- [ ] Save-for-later tap zone writing to iCloud
- [ ] Weekly digest: the week's five highest-scoring articles
- [ ] Track which framework references trend over time
