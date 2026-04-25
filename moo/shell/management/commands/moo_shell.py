# -*- coding: utf-8 -*-
import asyncio

from django.core.management.base import BaseCommand

from ...server import server


class Command(BaseCommand):
    help = "Run the moo SSH server."

    def handle(self, *args, **options):
        import logging

        shell_log = logging.getLogger("moo.shell")
        logging.info(
            "Starting shell server... moo.shell effective_level=%s (DEBUG=%s)",
            logging.getLevelName(shell_log.getEffectiveLevel()),
            shell_log.isEnabledFor(logging.DEBUG),
        )
        asyncio.run(server())
