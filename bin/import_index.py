#!/usr/bin/env python3

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

# Quick and dirt hack..  This makes it easier to take a DB dump from
# a layerindex and munge it for internal consumption by the setup
# program.
#
# You will need to adjust the items below...
#
# To get the input file, in your layerIndex run:
#   python3 manage.py dumpdata > /tmp/input.json
#
# By default the output will be organized by layerbranch in /tmp/output
#
# Split the results by base/bsp/addon
#
# example:
#   (cd /tmp/output ; cp `grep layer_type * | grep -v \"B\" | cut -f 1 -d :` /home/mhatle/git/lpd/wrlinux-x/data/index/base/.)
#   (cd /tmp/output ; cp `grep layer_type * | grep \"B\" | cut -f 1 -d :` /home/mhatle/git/lpd/wrlinux-x/data/index/bsps/.)
#

import os
import sys

REPLACE = [
            ( 'git://msp-git.wrs.com/git', '#BASE_URL#' ),
          ]

INDEXES = [
    {
        'DESCRIPTION' : 'Wind River Linux Index',
        'TYPE' : 'export',
        'URL' : '/tmp/input',
        'CACHE' : None,
    },
]

OUTPUT = '/tmp/output'

from layer_index import Layer_Index

index = Layer_Index(INDEXES, base_branch="")

for lindex in index.index:
    for entry in lindex['layerItems']:
        for obj in entry:
            # Run replace on any 'url' items.
            if 'url' in obj:
                vcs_url = entry[obj]
                for (search, replace) in REPLACE:
                    vcs_url = vcs_url.replace(search, replace)
                entry[obj] = vcs_url

    os.makedirs(OUTPUT, exist_ok=True)
    index.serialize_django_export(lindex, OUTPUT + '/' + lindex["name"], split=True)
