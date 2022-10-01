import sys

from django.conf import settings
from django.core.management.base import BaseCommand


from celery.bin import celery


class Command(BaseCommand):
    help = "Purge tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', "--force",
            action="store_true",
            dest="force",
            help="Skip the confirmation prompt.",
        )

    def handle(self, *args, **options):
        self.run(**options)

    def run(self, **options):
        """Run the server, using the autoreloader if needed."""
        sys.argv[:2] = [
            'celery',
            '-A',
            getattr(settings, 'CELERY_APPLICATION', ''),
            'purge',

        ]
        celery.main()

