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
import string
import sys

from argparse_setup import Argparse_Setup

class Argparse_Wrl(Argparse_Setup):
    def __init__(self, setup, parser=None):
        self.parser = argparse.ArgumentParser(description='setup.py: Application to fetch & setup a WindRiver Linux project.')
        Argparse_Setup.__init__(self, setup, parser)

    def handle_setup_args(self, parsed_args, args):
        if (parsed_args.buildtools_branch):
            # ignore (handled by setup.sh)
            del parsed_args.buildtools_branch

        if parsed_args.list_templates:
            if self.setup:
                self.setup.list_wrtemplates = True

        if (parsed_args.list_templates):
            return

        if parsed_args.templates:
            self.layer_select = True
            if self.setup:
                self.setup.wrtemplates = []
                for t in parsed_args.templates:
                    for wrtemplate in t.split(','):
                        self.setup.wrtemplates.append(wrtemplate)

        if parsed_args.dl_layers:
            self.layer_select = True
            if self.setup:
                self.setup.dl_layers = parsed_args.dl_layers

        if parsed_args.kernel:
            if self.setup:
                self.setup.kernel = parsed_args.kernel

        Argparse_Setup.handle_setup_args(self, parsed_args, args)

    def add_setup_options(self):
        Argparse_Setup.add_setup_options(self)

        setup_buildtools_branch = ""
        if self.setup and self.setup.buildtools_branch:
            setup_buildtools_branch = '(default %s)' % (self.setup.buildtools_branch)
        self.base_args.add_argument('--buildtools-branch', metavar="BRANCH", help='Buildtools branch %s' % (setup_buildtools_branch))

    def add_list_options(self):
        Argparse_Setup.add_list_options(self)
        self.list_args.add_argument('--list-templates', action='store_true', help='List all available templates')

    def add_layer_options(self):
        Argparse_Setup.add_layer_options(self)
        self.layer_args.add_argument('--templates', metavar='TEMPLATE', help='Select layers(s) based on template(s) and add them by default to the builds', nargs='+')
        self.layer_args.add_argument('--dl-layers', help='Enable download layers; these layers include predownloaded items', action='store_true')

    def add_other_options(self):
        Argparse_Setup.add_other_options(self)
        # WR Specific configuration

        self.misc_args = self.parser.add_argument_group('Miscellaneous')
        setup_kernel = ""
        setup_kernel_def = ""
        if self.setup:
            setup_kernel = self.setup.kernel
            setup_kernel_def = "(default %s)" % setup_kernel
        self.misc_args.add_argument('--kernel', metavar='KTYPE', help='Specify the target kernel configuration type %s' % (setup_kernel_def), default=setup_kernel)

