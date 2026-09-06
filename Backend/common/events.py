import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    customer_id: int
    source_module: str
    actor_user_id: Optional[int]
    actor_type: str
    summary: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    payload: dict = field(default_factory=dict)
    correlation_id: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


Handler = Callable[[DomainEvent], None]


class EventBus:
    _handlers: List[Handler] = []

    @classmethod
    def register(cls, handler: Handler) -> None:
        if handler not in cls._handlers:
            cls._handlers.append(handler)

    @classmethod
    def publish(cls, event: DomainEvent) -> None:
        for handler in cls._handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("event handler failed for %s", event.event_type)


def clear_handlers() -> None:
    EventBus._handlers = []
