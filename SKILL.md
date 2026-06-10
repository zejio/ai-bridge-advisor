---
name: ai-bridge-advisor
description: Automatically coordinate Claude Code and Codex advisors with shared handoff memory. Use proactively for complex coding, architecture, code review, deployment, trading-risk, paper/live gates, cross-agent continuity, or whenever work may move between Claude Code and Codex and should preserve advisor decisions.
---

# AI Bridge Advisor

Use this skill to set up or operate a shared advisor bridge between Claude Code and Codex. The bridge keeps Claude Sonnet as the default writer, adds Claude Opus and GPT-5.5 as read-only advisors, uses gpt-5.4-mini for low-cost triage, and writes continuity state into `.ai-bridge/shared/`.

## Auto Advisor Policy

Do not ask whether to use the advisor when a trigger matches. Run the bridge automatically unless the user explicitly says not to.

Run advisor before:
- architecture or multi-file implementation
- code review, merge, commit, or release readiness
- deployment, production, paper trading, live trading, or risk gates
- ambiguous requirements with high blast radius
- any handoff between Claude Code and Codex
- long-running work where continuity matters

Skip advisor for:
- tiny one-file edits
- pure formatting
- simple command output
- tasks where the user explicitly disables the bridge

## Install Into A Project

When the target project does not already have the bridge, run:

```powershell
py -3.10 <skill-dir>\scripts\install_project_bridge.py --project <project-root>
```

If Python 3.10 is unavailable, use any Python 3.10+ interpreter.

The installer copies:
- `tools/ai_bridge/`
- `tools/ai-bridge.py`
- `AGENTS.md` for Codex
- `CLAUDE.md` for Claude Code
- `.gitignore` entry for `.ai-bridge/`

It does not copy secrets and does not commit runtime state.

## Operate The Bridge

Use these commands from the project root:

```powershell
.\b-advisor "<task>"
.\b-advisor review
.\b-advisor triage "<logs or issue>"
.\b-advisor status
.\b-advisor sync "<handoff note>"
```

The default shortcut action is `advise`, so `.\b-advisor "review this architecture"` is equivalent to:

```powershell
py -3.10 tools\ai-bridge.py advise "<task>"
```

Long-form commands remain available:

```powershell
py -3.10 tools\ai-bridge.py implement "<task>"
py -3.10 tools\ai-bridge.py review
py -3.10 tools\ai-bridge.py triage "<logs or issue>"
py -3.10 tools\ai-bridge.py status
py -3.10 tools\ai-bridge.py sync "<handoff note>"
```

For Claude-style prompts, `/b-advisor <task>` should be treated as `.\b-advisor "<task>"`.

For Codex custom prompts, install the optional prompt and invoke `/prompts:b-advisor <task>`. Custom prompts are deprecated in Codex, so prefer the skill's automatic triggering when possible.

Routing defaults:
- `advise`: Opus + GPT-5.5 read-only advisors
- `implement`: Sonnet is the only writer; GPT-5.5 advises
- high-risk `implement`: Sonnet writes; Opus + GPT-5.5 advise
- `review`: Opus + GPT-5.5 read-only reviewers
- `triage`: gpt-5.4-mini read-only helper for logs/tests/summaries

## Shared State

Read `.ai-bridge/shared/current.md` before bridge-aware work. The bridge updates it after every run.

Use `.ai-bridge/runs/<timestamp>/decision.md` as the cross-agent decision brief. If continuing work from another agent, treat that file as the handoff source of truth.

Never store API keys, auth tokens, account credentials, or private secrets in `.ai-bridge/`.

## References

Read `references/claude-codex-routing.md` when adjusting routing policy.
Read `references/shared-state-format.md` when changing `.ai-bridge/shared/` semantics.
