from app.models import Status

ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.SCHEDULED: {Status.LIVE, Status.CANCELLED},
    Status.LIVE: {Status.COMPLETED, Status.CANCELLED},
    Status.COMPLETED: set(),
    Status.CANCELLED: set(),
}

class InvalidStateTransition(Exception):
    def __init__(self, current:Status,target:Status) -> None:
        self.current = current
        self.target = target
        allowed = sorted(s.value for s in ALLOWED_TRANSITIONS[current]) # Get allowed transitions as sorted list of strings

        if not allowed:
            message = (
            f"Cannot transition from '{current.value}': "
            "it is a terminal state."
            )
        else:
            message = (
                f"Cannot transition from {current.value} to {target.value}. "
                f"Allowed transitions: {', '.join(allowed)}."
            )

        super().__init__(message) # Call the base Exception constructor with the message

def transition(current: Status, target: Status) -> Status:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(current, target)
    return target