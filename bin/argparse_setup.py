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

# Note this class MUST run in both python2 and python3

import argparse
import logging
import string
import sys

class Argparse_Setup:
    def __init__(self, setup, parser=None):
        if not parser:
            parser = argparse.ArgumentParser(description='setup.py: Application to fetch & setup a distribution project.')
        self.parser = parser
        self.setup = setup

    def evaluate_args(self, args):
        self.add_options()
        parsed_args = self.parser.parse_args(args)
        self.handle_setup_args(parsed_args)

    def handle_setup_args(self, parsed_args):
        # Parse setup options
        if (parsed_args.verbose):
            if self.setup:
                self.setup.set_debug()
            del parsed_args.verbose

        if (parsed_args.base_url):
            if self.setup:
                self.setup.set_base_url(parsed_args.base_url)
            del parsed_args.base_url

        if (parsed_args.base_branch):
            if self.setup:
                self.setup.set_base_branch(parsed_args.base_branch)
            del parsed_args.base_branch

        if (parsed_args.mirror):
            if self.setup:
                self.setup.mirror = parsed_args.mirror

        # Parse repo option
        if (parsed_args.repo_jobs):
            if self.setup:
                self.setup.set_jobs(parsed_args.repo_jobs)
            del parsed_args.repo_jobs

        # Look for list options
        if parsed_args.list_distros:
            if self.setup:
                self.setup.list_distros = True

        if parsed_args.list_machines:
            if self.setup:
                self.setup.list_machines = True

        if parsed_args.list_layers:
            if self.setup:
                self.setup.list_layers = True

        if parsed_args.list_recipes:
            if self.setup:
                self.setup.list_recipes = True

        if (parsed_args.list_distros or parsed_args.list_machines or parsed_args.list_layers or parsed_args.list_recipes):
            return

        # Parse layer selection options
        if parsed_args.distros:
            if self.setup:
                self.setup.distros = []
                for d in parsed_args.distros:
                    for distro in d.split(','):
                        self.setup.distros.append(distro)

        if parsed_args.machines:
            if self.setup:
                self.setup.machines = []
                for m in parsed_args.machines:
                    for machine in m.split(','):
                        self.setup.machines.append(machine)

        if parsed_args.layers:
            if self.setup:
                self.setup.layers = []
                for l in parsed_args.layers:
                    for layer in l.split(','):
                        self.setup.layers.append(layer)

        if parsed_args.recipes:
            if self.setup:
                self.setup.recipes = []
                for r in parsed_args.recipes:
                    for recipe in r.split(','):
                        self.setup.recipes.append(recipe)

        if parsed_args.all_layers:
            if self.setup:
                self.setup.all_layers = parsed_args.all_layers

        if parsed_args.no_recommend:
            if self.setup:
                self.setup.no_recommend = parsed_args.no_recommend

    def add_setup_options(self):
        # Setup options
        self.parser.add_argument('-v', '--verbose', help='Set the verbosity to debug', action="store_true")

        setup_base_url = ""
        if self.setup and self.setup.base_url:
            setup_base_url = '(default %s)' % (self.setup.base_url)
        self.parser.add_argument('--base-url', metavar="URL", help='URL to fetch from %s' % (setup_base_url))

        setup_base_branch = ""
        if self.setup and self.setup.base_branch:
            setup_base_branch = '(default %s)' % (self.setup.base_branch)
        self.parser.add_argument('--base-branch', metavar="BRANCH", help='Base branch identifier %s' % (setup_base_branch))

        self.parser.add_argument('--mirror', help='Do not construct a project, instead construct a mirror for other projects', action='store_true')

    def add_repo_options(self):
        # Repo options
        setup_jobs = ""
        if self.setup and self.setup.jobs:
            setup_jobs = '(default %s)' % (self.setup.jobs)
        self.parser.add_argument('-rj', '--repo-jobs', help='Sets repo project to fetch simultaneously %s' % (setup_jobs))

    def add_list_options(self):
        # List options
        self.parser.add_argument('--list-distros',   action='store_true', help='List all available distro values.')
        self.parser.add_argument('--list-machines',  action='store_true', help='List all available machine values.')
        self.parser.add_argument('--list-layers',    action='store_true', help='List all available layers.')
        self.parser.add_argument('--list-recipes',   action='store_true', help='List all available recipes.')

    def add_layer_options(self):
        # Layer selection and local.conf setup
        setup_distro = ""
        setup_distro_str = ""
        if self.setup and self.setup.distros:
            setup_distro = self.setup.distros[0]
            setup_distro_str = '(default %s)' % setup_distro
        self.parser.add_argument('--distros', metavar='distro', help='Select layer(s) based on required distribution and set the default DISTRO= value %s' % setup_distro_str, nargs="+")

        setup_machine = ""
        setup_machine_str = ""
        if self.setup and self.setup.machines:
            setup_machine = self.setup.machines[0]
            setup_machine_str = '(default %s)' % setup_machine
        self.parser.add_argument('--machines', metavar='MACHINE', help='Select layer(s) based on required machine(s) and set the default MACHINE= value %s' % setup_machine_str, nargs='+')

        self.parser.add_argument('--layers', metavar='LAYER', help='Select layer(s) to include in the project and add to the default bblayers.conf', nargs='+')
        self.parser.add_argument('--recipes', metavar='RECIPE', help='Select layers(s) based on recipe(s)', nargs='+')
        self.parser.add_argument('--all-layers', help='Select all available layers', action='store_true')
        self.parser.add_argument('--no-recommend', help='Disable recommended layers during layer resolution', action='store_true')

    def add_other_options(self):
        pass

    def add_options(self):
        self.add_setup_options()
        self.add_repo_options()
        self.add_list_options()
        self.add_layer_options()
        self.add_other_options()
