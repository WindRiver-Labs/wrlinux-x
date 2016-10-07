# Note this class MUST run in both python2 and python3

import argparse
import logging
import string
import sys

# This class is to validate configure arguments.
# Self-contained to hide the crimes of the past.
class Argparse_Configure:
    def __init__(self, parser, setup):
        self.parser = parser
        self.setup = setup
        self.add_configure_options()
        self.configure_arguments = []
        self.workaround_args = {}


    def handle_configure_args(self, parsed_args):
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

        if parsed_args.list_templates:
            if self.setup:
                self.setup.list_wrtemplates = True

        if (parsed_args.list_distros or parsed_args.list_machines or parsed_args.list_layers or parsed_args.list_recipes or parsed_args.list_templates):
            return

        # Parse actual configuration options
        if parsed_args.distros:
            if self.setup:
                self.setup.distros = [ parsed_args.distros ]

        #if not parsed_args.machines:
        #    raise StandardError('You must specify at least one machine')
        #else:
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

        if parsed_args.templates:
            if self.setup:
                self.setup.wrtemplates = []
                for t in parsed_args.templates:
                    for wrtemplate in t.split(','):
                        self.setup.wrtemplates.append(wrtemplate)

        if parsed_args.all_layers:
            if self.setup:
                self.setup.all_layers = parsed_args.all_layers

        if parsed_args.dl_layers:
            if self.setup:
                self.setup.dl_layers = parsed_args.dl_layers

        if parsed_args.no_recommend:
            if self.setup:
                self.setup.no_recommend = parsed_args.no_recommend


        for key in vars(parsed_args):
            if (getattr(parsed_args, key)):
                name = key.translate(str.maketrans('_', '-'))
                val = getattr(parsed_args, key)
                if type(val) is list:
                   val = ",".join(val)
                arg = '--%s=%s' % (name, val)
                self.configure_arguments.append(arg)
                if key in self.workaround_args:
                    del self.workaround_args[key]

        for key in self.workaround_args.keys():
            arg = '--%s=%s' % (key, self.workaround_args[key])
            self.configure_arguments.append(arg)

        self.configure_arguments = sorted(self.configure_arguments)

    def add_configure_options(self):
        # List options
        self.parser.add_argument('--list-distros',   action='store_true', help='List all available distro values.')
        self.parser.add_argument('--list-machines',  action='store_true', help='List all available machine values.')
        self.parser.add_argument('--list-layers',    action='store_true', help='List all available layers.')
        self.parser.add_argument('--list-recipes',   action='store_true', help='List all available recipes.')
        self.parser.add_argument('--list-templates', action='store_true', help='List all available templates.')

        # Layer selection and local.conf setup
        setup_distro = ""
        setup_distro_str = ""
        if self.setup:
            setup_distro = self.setup.distros[0]
            setup_distro_str = '(default %s)' % setup_distro
        self.parser.add_argument('--distros', metavar='distro', help='Select layer(s) based on required distribution and set the default DISTRO= value %s' % setup_distro_str, default=setup_distro)

        setup_machine = ""
        setup_machine_str = ""
        if self.setup:
            setup_machine = self.setup.machines[0]
            setup_machine_str = '(default %s)' % setup_machine
        self.parser.add_argument('--machines', metavar='MACHINE', help='Select layer(s) based on required machine(s) and set the default MACHINE= value %s' % setup_machine_str, nargs='+')

        self.parser.add_argument('--layers', metavar='LAYER', help='Select layer(s) to include in the project and add to the default bblayers.conf', nargs='+')
        self.parser.add_argument('--recipes', metavar='RECIPE', help='Select layers(s) based on recipe(s)', nargs='+')
        self.parser.add_argument('--templates', metavar='TEMPLATE', help='Select layers(s) based on template(s) and add them by default to the builds', nargs='+')
        self.parser.add_argument('--all-layers', help='Select all available layers', action='store_true')

        # WR Specific configuration
        setup_kernel = ""
        setup_kernel_def = ""
        if self.setup:
            setup_kernel = self.setup.kernel
            setup_kernel_def = "(default %s)" % setup_kernel
        self.parser.add_argument('--kernel', metavar='KTYPE', help='Specify the target kernel configuration type %s' % (setup_kernel_def), default=setup_kernel)

        # Handle download support
        self.parser.add_argument('--no-recommend', help='Disable recommended layers during layer resolution', action='store_true')
        self.parser.add_argument('--dl-layers', help='Enable download layers, these layers include predownloaded items', action='store_true')
        #self.parser.add_argument('--enable-internet-download', help='Allow internet download during software build, sets BB_NO_NETWORK="0"', dest='no_network', action='store_false')
        #self.parser.add_argument('--disable-internet-download', help='Allow internet download during software build, sets BB_NO_NETWORK="1"', dest='no_network', action='store_true')
        #self.parser.add_argument('--allowed-download-networks', help='Limit allowed internet downloads to specified networks, sets BB_ALLOWED_NETWORKS', nargs='+', dest='allowed_network')
