"""Command runners and artifact writing for AI Bridge."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .router import AgentRoute, Role, RoutePlan, assert_one_writer, route_for
from .state import (
    SharedRecord,
    append_record,
    ensure_shared_state,
    read_shared_context,
    record_manual_note,
    update_current,
)


@dataclass(frozen=True)
class AgentResult:
    route: AgentRoute
    ok: bool
    command: tuple[str, ...]
    output: str
    error: str = ""


def utc_run_id(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def make_run_dir(repo_root: Path, run_id: str | None = None) -> Path:
    base = repo_root / ".ai-bridge" / "runs" / (run_id or utc_run_id())
    path = base
    counter = 1
    while path.exists():
        path = base.with_name(f"{base.name}-{counter:02d}")
        counter += 1
    path.mkdir(parents=True, exist_ok=False)
    return path


def collect_repo_context(repo_root: Path) -> str:
    """Collect small, deterministic context without reading large files."""

    commands = [
        ("git status --short", ["git", "status", "--short"]),
        ("git diff --stat", ["git", "diff", "--stat"]),
    ]
    sections: list[str] = []
    for title, command in commands:
        try:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )
            body = completed.stdout.strip() or completed.stderr.strip() or "(no output)"
        except Exception as exc:  # pragma: no cover - defensive only
            body = f"(failed: {exc})"
        sections.append(f"## {title}\n\n```text\n{body[:8000]}\n```")
    sections.append(f"## AI Bridge Shared State\n\n{read_shared_context(repo_root)}")
    return "\n\n".join(sections)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_prompt(command: str, task: str, role: Role, context: str, decision: str = "") -> str:
    role_contract = {
        Role.ADVISOR: (
            "You are an advisor only. Do not edit files or run mutating commands. "
            "Return Markdown with: verdict, risks, recommended_plan, "
            "blocking_questions, tests."
        ),
        Role.REVIEWER: (
            "You are a read-only reviewer. Inspect readiness and risks. "
            "Do not edit files. Return findings first, then tests and verdict."
        ),
        Role.HELPER: (
            "You are a low-cost read-only helper. Summarize logs/tests/context. "
            "Do not edit files. Return concise triage notes and next checks."
        ),
        Role.IMPLEMENTER: (
            "You are the only writer for this round. Use decision.md as source "
            "of truth, keep edits in scope, then report changed files, tests run, "
            "and unresolved risks."
        ),
    }[role]

    parts = [
        "# AI Bridge Task",
        f"Command: {command}",
        "",
        "## Contract",
        role_contract,
        "",
        "## User Task",
        task,
        "",
        "## Repository Context",
        context,
    ]
    if decision:
        parts.extend(["", "## decision.md", decision])
    return "\n".join(parts)


def command_for(route: AgentRoute, prompt: str, repo_root: Path) -> list[str]:
    if route.provider == "claude":
        command = [
            "claude",
            "-p",
            "--model",
            route.model,
            "--output-format",
            "json",
        ]
        if not route.writable:
            command.extend(["--permission-mode", "plan"])
        command.append(prompt)
        return command

    if route.provider == "codex":
        sandbox = "workspace-write" if route.writable else "read-only"
        return [
            "codex",
            "exec",
            "-m",
            route.model,
            "-s",
            sandbox,
            "-a",
            "never",
            "-C",
            str(repo_root),
            prompt,
        ]

    raise ValueError(f"Unsupported provider: {route.provider}")


def run_agent(route: AgentRoute, prompt: str, repo_root: Path, dry_run: bool = False) -> AgentResult:
    command = tuple(command_for(route, prompt, repo_root))
    if dry_run:
        redacted = list(command)
        if redacted:
            redacted[-1] = "<prompt>"
        return AgentResult(
            route=route,
            ok=True,
            command=tuple(redacted),
            output="DRY RUN: command was not executed.",
        )

    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=1800,
            check=False,
        )
    except Exception as exc:
        return AgentResult(
            route=route,
            ok=False,
            command=command[:-1] + ("<prompt>",),
            output="",
            error=f"{type(exc).__name__}: {exc}",
        )
    output = _extract_claude_json(completed.stdout) if route.provider == "claude" else completed.stdout
    return AgentResult(
        route=route,
        ok=completed.returncode == 0,
        command=command[:-1] + ("<prompt>",),
        output=(output or "").strip(),
        error=(completed.stderr or "").strip(),
    )


def _extract_claude_json(stdout: str) -> str:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout
    for key in ("result", "content", "response", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return json.dumps(payload, indent=2, ensure_ascii=False)


def result_filename(route: AgentRoute) -> str:
    if route.name == "claude-opus-advisor":
        return "advisor-opus.md"
    if route.name == "codex-gpt55-advisor":
        return "advisor-gpt55.md"
    if route.role == Role.IMPLEMENTER:
        return "result.md"
    if route.role == Role.HELPER:
        return "triage.md"
    if route.role == Role.REVIEWER:
        return f"review-{route.model.replace('.', '')}.md"
    return f"{route.name}.md"


def write_agent_result(run_dir: Path, result: AgentResult) -> None:
    body = [
        f"# {result.route.name}",
        "",
        f"- provider: `{result.route.provider}`",
        f"- model: `{result.route.model}`",
        f"- role: `{result.route.role.value}`",
        f"- writable: `{str(result.route.writable).lower()}`",
        f"- ok: `{str(result.ok).lower()}`",
        f"- command: `{' '.join(result.command)}`",
        "",
        "## Output",
        "",
        result.output or "(no output)",
    ]
    if result.error:
        body.extend(["", "## Error", "", f"```text\n{result.error}\n```"])
    write_text(run_dir / result_filename(result.route), "\n".join(body).rstrip() + "\n")


def write_decision(run_dir: Path, task: str, plan: RoutePlan, results: Iterable[AgentResult]) -> None:
    results = tuple(results)
    sections = [
        "# AI Bridge Decision Brief",
        "",
        f"- command: `{plan.command}`",
        f"- critical: `{str(plan.critical).lower()}`",
        f"- writer: `{plan.writer.name if plan.writer else 'none'}`",
        f"- one_writer_policy: `enforced`",
        "",
        "## Task",
        "",
        task,
        "",
        "## Participants",
    ]
    for route in plan.all_routes:
        sections.append(
            f"- `{route.name}`: {route.provider}/{route.model}, role={route.role.value}, writable={route.writable}"
        )
    sections.extend(["", "## Advisor And Reviewer Outputs"])
    for result in results:
        sections.extend(
            [
                "",
                f"### {result.route.name}",
                "",
                result.output or "(no output)",
            ]
        )
        if not result.ok:
            sections.extend(
                [
                    "",
                    "Fallback: keep the run in advisory mode and do not proceed to a writer until this failure is reviewed.",
                ]
            )
    write_text(run_dir / "decision.md", "\n".join(sections).rstrip() + "\n")


def summarize_run(run_dir: Path) -> str:
    decision = run_dir / "decision.md"
    if not decision.exists():
        return "(decision.md was not created)"
    content = decision.read_text(encoding="utf-8")
    return content[:4000]


def finish_shared_state(
    repo_root: Path,
    run_dir: Path,
    command: str,
    task: str,
    plan: RoutePlan,
    results: Iterable[AgentResult],
) -> None:
    results = tuple(results)
    record = SharedRecord(
        run_id=run_dir.name,
        command=command,
        task=task,
        run_dir=str(run_dir),
        writer=plan.writer.name if plan.writer else "none",
        critical=plan.critical,
        ok=all(result.ok for result in results),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    append_record(repo_root, record)
    update_current(repo_root, record, summarize_run(run_dir))


def execute_bridge(command: str, task: str, repo_root: Path, dry_run: bool = False) -> Path:
    plan = route_for(command, task)
    assert_one_writer(plan)
    ensure_shared_state(repo_root)
    run_dir = make_run_dir(repo_root)
    context = collect_repo_context(repo_root)
    write_text(run_dir / "task.md", f"# Task\n\n{task}\n\n# Repo Context\n\n{context}\n")

    non_writer_routes = plan.advisors + plan.reviewers + plan.helpers
    all_results: list[AgentResult] = []
    for route in non_writer_routes:
        prompt = build_prompt(plan.command, task, route.role, context)
        result = run_agent(route, prompt, repo_root, dry_run=dry_run)
        all_results.append(result)
        write_agent_result(run_dir, result)

    write_decision(run_dir, task, plan, all_results)

    if plan.writer is not None:
        decision = (run_dir / "decision.md").read_text(encoding="utf-8")
        prompt = build_prompt(plan.command, task, plan.writer.role, context, decision=decision)
        result = run_agent(plan.writer, prompt, repo_root, dry_run=dry_run)
        all_results.append(result)
        write_agent_result(run_dir, result)
    elif not (run_dir / "result.md").exists():
        write_text(
            run_dir / "result.md",
            "# Result\n\nNo writer was assigned for this command. See `decision.md`.\n",
        )

    finish_shared_state(repo_root, run_dir, command, task, plan, all_results)
    return run_dir


def status_text(repo_root: Path, limit: int = 5) -> str:
    ensure_shared_state(repo_root)
    current = read_shared_context(repo_root)
    return current


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-bridge")
    parser.add_argument("--repo-root", default=os.getcwd(), help="Repository root. Defaults to cwd.")
    parser.add_argument("--dry-run", action="store_true", help="Create artifacts without invoking Claude or Codex.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("advise", "implement", "review", "triage"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)
        sub.add_argument("task", nargs="*", help="Task text.")
    status = subparsers.add_parser("status")
    status.add_argument("--limit", type=int, default=5)
    sync = subparsers.add_parser("sync")
    sync.add_argument("note", nargs="*", help="Manual continuity note to add.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    if args.command == "status":
        print(status_text(repo_root, limit=args.limit))
        return 0
    if args.command == "sync":
        note = " ".join(args.note).strip()
        if not note:
            parser.error("note is required")
        path = record_manual_note(repo_root, note)
        print(f"AI Bridge note: {path}")
        return 0

    task = " ".join(args.task).strip()
    if not task and args.command != "review":
        parser.error("task is required")
    if args.command == "review" and not task:
        task = "Review the current repository diff for readiness, risks, and missing tests."

    run_dir = execute_bridge(
        args.command,
        task,
        repo_root,
        dry_run=args.dry_run,
    )
    print(f"AI Bridge run: {run_dir}")
    return 0
