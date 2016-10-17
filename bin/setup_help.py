#!/usr/bin/env python

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

# Everything mentioned must be python2 compatible
# for __init__ and any methods invoked here.

from argparse_setup import Argparse_Setup

# We need Setup because it provides defaults for several
# options.
#
parser = Argparse_Setup(None)
parser.evaluate_args(['--help'])


