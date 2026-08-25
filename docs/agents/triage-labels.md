# Triage labels

Canonical `Status:` line format and values for issue files under
`.scratch/*/issues/`. Based on values already in use across this repo's
issue history.

## Format

Use plain `Status: <value>`, not bold `**Status:** <value>`. Both forms
currently exist in this repo (tickets 01-06 use plain, 07-18 use bold) —
standardize on plain going forward.

## Values

| Status | Meaning | Used by |
|---|---|---|
| *(no `Status:` line)* | Open, unclaimed, no work started | any ticket type |
| `claimed` | An agent has picked this up and is working it | wayfinder tickets |
| `blocked` | Waiting on the tickets listed in `Blocked by:` | wayfinder tickets |
| `resolved` | Answered/decided; answer appended under `## Answer`, decision pointer added to `map.md` | research/grilling/task wayfinder tickets |
| `ready-for-agent` | Triaged and scoped, waiting for an agent to implement | implementation tickets |
| `complete` | Implementation finished and merged/committed | implementation tickets |
| `closed` | Abandoned or superseded without being implemented | any ticket type |

## Notes

- `resolved` (a question was answered) and `complete` (code was written and
  landed) are not interchangeable — use the one matching the ticket type.
- `done`/`finished` are NOT valid — use `complete`.
