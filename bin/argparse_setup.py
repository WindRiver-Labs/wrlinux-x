# Copyright (C) 2016 Wind River Systems, Inc.
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

# Note this class must run in both python2 and python3

import argparse
import logging

from argparse_configure import Argparse_Configure

class Argparse_Setup:

    def __init__(self, setup):
        self.setup = setup;
        self.parser = argparse.ArgumentParser(description='setup.py: Application to fetch & setup a WindRiver Linux project.')
        self.argparse_conf = Argparse_Configure(self.parser, setup)

    def evaluate_args(self, args):
        self.setup_arg_parser()

        parsed_args = self.parser.parse_args(args)

        self.handle_setup_args(parsed_args)
        self.argparse_conf.handle_configure_args(parsed_args)

    def handle_setup_args(self, parsed_args):
        # Parse command line arguments for setup AND DELETE THEM to avoid passing them off to configure.
        if (parsed_args.verbose):
            if self.setup:
                self.setup.set_debug()
            del parsed_args.verbose

        if (parsed_args.repo_jobs):
            if self.setup:
                self.setup.set_jobs(parsed_args.repo_jobs)
            del parsed_args.repo_jobs

        if (parsed_args.base_url):
            if self.setup:
                self.setup.set_base_url(parsed_args.base_url)
            del parsed_args.base_url

        if (parsed_args.core_branch):
            if self.setup:
                self.setup.set_base_branch(parsed_args.core_branch)
            del parsed_args.core_branch

        if (parsed_args.buildtools_branch):
            # ignore (handled by setup.sh)
            del parsed_args.buildtools_branch

        if (parsed_args.mirror):
            if self.setup:
                self.setup.mirror = parsed_args.mirror

    def setup_arg_parser(self):
        self.parser.add_argument('-v', '--verbose', help='Set the verbosity to debug',
                action="store_true")

        setup_jobs = ""
        if self.setup:
            setup_jobs = '(default %s)' % (self.setup.jobs)
        self.parser.add_argument('-rj', '--repo-jobs', help='Sets repo project to fetch simultaneously %s' % (setup_jobs))

        setup_base_url = ""
        if self.setup:
            setup_base_url = '(default %s)' % (self.setup.base_url)
        self.parser.add_argument('--base-url', metavar="URL", help='URL to fetch from %s' % (setup_base_url))

        setup_base_branch = ""
        if self.setup:
            setup_base_branch = '(default %s)' % (self.setup.base_branch)
        self.parser.add_argument('--core-branch', metavar="BRANCH", help='Core branch identifier %s' % (setup_base_branch))
        self.parser.add_argument('--buildtools-branch', metavar="BRANCH", help='Buildtools branch %s' % (setup_base_branch))

        self.parser.add_argument('--mirror', help='Do not construct a project, instead construct a mirror for other projects', action='store_true')
