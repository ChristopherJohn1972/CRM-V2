from django.core.management.base import BaseCommand

from common.db import Base, engine


class Command(BaseCommand):
    help = "Create all tables from SQLAlchemy models"

    def handle(self, *args, **options):
        self.stdout.write("Creating tables from SQLAlchemy models...")
        Base.metadata.create_all(engine)
        self.stdout.write(self.style.SUCCESS("All tables created successfully."))
