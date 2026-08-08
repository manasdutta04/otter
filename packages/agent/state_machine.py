"""Formal engineer state machine — orchestration owns transitions, not the LLM."""

from __future__ import annotations

from packages.agent.types import EngineerState


# Allowed transitions for the engineer loop.
ALLOWED: dict[EngineerState, set[EngineerState]] = {
    EngineerState.IDLE: {EngineerState.UNDERSTAND, EngineerState.CANCELLED},
    EngineerState.UNDERSTAND: {EngineerState.INVESTIGATE, EngineerState.CANCELLED},
    EngineerState.INVESTIGATE: {EngineerState.PLAN, EngineerState.CANCELLED},
    EngineerState.PLAN: {EngineerState.DECOMPOSE, EngineerState.AWAIT_APPROVAL, EngineerState.CANCELLED},
    EngineerState.DECOMPOSE: {EngineerState.AWAIT_APPROVAL, EngineerState.CANCELLED},
    EngineerState.AWAIT_APPROVAL: {
        EngineerState.IMPLEMENT,
        EngineerState.CANCELLED,
        EngineerState.PLAN,
    },
    EngineerState.IMPLEMENT: {EngineerState.VALIDATE, EngineerState.FAILED, EngineerState.CANCELLED},
    EngineerState.VALIDATE: {
        EngineerState.REVIEW,
        EngineerState.DEBUG,
        EngineerState.FAILED,
    },
    EngineerState.DEBUG: {EngineerState.INVESTIGATE, EngineerState.IMPLEMENT, EngineerState.FAILED},
    EngineerState.REVIEW: {EngineerState.FINAL_APPROVAL, EngineerState.IMPLEMENT, EngineerState.FAILED},
    EngineerState.FINAL_APPROVAL: {EngineerState.APPLY, EngineerState.CANCELLED, EngineerState.IMPLEMENT},
    EngineerState.APPLY: {EngineerState.DONE, EngineerState.FAILED},
    EngineerState.FAILED: {EngineerState.DEBUG, EngineerState.CANCELLED, EngineerState.IDLE},
    EngineerState.CANCELLED: {EngineerState.IDLE},
    EngineerState.DONE: {EngineerState.IDLE},
}


WRITE_STATES = frozenset(
    {
        EngineerState.IMPLEMENT,
        EngineerState.APPLY,
    }
)

REQUIRES_HUMAN_BEFORE = frozenset(
    {
        EngineerState.IMPLEMENT,  # needs plan approval
        EngineerState.APPLY,  # needs final approval (patch_ready → approved)
    }
)


class IllegalTransition(ValueError):
    pass


def can_transition(current: EngineerState, nxt: EngineerState) -> bool:
    return nxt in ALLOWED.get(current, set())


def transition(current: EngineerState, nxt: EngineerState) -> EngineerState:
    if not can_transition(current, nxt):
        raise IllegalTransition(f"Cannot transition {current.value} → {nxt.value}")
    return nxt


def assert_can_implement(current: EngineerState) -> None:
    """Implement only after await_approval (human plan approval)."""
    if current != EngineerState.AWAIT_APPROVAL:
        raise IllegalTransition(
            f"Cannot implement from {current.value}; human plan approval required "
            f"(expected await_approval)"
        )


def assert_can_apply(code_task_status: str) -> None:
    """Apply only when CodeChangeTask is approved (existing API gate)."""
    if code_task_status != "approved":
        raise IllegalTransition(
            f"Cannot apply patch when code task status is {code_task_status!r}; "
            "expected 'approved'"
        )


def assert_can_generate(code_task_status: str) -> None:
    if code_task_status != "ready_for_approval":
        raise IllegalTransition(
            f"Cannot generate patch when status is {code_task_status!r}; "
            "expected 'ready_for_approval'"
        )


__all__ = [
    "ALLOWED",
    "IllegalTransition",
    "REQUIRES_HUMAN_BEFORE",
    "WRITE_STATES",
    "assert_can_apply",
    "assert_can_generate",
    "assert_can_implement",
    "can_transition",
    "transition",
]
