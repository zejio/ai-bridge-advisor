"""Convenience script for running the AI Bridge CLI from the repo root."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.ai_bridge.runner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
