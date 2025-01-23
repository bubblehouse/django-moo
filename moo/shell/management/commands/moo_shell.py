# -*- coding: utf-8 -*-
import asyncio

from django.core.management.base import BaseCommand

from ...server import server


class Command(BaseCommand):
    help = "Run the moo SSH server."

    def handle(self, *args, **options):
        import logging

        logging.info("Starting shell server...")
        asyncio.run(server())
