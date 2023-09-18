# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand

from ...interface.server import SshServer

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the termiverse SSH server.'

    def handle(self, *args, **options):
        server = SshServer('/Users/philchristensen/.ssh/id_rsa')
        server.start()
