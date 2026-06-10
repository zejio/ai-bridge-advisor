"""Install AI Bridge Advisor assets into a target project."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def copy_file(src: Path, dest: Path, overwrite: bool) -> None:
    if dest.exists() and not overwrite:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def copy_tree(src: Path, dest: Path, overwrite: bool) -> None:
    if dest.exists() and overwrite:
        shutil.rmtree(dest)
    if dest.exists():
        return
    shutil.copytree(src, dest)


def ensure_gitignore(project: Path) -> None:
    path = project / ".gitignore"
    marker = ".ai-bridge/"
    if path.exists():
        content = path.read_text(encoding="utf-8")
    else:
        content = ""
    if marker in content:
        return
    suffix = "\n" if content and not content.endswith("\n") else ""
    path.write_text(
        content + suffix + "\n# AI Bridge runtime handoff artifacts\n.ai-bridge/\n",
        encoding="utf-8",
    )


def install(project: Path, overwrite: bool = False) -> None:
    root = skill_root()
    assets = root / "assets"
    project = project.resolve()

    copy_tree(assets / "tools" / "ai_bridge", project / "tools" / "ai_bridge", overwrite)
    copy_file(assets / "tools" / "ai-bridge.py", project / "tools" / "ai-bridge.py", overwrite)
    copy_file(assets / "templates" / "AGENTS.md.template", project / "AGENTS.md", overwrite)
    copy_file(assets / "templates" / "CLAUDE.md.template", project / "CLAUDE.md", overwrite)
    ensure_gitignore(project)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".", help="Target project root.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing bridge files.")
    args = parser.parse_args()

    install(Path(args.project), overwrite=args.overwrite)
    print(f"Installed AI Bridge Advisor into {Path(args.project).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
