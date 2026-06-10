# Shared State Format

AI Bridge runtime state lives under `.ai-bridge/` in each target project.

## Files

- `.ai-bridge/shared/current.md`: latest cross-agent handoff summary.
- `.ai-bridge/shared/ledger.jsonl`: append-only record of bridge runs.
- `.ai-bridge/shared/notes.md`: manual notes added with `sync`.
- `.ai-bridge/runs/<timestamp>/task.md`: task plus repo/shared context.
- `.ai-bridge/runs/<timestamp>/decision.md`: advisor/reviewer decision brief.
- `.ai-bridge/runs/<timestamp>/result.md`: writer or no-writer result.

## Rules

- Do not commit `.ai-bridge/`.
- Do not store secrets.
- Read `current.md` before advisor-aware work.
- Treat `decision.md` as the source of truth for implementation rounds.
