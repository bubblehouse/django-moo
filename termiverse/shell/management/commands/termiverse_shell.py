# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand

from ...interface.server import SshServer

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the termiverse SSH server.'

    def handle(self, *args, **options):
        log.info("Starting shell server...")
        server = SshServer('/etc/ssh/termiverse_private_key')
        server.start(address='0.0.0.0')
