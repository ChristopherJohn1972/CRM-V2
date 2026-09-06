import logging
from django.core.management.base import BaseCommand

from common.db import SessionLocal
from event_engine.services import EventProcessingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process pending events from the outbox"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of events to process per batch",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        self.stdout.write(f"Processing outbox events (batch_size={batch_size})...")

        session = SessionLocal()
        try:
            processed = EventProcessingService.process_pending(session, batch_size=batch_size)
            session.commit()
            self.stdout.write(self.style.SUCCESS(f"Processed {processed} events."))
        except Exception as exc:
            session.rollback()
            logger.exception("Failed to process outbox events")
            self.stderr.write(self.style.ERROR(f"Error: {exc}"))
        finally:
            session.close()
