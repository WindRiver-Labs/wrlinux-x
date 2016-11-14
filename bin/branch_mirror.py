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

# This program will identify the layers, and their current branches,
# that need to be branched as part of the release process.
#
# The program will branch them and provide a list that can be used
# to push the items.
#
# The program will also update the mirror index entries with the
# branch names.

import os
import sys

import subprocess

import xml.etree.ElementTree as ET

import utils_setup

from layer_index import Layer_Index

import logger_setup

import settings

completed = []

def usage():
    print("usage: %s <branch> [--force]" % sys.argv[0])
    sys.exit(1)

if len(sys.argv) < 2:
    usage()

logger = logger_setup.setup_logging()

dest_branch = sys.argv[1]

force = False
if len(sys.argv) > 2:
    if sys.argv[2] != '--force':
        usage()

    force = True

mirror_path = 'mirror-index'
if not os.path.exists(mirror_path):
    logger.critical('No mirror-index found. %s' % mirror_path)
    sys.exit(1)

cmd = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
ret = subprocess.Popen(cmd, cwd=mirror_path, close_fds=True, stdout=subprocess.PIPE)
branch = ""
output = ""
while True:
    output = ret.stdout.readline()
    if not output and ret.poll() is not None:
        break
    branch += output.decode('utf-8')
ret.wait()
branch = branch.strip()

if branch == dest_branch:
    logger.warning('Branch is already configured!')

work_list = []

def git_branch(_dst, _orig_branch, _branch):
    logger.info('Branching %s: %s -> %s' % (_dst, _orig_branch, _branch))

    _cmd = [ 'git', 'fetch', '.', '%s:%s' % (_orig_branch, _branch) ]
    if force:
        _cmd.append('-f')
    utils_setup.run_cmd(_cmd, cwd=_dst)

    work_list.append('%s %s' % (_dst, _branch))

# We assume this program is located in the bin directory
dst = os.path.dirname(os.path.dirname(sys.argv[0]))

# Branch the setup program....
git_branch(_dst=dst, _orig_branch=branch, _branch=dest_branch)
completed.append(dst)

# Transform and export the mirror index
git_branch(mirror_path, branch, dest_branch)
completed.append(mirror_path)

index = Layer_Index(indexcfg=settings.INDEXES, base_branch=branch, replace=settings.REPLACE, mirror=mirror_path)

cmd = ['git', 'checkout', dest_branch]
utils_setup.run_cmd(cmd, cwd=mirror_path)

logger.info('Loading default.xml')
tree = ET.parse('default.xml')
root = tree.getroot()



logger.info('Branching based on default.xml')
default_revision = None
base_url = None
for child in root:
    if child.tag == 'remote':
        if 'fetch' in child.attrib:
            base_url = child.attrib['fetch']

    if child.tag == 'default':
        if 'revision' in child.attrib:
            default_revision = child.attrib['revision']

    if child.tag != 'project':
        continue

    src = child.attrib['name']

    if not os.path.exists(src):
        if os.path.exists(src + '.git'):
            src += '.git'
        else:
            logger.warning('Unable to find %s' % src)
            continue

    revision = None
    if not ('bare' in child.attrib and child.attrib['bare'] == 'True'):
        revision = default_revision
        if 'revision' in child.attrib:
            revision = child.attrib['revision']

    if revision:
        git_branch(src, revision, dest_branch)
    completed.append(src)



logger.info('Transforming default.xml')
for child in root:
    if 'revision' in child.attrib:
        child.attrib['revision'] = dest_branch
open('default.xml', 'wt').write(ET.tostring(root, encoding='unicode'))



logger.info('Transforming index...')

bitbake_branch = branch
branchid = None
for lindex in index.index:
    for branches in lindex['branches']:
        if 'name' in branches and branches['name'] == branch:
            branches['name'] = dest_branch
            if 'bitbake_branch' in branches and branches['bitbake_branch'] != '':
                bitbake_branch = branches['bitbake_branch']
                branches['bitbake_branch'] = dest_branch
            branchid = branches['id']

    for layer in lindex['layerItems']:
        if layer['vcs_url']:
            for lb in lindex['layerBranches']:
                if layer['id'] == lb['layer'] and lb['branch'] == branchid:
                    if 'actual_branch' in lb and lb['actual_branch'] != "":
                        lb['actual_branch'] = ''

    # Remove older entries
    for (dirpath, dirnames, filenames) in os.walk(mirror_path):
        if dirpath.endswith('/.git') or '/.git/' in dirpath or dirpath.endswith('/xml') or '/xml/' in dirpath:
            continue
        for filename in filenames:
            if filename.startswith(lindex['CFG']['DESCRIPTION'].translate(str.maketrans('/ ', '__'))):
                os.remove(os.path.join(dirpath, filename))

    index.serialize_index(lindex, os.path.join(mirror_path, lindex['CFG']['DESCRIPTION']), split=True, IncludeCFG=True, mirror=True, base_url=base_url)

# git add file.
cmd = ['git', 'add', '-A', '.']
utils_setup.run_cmd(cmd, cwd=mirror_path)

cmd = ['git', 'diff-index', '--quiet', 'HEAD', '--']
try:
    utils_setup.run_cmd(cmd, cwd=mirror_path)
except:
    logger.debug('Updating mirror-index')
    cmd = ['git', 'commit', '-m', 'Branch (%s) and adjust index entries' % (dest_branch)]
    utils_setup.run_cmd(cmd, cwd=mirror_path)

logger.info('Done')

logger.plain('Writing branched-layer.list...')
output = open('branched-layer.list', 'wt')
for item in work_list:
    output.write("%s\n" % item)
output.close()
