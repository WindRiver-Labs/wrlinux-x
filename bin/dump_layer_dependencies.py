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

# This program will dump the dependencies for one or more layers in a
# given branch.  It can be used to verify that when a branch is created
# that the dependencies have been scanned properly.

# Adjust the standard WR urls to make comparisons easier.
REPLACE = [
            ( 'git://git.wrs.com/', '#BASE_URL#' ),
            ( 'http://git.wrs.com/cgit/', '#BASE_WEB#' ),
          ]

# Note the branch can be hard coded.  This is required only when you want
# to limit the branch from a restapi-web import.  (This does not do anything
# on other input formats.)
INDEXES = [
    {
        'DESCRIPTION' : 'Wind River Developer Layer Index',
        'TYPE' : 'restapi-web',
        'URL' : 'http://layers.wrs.com/layerindex/api/',
        'CACHE' : None,
        #'BRANCH' : 'WRLINUX_9_BASE',
    },
]

import os
import sys

from layer_index import Layer_Index

def usage():
    print("usage: %s <branch>" % sys.argv[0])
    sys.exit(1)

if len(sys.argv) < 2:
    usage()

base_branch=sys.argv[1]

index = Layer_Index(INDEXES, base_branch=base_branch, replace=REPLACE)

import unicodedata
for lindex in index.index:
    dep_out = []
    branchid = index.getBranchId(lindex, index.getIndexBranch(default=base_branch, lindex=lindex))
    if branchid:
        for lb in lindex['layerBranches']:
            if lb['branch'] == branchid:
                for layer in index.find_layer(lindex, layerBranch=lb):
                    name = layer['name']
                    (required, recommended) = index.getDependencies(lindex, lb)
                    reqnames = []
                    recnames = []
                    for req in required:
                        for layer in index.find_layer(lindex, layerBranch=req):
                            reqnames.append(layer['name'])
                    for rec in recommended:
                        for layer in index.find_layer(lindex, layerBranch=rec):
                            recnames.append(layer['name'])

                    dep_out.append((name, ' '.join(sorted(reqnames)), ' '.join(sorted(recnames))))

    for (name, reqs, recs) in sorted(dep_out, key=lambda t: t[0]):
       print('%s %s (%s)' % (name, reqs, recs))
