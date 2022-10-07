import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import autoreload


from celery.bin import celery


class Command(BaseCommand):
    help = "Starts a worker with autoreload enabled."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noreload",
            action="store_false",
            dest="use_reloader",
            help="Tells Django to NOT use the auto-reloader.",
        )

    def handle(self, *args, **options):
        self.run(**options)

    def run(self, **options):
        """Run the server, using the autoreloader if needed."""
        if options["use_reloader"]:
            autoreload.run_with_reloader(self.inner_run, *sys.argv[2:], **options)
        else:
            self.inner_run(None, *sys.argv[2:], **options)

    def inner_run(self, *args, **options):
        sys.argv = [
            'celery',
            '-A',
            getattr(settings, 'CELERY_APPLICATION', ''),
            'worker',
            *args
        ]

        celery.main()