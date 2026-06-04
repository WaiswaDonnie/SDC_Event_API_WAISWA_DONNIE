"""
Unit tests for the state machine module.

These tests have no DB or HTTP dependencies — the state machine is pure logic.
"""
import pytest

from app.models import Status
from app.state_machine import (
    ALLOWED_TRANSITIONS,
    InvalidStateTransition,
    transition,
)


class TestValidTransitions:
    """Every transition explicitly allowed in ALLOWED_TRANSITIONS must succeed."""

    def test_scheduled_to_live(self) -> None:
        assert transition(Status.SCHEDULED, Status.LIVE) == Status.LIVE

    def test_scheduled_to_cancelled(self) -> None:
        assert transition(Status.SCHEDULED, Status.CANCELLED) == Status.CANCELLED

    def test_live_to_completed(self) -> None:
        assert transition(Status.LIVE, Status.COMPLETED) == Status.COMPLETED

    def test_live_to_cancelled(self) -> None:
        assert transition(Status.LIVE, Status.CANCELLED) == Status.CANCELLED


class TestInvalidTransitions:
    """Disallowed transitions must raise InvalidStateTransition."""

    def test_scheduled_cannot_skip_to_completed(self) -> None:
        with pytest.raises(InvalidStateTransition):
            transition(Status.SCHEDULED, Status.COMPLETED)

    def test_completed_is_terminal(self) -> None:
        with pytest.raises(InvalidStateTransition):
            transition(Status.COMPLETED, Status.LIVE)

    def test_cancelled_is_terminal(self) -> None:
        with pytest.raises(InvalidStateTransition):
            transition(Status.CANCELLED, Status.SCHEDULED)

    def test_transition_to_self_rejected(self) -> None:
        with pytest.raises(InvalidStateTransition):
            transition(Status.SCHEDULED, Status.SCHEDULED)


class TestExceptionMessages:
    """The exception message should be useful and structured."""

    def test_terminal_state_message(self) -> None:
        with pytest.raises(InvalidStateTransition) as exc_info:
            transition(Status.COMPLETED, Status.LIVE)
        assert "terminal" in str(exc_info.value).lower()

    def test_invalid_transition_message_lists_allowed_targets(self) -> None:
        with pytest.raises(InvalidStateTransition) as exc_info:
            transition(Status.SCHEDULED, Status.COMPLETED)
        msg = str(exc_info.value)
        assert "cancelled" in msg
        assert "live" in msg

    def test_exception_carries_current_and_target(self) -> None:
        with pytest.raises(InvalidStateTransition) as exc_info:
            transition(Status.COMPLETED, Status.LIVE)
        assert exc_info.value.current == Status.COMPLETED
        assert exc_info.value.target == Status.LIVE


class TestAllowedTransitionsTable:
    """Guard against accidental mutation of the source-of-truth dict."""

    def test_terminal_states_have_no_outgoing_transitions(self) -> None:
        assert ALLOWED_TRANSITIONS[Status.COMPLETED] == set()
        assert ALLOWED_TRANSITIONS[Status.CANCELLED] == set()

    def test_every_status_has_an_entry(self) -> None:
        # Catches the case where someone adds a Status value but forgets to
        # update ALLOWED_TRANSITIONS.
        for status_value in Status:
            assert status_value in ALLOWED_TRANSITIONS