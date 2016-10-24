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

import settings

import os

class Setup():
    jobs = settings.REPO_JOBS
    distros = [ settings.DEFAULT_DISTRO ]
    machines = [ settings.DEFAULT_MACHINE ]
    kernel = settings.DEFAULT_KTYPE

    def __init__(self):
       # Pull in the defaults from the environment (set by setup.sh)
        self.base_url = os.getenv('OE_BASEURL')
        self.base_branch = os.getenv('OE_BASEBRANCH')
        self.buildtools_branch = os.getenv('OE_BUILDTOOLS_BRANCH')
        self.buildtools_remote = os.getenv('OE_BUILDTOOLS_REMOTE')

parser = Argparse_Setup(Setup())
parser.evaluate_args(['--help'])


