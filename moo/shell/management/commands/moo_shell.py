# -*- coding: utf-8 -*-
import logging
import asyncio

from django.core.management.base import BaseCommand

from ...server import server

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the moo SSH server.'

    def handle(self, *args, **options):
        log.info("Starting shell server...")
        asyncio.run(server())
