# -*- coding: utf-8 -*-
import logging
import asyncio

from django.core.management.base import BaseCommand

from ...interface.server import server

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the termiverse SSH server.'

    def handle(self, *args, **options):
        log.info("Starting shell server...")
        asyncio.run(server())
