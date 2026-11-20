# Online Presence Audit — Lichuan (Leo / Homer) Hong

Version-controlled snapshots of what search engines and AI tools can find about me.
Each snapshot re-runs the same query set (Q01–Q11) so results are comparable over time.

## Contents
- `PROFILE.md` — consolidated public record (v1.0)
- `snapshots/` — machine-readable query results per version
- `sources/` — external reports used as inputs (e.g. multi-AI test, 2026-11-20)

## Workflow
1. Make a fix (e.g. robots.txt, ORCID, LinkedIn).
2. Log it in `CHANGELOG.md`.
3. Wait for indexing (1–2 weeks), re-run Q01–Q11, save `snapshots/YYYY-MM-DD_vX.Y.json`.
4. Commit and tag: `git tag vX.Y`. Compare: `git diff v1.0 vX.Y -- snapshots/`.

## KPIs tracked
| KPI | v1.0 (2026-11-20) | Target |
|---|---|---|
| leohong.ca indexed | No | Yes |
| Queries with a hit about me | 3/13 | ≥10/13 |
| Post-2020 career visible off-site | No | Yes |
| PubMed papers attributed | 11 | 11 (+ ORCID-linked) |
| ORCID / public LinkedIn / GitHub | None | All three |

## Versioning
- Major (2.0): a new query set or method change.
- Minor (1.1): a re-run of the same query set after a fix.
