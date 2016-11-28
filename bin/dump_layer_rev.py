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

# This program will load the index and for each layer list the layer,
# branch and current commit.  This can be used to verify that the
# index and layers are in sync.

import os
import sys

import settings

from layer_index import Layer_Index

mirror_path = 'mirror-index'
if not os.path.exists(mirror_path):
    if not os.path.exists(mirror_path + '.git'):
        print('No %s found.  Is this a mirror?' % mirror_path)
        sys.exit(1)
    else:
        mirror_path = mirror_path + '.git'

index = Layer_Index(indexcfg=settings.INDEXES, base_branch=None, replace=settings.REPLACE, mirror=mirror_path)

for lindex in index.index:
    for branch in lindex['branches']:
        basebranch = branch['name']
        for litem in lindex['layerItems']:
            for lbranch in lindex['layerBranches']:
                if lbranch['layer'] == litem['id']:
                    branch = basebranch
                    if lbranch['actual_branch'] != "":
                        branch = lbranch['actual_branch']
                    print('%s %s %s %s' % (litem['name'], litem['vcs_url'], branch, lbranch['vcs_last_rev']))
                    break
