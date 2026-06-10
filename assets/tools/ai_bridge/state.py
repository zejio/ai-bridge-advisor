"""Shared continuity state for Claude Code and Codex bridge runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SharedRecord:
    run_id: str
    command: str
    task: str
    run_dir: str
    writer: str
    critical: bool
    ok: bool
    created_at: str


def shared_dir(repo_root: Path) -> Path:
    return repo_root / ".ai-bridge" / "shared"


def current_path(repo_root: Path) -> Path:
    return shared_dir(repo_root) / "current.md"


def ledger_path(repo_root: Path) -> Path:
    return shared_dir(repo_root) / "ledger.jsonl"


def ensure_shared_state(repo_root: Path) -> None:
    root = shared_dir(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    path = current_path(repo_root)
    if not path.exists():
        path.write_text(
            "# AI Bridge Shared State\n\n"
            "No bridge runs have been recorded yet.\n",
            encoding="utf-8",
        )


def read_shared_context(repo_root: Path, max_chars: int = 12000) -> str:
    ensure_shared_state(repo_root)
    content = current_path(repo_root).read_text(encoding="utf-8")
    if len(content) <= max_chars:
        return content
    return content[-max_chars:]


def append_record(repo_root: Path, record: SharedRecord) -> None:
    ensure_shared_state(repo_root)
    with ledger_path(repo_root).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")


def latest_records(repo_root: Path, limit: int = 5) -> list[SharedRecord]:
    ensure_shared_state(repo_root)
    path = ledger_path(repo_root)
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records: list[SharedRecord] = []
    for line in lines[-limit:]:
        payload = json.loads(line)
        records.append(SharedRecord(**payload))
    return records


def update_current(repo_root: Path, record: SharedRecord, summary: str) -> None:
    ensure_shared_state(repo_root)
    recent = latest_records(repo_root, limit=5)
    notes = latest_notes(repo_root)
    lines = [
        "# AI Bridge Shared State",
        "",
        "This file is the handoff memory for Claude Code and Codex. Read it before starting bridge-aware work.",
        "",
        "## Latest Run",
        "",
        f"- run_id: `{record.run_id}`",
        f"- command: `{record.command}`",
        f"- task: {record.task}",
        f"- writer: `{record.writer}`",
        f"- critical: `{str(record.critical).lower()}`",
        f"- ok: `{str(record.ok).lower()}`",
        f"- run_dir: `{record.run_dir}`",
        f"- created_at: `{record.created_at}`",
        "",
        "## Latest Decision Summary",
        "",
        summary.strip() or "(no summary)",
        "",
        "## Manual Sync Notes",
        "",
        notes or "- none",
        "",
        "## Recent Runs",
        "",
    ]
    if not recent:
        lines.append("- none")
    else:
        for item in reversed(recent):
            lines.append(
                f"- `{item.created_at}` `{item.command}` ok={item.ok} writer=`{item.writer}` task={item.task}"
            )
    current_path(repo_root).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def latest_notes(repo_root: Path, max_chars: int = 3000) -> str:
    path = shared_dir(repo_root) / "notes.md"
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8").strip()
    if len(content) <= max_chars:
        return content
    return content[-max_chars:]


def record_manual_note(repo_root: Path, note: str) -> Path:
    ensure_shared_state(repo_root)
    created_at = datetime.now(timezone.utc).isoformat()
    note_path = shared_dir(repo_root) / "notes.md"
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else "# AI Bridge Notes\n\n"
    note_path.write_text(
        existing.rstrip() + f"\n\n## {created_at}\n\n{note.strip()}\n",
        encoding="utf-8",
    )
    current = current_path(repo_root)
    current_existing = current.read_text(encoding="utf-8") if current.exists() else "# AI Bridge Shared State\n"
    current.write_text(
        current_existing.rstrip()
        + "\n\n## Latest Manual Sync Note\n\n"
        + f"- created_at: `{created_at}`\n"
        + f"- note: {note.strip()}\n",
        encoding="utf-8",
    )
    return note_path
