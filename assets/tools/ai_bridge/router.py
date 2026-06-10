"""Routing policy for the Claude/Codex bridge.

The policy is intentionally conservative: only one agent may write during a
round, and advisors stay read-only unless a future command explicitly grants a
writer lease.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    ADVISOR = "advisor"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    HELPER = "helper"


@dataclass(frozen=True)
class AgentRoute:
    name: str
    provider: str
    model: str
    role: Role
    writable: bool = False


@dataclass(frozen=True)
class RoutePlan:
    command: str
    writer: AgentRoute | None
    advisors: tuple[AgentRoute, ...]
    helpers: tuple[AgentRoute, ...] = ()
    reviewers: tuple[AgentRoute, ...] = ()
    critical: bool = False

    @property
    def all_routes(self) -> tuple[AgentRoute, ...]:
        routes: list[AgentRoute] = []
        if self.writer is not None:
            routes.append(self.writer)
        routes.extend(self.advisors)
        routes.extend(self.helpers)
        routes.extend(self.reviewers)
        return tuple(routes)


SONNET_WRITER = AgentRoute(
    name="claude-sonnet-writer",
    provider="claude",
    model="sonnet",
    role=Role.IMPLEMENTER,
    writable=True,
)
SONNET_HELPER = AgentRoute(
    name="claude-sonnet-helper",
    provider="claude",
    model="sonnet",
    role=Role.HELPER,
)
OPUS_ADVISOR = AgentRoute(
    name="claude-opus-advisor",
    provider="claude",
    model="opus",
    role=Role.ADVISOR,
)
GPT55_ADVISOR = AgentRoute(
    name="codex-gpt55-advisor",
    provider="codex",
    model="gpt-5.5",
    role=Role.ADVISOR,
)
GPT54_MINI_HELPER = AgentRoute(
    name="codex-gpt54-mini-helper",
    provider="codex",
    model="gpt-5.4-mini",
    role=Role.HELPER,
)

CRITICAL_KEYWORDS = {
    "critical",
    "gate",
    "go/no-go",
    "live",
    "paper",
    "trading",
    "risk",
    "deploy",
    "review",
    "merge",
    "commit",
    "production",
}

TRIAGE_KEYWORDS = {
    "triage",
    "scan",
    "summarize",
    "summary",
    "log",
    "logs",
    "test",
    "tests",
    "pytest",
    "read-only",
}


def is_critical_task(task: str, command: str = "") -> bool:
    haystack = f"{command} {task}".lower()
    return any(keyword in haystack for keyword in CRITICAL_KEYWORDS)


def is_triage_task(task: str, command: str = "") -> bool:
    haystack = f"{command} {task}".lower()
    return any(keyword in haystack for keyword in TRIAGE_KEYWORDS)


def route_for(command: str, task: str = "") -> RoutePlan:
    """Return the deterministic v1 route for a bridge command."""

    normalized = command.lower().strip()
    critical = is_critical_task(task, normalized)

    if normalized == "advise":
        return RoutePlan(
            command=normalized,
            writer=None,
            advisors=(OPUS_ADVISOR, GPT55_ADVISOR),
            critical=critical,
        )

    if normalized == "implement":
        return RoutePlan(
            command=normalized,
            writer=SONNET_WRITER,
            advisors=(GPT55_ADVISOR,) if not critical else (OPUS_ADVISOR, GPT55_ADVISOR),
            critical=critical,
        )

    if normalized == "review":
        return RoutePlan(
            command=normalized,
            writer=None,
            advisors=(),
            reviewers=(OPUS_ADVISOR, GPT55_ADVISOR),
            critical=True,
        )

    if normalized == "triage":
        helper = GPT54_MINI_HELPER if is_triage_task(task, normalized) else SONNET_HELPER
        return RoutePlan(
            command=normalized,
            writer=None,
            advisors=(),
            helpers=(helper,),
            critical=False,
        )

    raise ValueError(f"Unknown ai-bridge command: {command}")


def assert_one_writer(plan: RoutePlan) -> None:
    writers = [route for route in plan.all_routes if route.writable]
    if len(writers) > 1:
        names = ", ".join(route.name for route in writers)
        raise ValueError(f"one-writer policy violated: {names}")
