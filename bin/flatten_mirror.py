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

# This program will flatten a mirror and copy the result into a target dir.
#
# Many git servers require a single flat level of git trees in order to
# work properly.  Flattening the tree will require both renaming directories
# as well as updating the mirror-index to match.

import os
import sys

import shutil

import subprocess

import xml.etree.ElementTree as ET

import utils_setup

from layer_index import Layer_Index

import logger_setup

import settings

if len(sys.argv) < 2:
    print("usage: %s <dest>" % sys.argv[0])
    sys.exit(1)

logger = logger_setup.setup_logging()

dest = os.path.abspath(sys.argv[1])

if os.path.exists(dest):
    logger.critical('Destination directory %s already exists.  Please choose a different destination.' % (dest))
    sys.exit(1)

mirror_path = os.path.abspath('mirror-index')
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

# We assume this program is located in the bin directory
setup_dir = os.path.dirname(os.path.dirname(sys.argv[0]))

# Create the destination
os.makedirs(dest)

# Duplicate the setup dir to a bare repo
src = os.path.join(setup_dir, '.git')
dst = os.path.join(dest, os.path.basename(setup_dir))
if not dst.endswith('.git'):
    dst += '.git'

logger.plain('%s -> %s' % (src, dst))
shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)

# Duplicate the git-repo.git
src = os.path.abspath('git-repo')
if not os.path.exists(src):
    src = os.path.abspath('git-repo.git')
    if not os.path.exists(src):
        logger.critical("Unable to find git-repo.git!")
        sys.exit(1)
dst = os.path.join(dest, os.path.basename(src))
if not dst.endswith('.git'):
    dst += '.git'

logger.plain('%s -> %s' % (src, dst))
shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)

tree = ET.parse('default.xml')
root = tree.getroot()

for child in root:
    if child.tag != 'project':
        continue

    src = child.attrib['name']

    if not os.path.exists(src):
        if os.path.exists(src + '.git'):
            src += '.git'
        else:
            logger.warning('Unable to find %s' % src)
            continue

    dst = os.path.join(dest, os.path.basename(src))

    logger.plain('%s -> %s' % (src, dst))
    shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)

index = Layer_Index(indexcfg=settings.INDEXES, base_branch=branch, replace=settings.REPLACE, mirror=mirror_path)

# Transform and export the mirror index
dst = os.path.join(dest, 'mirror-index')

os.makedirs(dst)

cmd = ['git', 'init', dst]
utils_setup.run_cmd(cmd, cwd=dest)

cmd = ['git', 'checkout', '-b', branch]
try:
    utils_setup.run_cmd(cmd, cwd=dst)
except:
    # if we failed, then simply try to switch branches
    cmd = ['git', 'checkout', branch]
    utils_setup.run_cmd(cmd, cwd=dst)

def transform_xml(_src, _dest):
    logger.plain('Processing %s' % _src)
    fin = open(_src, 'rt')
    fout = open(_dest, 'wt')
    for line in fin:
        modified = False
        try:
            _root = ET.fromstring(line)
        except:
            fout.write('%s' % line)
            continue

        if _root.tag != 'project':
            fout.write('%s' % line)
            continue

        for attrib in _root.attrib:
            if attrib == 'name' and _root.attrib['name'] != _root.attrib['name'].split('/')[-1]:
                _root.attrib['name'] = _root.attrib['name'].split('/')[-1]
                modified = True

        for _child in _root:
            for attrib in _child.attrib:
                if attrib == 'name' and _child.attrib['name'] != _child.attrib['name'].split('/')[-1]:
                    _child.attrib['name'] = _child.attrib['name'].split('/')[-1]
                    modified = True

        if modified:
            fout.write('    %s\n' % (ET.tostring(_root, encoding='unicode')))
        else:
            fout.write('%s' % line)

logger.plain('Transforming index...')
dst_xml = os.path.join(dst, 'xml')

os.makedirs(dst_xml)

for lindex in index.index:
    for layer in lindex['layerItems']:
        if 'vcs_url' in layer:
            layer['vcs_url'] = '#BASE_URL#' + '/' + layer['vcs_url'].split('/')[-1]
            layer['vcs_web_url'] = ''
            layer['vcs_web_tree_base_url'] = ''
            layer['vcs_web_file_base_url'] = ''
            layer['mailing_list_url'] = ''

        src = os.path.join(mirror_path, 'xml', '%s.inc' % layer['name'])
        if os.path.exists(src):
            transform_xml(src, os.path.join(dst_xml, '%s.inc' % layer['name']))

        src = os.path.join(mirror_path, 'xml', '%s.xml' % layer['name'])
        if os.path.exists(src):
            transform_xml(src, os.path.join(dst_xml, '%s.xml' % layer['name']))

        if layer['name'] == 'openembedded-core':
            src = os.path.join(mirror_path, 'xml', 'bitbake.inc')
            if os.path.exists(src):
                transform_xml(src, os.path.join(dst_xml, 'bitbake.inc'))

            src = os.path.join(mirror_path, 'xml', 'bitbake.xml')
            if os.path.exists(src):
                transform_xml(src, os.path.join(dst_xml, 'bitbake.xml'))

    index.serialize_index(lindex, os.path.join(dst, lindex['CFG']['DESCRIPTION']), split=True, IncludeCFG=True, mirror=True)

# git add file.
cmd = ['git', 'add', '-A', '.']
utils_setup.run_cmd(cmd, cwd=dst)

cmd = ['git', 'diff-index', '--quiet', 'HEAD', '--']
try:
    utils_setup.run_cmd(cmd, cwd=dst)
except:
    logger.debug('Updating mirror-index')
    cmd = ['git', 'commit', '-m', 'Updated index - Flatten Mirror']
    utils_setup.run_cmd(cmd, cwd=dst)

logger.plain('Done')

