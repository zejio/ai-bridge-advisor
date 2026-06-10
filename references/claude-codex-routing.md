# Claude/Codex Routing

Use this reference when changing bridge behavior.

## Roles

- Claude Sonnet: default implementation writer.
- Claude Opus: read-only advisor/reviewer for critical reasoning and risk.
- GPT-5.5: read-only co-advisor for architecture, coding, and risk review.
- gpt-5.4-mini: read-only helper for scan, logs, tests, and summaries.

## One Writer Rule

Only one agent may write files in a bridge run. In v1 this is Sonnet by default.

Do not let Opus, GPT-5.5, or gpt-5.4-mini edit files unless a future explicit writer lease mechanism is added.

## Critical Triggers

Treat these as critical:
- paper/live trading gates
- deployment or production risk
- code review before merge/commit
- large refactors
- unclear architecture decisions
- high-blast-radius financial logic
