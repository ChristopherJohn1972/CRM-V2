import sqlalchemy as sa
from django.core.management.base import BaseCommand
from common.db import engine


class Command(BaseCommand):
    help = "Fix permissions table: remove duplicates, ensure unique constraints"

    def handle(self, *args, **options):
        with engine.connect() as conn:
            # Remove duplicate permissions (keep lowest permission_id)
            result = conn.execute(sa.text("""
                DELETE FROM permissions
                WHERE permission_id NOT IN (
                    SELECT MIN(permission_id)
                    FROM permissions
                    GROUP BY name
                )
            """))
            self.stdout.write(f"Removed {result.rowcount} duplicate permission rows")

            # Add unique constraint on code if not exists
            conn.execute(sa.text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conrelid = 'permissions'::regclass
                        AND contype = 'u'
                        AND conname = 'permissions_code_key'
                    ) THEN
                        ALTER TABLE permissions ADD CONSTRAINT permissions_code_key UNIQUE (code);
                    END IF;
                END $$;
            """))
            self.stdout.write(self.style.SUCCESS("Permissions constraints fixed"))
            conn.commit()
