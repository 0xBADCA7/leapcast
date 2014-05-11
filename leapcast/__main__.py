#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

import signal
import logging
import sys
from os import environ

sys.path.append('.')

from leapcast.environment import parse_cmd, Environment
from leapcast.services.leap import LEAPserver
from leapcast.services.ssdp import SSDPserver
from leapcast.services.bonjour import BonjourServer
from leapcast.services.castsocket import CastSocketServer

logger = logging.getLogger('Leapcast')


def main():
    parse_cmd()

    if sys.platform == 'darwin' and environ.get('TMUX') is not None:
        logger.error('Running Chrome inside tmux on OS X might cause problems.'
                     ' Please start leapcast outside tmux.')
        sys.exit(1)

    def shutdown(signum, frame):
        #ssdp_server.shutdown()
        bonjour_server.shutdown()
        castsocket_server.shutdown()
        leap_server.sig_handler(signum, frame)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    #ssdp_server = SSDPserver()
    #ssdp_server.start(Environment.interfaces)

    castsocket_server = CastSocketServer()
    castsocket_server.start()

    bonjour_server = BonjourServer()
    bonjour_server.start(Environment.uuid, Environment.friendlyName)

    leap_server = LEAPserver()
    leap_server.start()

if __name__ == "__main__":
    main()
