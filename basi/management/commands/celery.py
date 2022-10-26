import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import autoreload


from celery.bin import celery


class Command(BaseCommand):
    help = "Starts a worker with autoreload enabled."

    reload_commands = [
        'worker',
        'multi',
        'beat',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            nargs='?',
            dest="command",
            help="The celery subcommand to run.",
        )
        parser.add_argument(
            "--noreload",
            action="store_false",
            dest="use_reloader",
            help="Tells Django to NOT use the auto-reloader.",
        )

    def handle(self, **options):
        command = options['command']
        args = sys.argv[2:]
        
        options["use_reloader"] = options["use_reloader"] and command in self.reload_commands
        # if options['loglevel'] is None:
        #     args = [*args, '-l', 'DEBUG' if settings.DEBUG else 'INFO']
        self.run(*args, **options)

    def run(self, *args, **options):
        """Run the server, using the autoreloader if needed."""
        if options["use_reloader"]:
            autoreload.run_with_reloader(self.inner_run, *args, **options)
        else:
            self.inner_run(*args, **options)

    def inner_run(self, *args, **options):
        sys.argv = [
            'celery',
            '-A',
            getattr(settings, 'CELERY_APPLICATION', ''),
            *args
        ]
        celery.main()