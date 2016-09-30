#!/usr/bin/env python

# Everything mentioned must be python2 compatible
# for __init__ and any methods invoked here.

from argparse_setup import Argparse_Setup

# We need Setup because it provides defaults for several
# options.
#
parser = Argparse_Setup(None)
parser.evaluate_args(['--help'])


