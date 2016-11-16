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

import argparse

import os
import sys

import shutil

import subprocess

import xml.etree.ElementTree as ET

import utils_setup

from layer_index import Layer_Index

import logger_setup

import settings

def config_args(args):
    parser = argparse.ArgumentParser(description='flatten_mirror.py: Flatten a mirror.')

    parser.add_argument('dest', help='Destination Directory')

    parser.add_argument('--push-not-copy', help='Push non-bare layers, don\'t copy them.  This allows the flattened version to only have one branch.', action='store_true')

    parsed_args = parser.parse_args(args)

    return (parsed_args.dest, parsed_args.push_not_copy)

def push_or_copy(_src, _dst, _branch=None):
    if not git_push or not _branch:
        logger.plain('cp %s -> %s' % (_src, _dst))
        shutil.copytree(_src, _dst, symlinks=True, ignore_dangling_symlinks=True)
    else:
        logger.plain('push %s -> %s (%s)' % (_src, _dst, _branch))
        if os.path.exists(_dst):
            logger.critical('Destination %s already exists!' % _dst)
        os.makedirs(_dst, exist_ok=False)

        # New bare repo
        cmd = [ 'git', 'init', '--bare' ]
        utils_setup.run_cmd(cmd, cwd=_dst)

        # Push just the one branch
        cmd = [ 'git', 'push', _dst, _branch ]
        utils_setup.run_cmd(cmd, cwd=_src)

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

# This assumes variables 'dest', 'git_push', and
# 'setup_dir' is globally set.
def main():
    global branch

    if os.path.exists(dest):
        logger.critical('Destination directory %s already exists.  Please choose a different destination.' % (dest))
        return 1

    mirror_path = os.path.abspath('mirror-index')
    if not os.path.exists(mirror_path):
        logger.critical('No mirror-index found. %s' % mirror_path)
        return 1

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

    push_or_copy(src, dst, branch)

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

    push_or_copy(src, dst)

    tree = ET.parse('default.xml')
    root = tree.getroot()

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

        dst = os.path.join(dest, os.path.basename(src))

        revision = None
        if not ('bare' in child.attrib and child.attrib['bare'] == 'True'):
            revision = default_revision
            if 'revision' in child.attrib:
                revision = child.attrib['revision']

        push_or_copy(src, dst, revision)

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

        index.serialize_index(lindex, os.path.join(dst, lindex['CFG']['DESCRIPTION']), split=True, IncludeCFG=True, mirror=True, base_url=base_url)

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


# Define globals
if __name__ == '__main__':
    logger = logger_setup.setup_logging()
    dest, git_push = config_args(sys.argv[1:])

    subset_folders = None
    branch = None

    setup_dir = os.path.dirname(os.path.dirname(sys.argv[0]))

    ret = main()
    sys.exit(ret)
