#!/usr/bin/env python3

# Copyright (C) 2016-2017 Wind River Systems, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

# Please keep these sorted.
import logging
import os
import sys
import argparse

import logger_setup

logger = logger_setup.setup_logging()
logger.setLevel(logging.DEBUG)

# Redirect stdout and stderr to the custom logger.  This allows us to use
# python modules that may output only via stdout/stderr.
sys.stdout = logger_setup.LoggerOut(logger.info)
sys.stderr = logger_setup.LoggerOut(logger.error)

def parse_args():
    parser = argparse.ArgumentParser(description='test-network.py: Application to check network connection ability.')

    # Define arguments
    parser.add_argument("repoURL", help="The repoURL provided by Windshare.")

    parser.parse_args()
    return parser.parse_args()

def dump_proxies():
    logger.info("Checking if proxies are enabled in the environment...")

    if 'http_proxy' in os.environ:
        logger.debug("http_proxy = %s" % (os.environ['http_proxy']))
    else:
        logger.debug("No http_proxy defined.")

    if 'https_proxy' in os.environ:
        logger.debug("https_proxy = %s" % (os.environ['https_proxy']))
    else:
        logger.debug("No https_proxy defined.")

def test_windshare(repoUrl):
    logger.info("Running Windshare test based on repoURL: %s" % repoUrl)

    from windshare import Windshare
    ws = Windshare(debug=1)
    ws.interactive = 1

    from urllib.parse import urlsplit, urlunsplit

    (uscheme, uloc, upath, uquery, ufragid) = urlsplit(repoUrl)

    base_folder = os.path.basename(upath)

    if not base_folder or base_folder == "":
        logger.error("Invalid URL, unable to determine base_folder")
        return

    # Folder root is one directory higher
    upath = os.path.dirname(upath)
    base_url = urlunsplit((uscheme, uloc, upath, uquery, ufragid))

    logger.debug("BASE URL = %s" % base_url)

    # Determine if this is a windshare install
    (ws_base_url, _, ws_entitlement_url) = ws.get_windshare_urls(base_url)

    if ws_base_url and ws_base_url != "" and ws.load_folders(ws_entitlement_url):
        logger.info('Detected Windshare configuration.  Processing entitlements and indexes.')
    else:
        logger.info('Unable to detect Windshare configuration!  No entitlements available.')

    return ws

if __name__ == "__main__":
    args = parse_args()

    logger.info("------------- Environment Information --------------")
    logger.info(sys.version)
    logger.plain("")

    logger.info("---------------- Proxy Information -----------------")
    dump_proxies()
    logger.plain("")

    if args.repoURL:
        logger.info("-------------- Windshare Information ---------------")
        windshare = test_windshare(args.repoURL)
        logger.plain("")

        logger.info("------------- Available Entitlements ---------------")
        for folder in windshare.folders or [ 'none (Unable to load Windshare data)' ]:
            logger.info('    %s' % folder)
        logger.plain("")
