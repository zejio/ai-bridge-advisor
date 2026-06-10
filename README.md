# AI Bridge Advisor

AI Bridge Advisor is a reusable Codex skill and project bridge for coordinating Claude Code and Codex in the same codebase. It keeps one agent as the writer, uses stronger models as advisors, and records shared handoff state so work can continue cleanly from either side.

The default workflow is:

- Claude Sonnet writes implementation changes.
- Claude Opus acts as a read-only advisor/reviewer.
- GPT-5.5 acts as a read-only co-advisor.
- gpt-5.4-mini handles low-cost read-only triage, scans, logs, and summaries.
- `.ai-bridge/shared/current.md` stores the latest cross-agent handoff.

## What It Does

AI Bridge Advisor helps with:

- running an advisor pass before complex implementation
- asking both Opus and GPT-5.5 for architecture, risk, and review input
- keeping Sonnet as the only default writer to avoid multi-agent file conflicts
- sharing continuity between Claude Code and Codex through `.ai-bridge/`
- recording decision briefs for later continuation
- installing the same bridge conventions into other projects

It is useful when you work across Claude Code and Codex and want the same "advisor" behavior no matter which chat or tool you start from.

## Repository Contents

```text
ai-bridge-advisor/
  SKILL.md
  agents/
    openai.yaml
  scripts/
    install_project_bridge.py
  references/
    claude-codex-routing.md
    shared-state-format.md
  assets/
    templates/
      AGENTS.md.template
      CLAUDE.md.template
    tools/
      ai-bridge.py
      ai_bridge/
```

## Install As A Codex Skill

Clone the repository:

```powershell
git clone https://github.com/zejio/ai-bridge-advisor.git
```

Install into Codex skills:

```powershell
Copy-Item .\ai-bridge-advisor C:\Users\dream\.codex\skills\ai-bridge-advisor -Recurse
```

Restart Codex so the skill is discovered.

For another Windows user, replace `C:\Users\dream` with that user's home directory.

## Install Into A Project

After installing or cloning this skill, run the project installer:

```powershell
py -3.10 .\ai-bridge-advisor\scripts\install_project_bridge.py --project E:\YourProject
```

From inside the skill folder:

```powershell
py -3.10 scripts\install_project_bridge.py --project E:\YourProject
```

The installer copies these files into the target project:

- `tools/ai_bridge/`
- `tools/ai-bridge.py`
- `AGENTS.md`
- `CLAUDE.md`
- `.gitignore` entry for `.ai-bridge/`

It does not copy credentials or API keys.

## Basic Usage

Run commands from the target project root.

Ask both advisors for a decision brief:

```powershell
py -3.10 tools\ai-bridge.py advise "review this architecture before implementation"
```

Run an implementation round:

```powershell
py -3.10 tools\ai-bridge.py implement "add the new feature"
```

Run a review round:

```powershell
py -3.10 tools\ai-bridge.py review
```

Triage logs or test failures:

```powershell
py -3.10 tools\ai-bridge.py triage "summarize these pytest failures"
```

Check shared continuity state:

```powershell
py -3.10 tools\ai-bridge.py status
```

Add a manual handoff note:

```powershell
py -3.10 tools\ai-bridge.py sync "Continue from the P9 gate decision. Do not skip risk review."
```

Dry-run without calling Claude or Codex:

```powershell
py -3.10 tools\ai-bridge.py --dry-run advise "smoke test bridge setup"
```

## Routing Rules

| Command | Default behavior |
| --- | --- |
| `advise` | Claude Opus + GPT-5.5 give read-only advice |
| `implement` | Claude Sonnet writes; GPT-5.5 advises |
| high-risk `implement` | Claude Sonnet writes; Claude Opus + GPT-5.5 advise |
| `review` | Claude Opus + GPT-5.5 review in read-only mode |
| `triage` | gpt-5.4-mini handles read-only scan/log/test triage |

High-risk triggers include:

- live trading
- paper trading gates
- deployment
- production changes
- code review before merge or commit
- financial risk logic
- architecture decisions

## Shared State

AI Bridge writes runtime handoff state under:

```text
.ai-bridge/
  shared/
    current.md
    ledger.jsonl
    notes.md
  runs/
    <timestamp>/
      task.md
      advisor-opus.md
      advisor-gpt55.md
      decision.md
      result.md
```

Important files:

- `.ai-bridge/shared/current.md`: latest cross-agent continuity state
- `.ai-bridge/runs/<timestamp>/decision.md`: advisor/reviewer decision brief
- `.ai-bridge/runs/<timestamp>/result.md`: writer result or no-writer result

Do not commit `.ai-bridge/`. It is runtime state and may contain project-specific context.

## Auto-Advisor Behavior

The installer adds `AGENTS.md` and `CLAUDE.md` to the target project. These files tell Codex and Claude Code to use AI Bridge automatically for complex, risky, or cross-agent work.

The bridge should be used automatically for:

- multi-file implementation
- architecture decisions
- code review
- deployment or release readiness
- paper/live trading gates
- risk-sensitive financial logic
- handoff between Claude Code and Codex

It should be skipped for:

- tiny one-file edits
- formatting-only changes
- simple command output
- tasks where the user explicitly disables the bridge

Note: a skill is not a background daemon. Existing Claude Code or Codex sessions may need to reload project instructions or be restarted before they consistently follow the new `AGENTS.md` and `CLAUDE.md` rules.

## Safety Model

AI Bridge uses a one-writer rule:

- Sonnet is the default writer.
- Opus, GPT-5.5, and gpt-5.4-mini are read-only by default.
- Runtime state is stored locally under `.ai-bridge/`.
- Secrets must not be stored in `.ai-bridge/`.

This avoids two agents editing the same files at the same time.

## Validate The Skill

From a machine with Codex's skill creator tools installed:

```powershell
py -3.10 C:\Users\dream\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\ai-bridge-advisor
```

Smoke-test project installation:

```powershell
$tmp = Join-Path $env:TEMP "ai-bridge-smoke"
New-Item -ItemType Directory -Force -Path $tmp
py -3.10 .\ai-bridge-advisor\scripts\install_project_bridge.py --project $tmp
py -3.10 "$tmp\tools\ai-bridge.py" --repo-root $tmp --dry-run advise "portable install smoke test"
```

## Future Plugin Path

This repository is currently a skill. To publish it as a Codex plugin later, wrap it in a plugin repository with:

```text
.codex-plugin/
  plugin.json
skills/
  ai-bridge-advisor/
```

Keep this skill repository as the portable source of truth, then create a separate plugin repository that bundles it.
