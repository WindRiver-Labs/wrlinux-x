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

# Format of the subset folder file is:
# <layer> <folder>
#
# <layer> is the name in the layer index of that layer
# <folder> is a directory to generate inside of the <dest>
#
# Note, if this is used, an error will be generated for any known layers
# that are not assigned to a folder.
#
# A special folder name '[SKIP]' is defined when you are intentionally
# skipping a layer.

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
    parser.add_argument('--subset-mirror', metavar='FILE', help='Use a file that will allow the system to subset the mirror into specific subdirectories.')
    parser.add_argument('--strip-git', help='Strip the .git suffix from paths when copying.  This is needed when copying to an http server, vs a git server.', action='store_true')

    parsed_args = parser.parse_args(args)

    return (parsed_args.dest, parsed_args.push_not_copy, parsed_args.subset_mirror, parsed_args.strip_git)

def push_or_copy(_layer, _src, _dst, _branch=None):
    if subset_folders:
        if _layer not in subset_folders:
            logger.critical("Layer %s (%s) not in SUBSET_FOLDERS" % (_layer, _src))
            raise
        elif subset_folders[_layer] == "[SKIP]":
            return
        else:
            dstdir = os.path.dirname(_dst)
            dstbase = os.path.basename(_dst)
            _dst = os.path.join(dstdir, subset_folders[_layer], dstbase)

    if not os.path.exists(_src):
        _src += '.git'
        if not os.path.exists(_src):
            logger.critical("Unable to find %s!" % _src)
            raise

    # Make output consistent
    if not strip_git and not _dst.endswith('.git'):
        _dst += '.git'

    if strip_git and _dst.endswith('.git'):
        _dst = _dst[:-4]

    if not git_push or not _branch:
        logger.plain('cp %s -> %s' % (_src, _dst))
        shutil.copytree(_src, _dst, symlinks=True, ignore_dangling_symlinks=True)
    else:
        logger.plain('push %s -> %s (%s)' % (_src, _dst, _branch))
        if os.path.exists(_dst):
            logger.critical('Destination %s already exists!' % _dst)
            raise
        os.makedirs(_dst, exist_ok=True)

        # New bare repo
        _cmd = [ 'git', 'init', '--bare' ]
        utils_setup.run_cmd(_cmd, cwd=_dst)

        # Push just the one branch
        _cmd = [ 'git', 'push', os.path.abspath(_dst), _branch ]
        utils_setup.run_cmd(_cmd, cwd=_src)

# Used to subset target mirror path, if necessary

# Return the mirror_directory target for a given layer entry.
# If the target directory does not exist, we create it (git repository)
#
# This function will return None if the layer is to be skipped.
def get_mirror_dir(_layer, _dst):
    if subset_folders:
        if _layer in subset_folders:
            if subset_folders[_layer] == "[SKIP]":
                return None

            dstdir = os.path.dirname(_dst)
            dstbase = os.path.basename(_dst)
            _dst = os.path.join(dstdir, subset_folders[_layer], dstbase)
        else:
            logger.error("Layer %s not in SUBSET_FOLDERS" % _layer)
            # Use default directory

    # If the target directory does not exist, create it
    if not os.path.exists(_dst):
        cmd = ['git', 'init', _dst]
        utils_setup.run_cmd(cmd)

        if not branch or branch == "":
            logger.critical('Where did the branch val go!? %s' % branch)
            raise

        cmd = ['git', 'checkout', '-b', branch]
        try:
            utils_setup.run_cmd(cmd, cwd=_dst)
        except:
            # if we failed, then simply try to switch branches
            cmd = ['git', 'checkout', branch]
            utils_setup.run_cmd(cmd, cwd=_dst)

    return _dst

# Return the layer specific XML directory.  The XML directory
# lives inside of the mirror path.  If the mirror directory does
# not already exist it is created by callign get_mirror_dir
#
# This function will return None if the layer is to be skipped.
def get_xml_dir(_layer, _mirror):
    _mirror = get_mirror_dir(_layer, _mirror)
    if _mirror:
        return os.path.join(_mirror, 'xml')
    return _mirror

# Process and transform the specified XML files.  Return a list of
# project names referenced by this XML file.
#
# If the _dest is None, we still process the XML layer, but we never
# write out a result.  This is necessary to parse the components owned
# by the xml file so we know to skip them...
def transform_xml(_src, _dest):
    logger.plain('Processing %s' % _src)
    if not os.path.exists(_src):
        logger.warning('Not found %s' % _src)
        return []

    if _dest:
        os.makedirs(os.path.dirname(_dest), exist_ok=True)
        with open(_src, 'rt') as fin, open(_dest, 'wt') as fout:
            return transform_xml_inside(fin, fout)
    else:
        with open(_src, 'rt') as fin:
            return transform_xml_inside(fin, None)

def transform_xml_inside(_fin, _fout):
    result = []

    for _line in _fin:
        modified = False
        try:
            _root = ET.fromstring(_line)
        except:
            logger.warning('exception on: %s' % _line)
            if _fout:
                _fout.write('%s' % _line)
            continue

        # Skip linkfiles, don't warn.. we know these are valid
        if _root.tag == 'linkfile':
            if _fout:
                _fout.write('%s' % _line)
            continue

        if _root.tag != 'project':
            logger.warning('Not project: %s' % _line)
            if _fout:
                _fout.write('%s' % _line)
            continue

        for attrib in _root.attrib:
            if attrib == 'name':
                result.append(_root.attrib['name'])
                if _root.attrib['name'] != _root.attrib['name'].split('/')[-1]:
                    _root.attrib['name'] = _root.attrib['name'].split('/')[-1]
                    modified = True

        for _child in _root:
            for attrib in _child.attrib:
                if attrib == 'name':
                    result.append(_child.attrib['name'])
                    if _child.attrib['name'] != _child.attrib['name'].split('/')[-1]:
                        _child.attrib['name'] = _child.attrib['name'].split('/')[-1]
                        modified = True

        if _fout:
            if modified:
                _fout.write('    %s\n' % (ET.tostring(_root, encoding='unicode')))
            else:
                _fout.write('%s' % _line)

    return result

# Process the mirrors and add any new files to the git repo
def update_mirror(_dst_mirror):
    cmd = ['git', 'add', '-A', '.']
    utils_setup.run_cmd(cmd, cwd=_dst_mirror)

    logger.debug('Updating mirror-index')
    cmd = ['git', 'commit', '-m', 'Updated index - Flatten Mirror']
    try:
        utils_setup.run_cmd(cmd, cwd=_dst_mirror, log=2)
    except:
        # Nothing changed...
        pass

def copy_premirrors_dl(dest):
    premirrors_dl = "premirrors-dl/downloads/"
    if os.path.exists(premirrors_dl):
        logger.plain("Copying %s" % premirrors_dl)
    else:
        return
    cmd = "cp --parent -a".split()
    if os.stat(premirrors_dl).st_dev == os.stat(dest).st_dev:
        # Hard link when possible
        cmd.append("-l")
    cmd += [premirrors_dl, dest]
    utils_setup.run_cmd(cmd)

# This assumes variables 'dest', 'git_push', 'subset_file' and
# 'setup_dir' is globally set.
def main():
    global subset_folders
    global branch

    if subset_file:
        subset_folders = {}
        with open(subset_file, 'rt') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                lsplit = line.split()
                if len(lsplit) == 0:
                    continue
                if len(lsplit) != 2:
                    logger.critical("Subset Folders, invalid line: %s" % (line))
                    return 1
                subset_folders[lsplit[0]] = lsplit[1]

    if os.path.exists(dest):
        logger.critical('Destination directory %s already exists.  Please choose a different destination.' % (dest))
        return 1

    # We have to run this against a mirror, check for a mirror-index
    mirror_path = 'mirror-index'
    if not os.path.exists(mirror_path):
        logger.critical('No %s found.  Is this a mirror?' % mirror_path)
        return 1

    dst_base_mirror = os.path.join(dest, mirror_path)

    # Find the base branch of the mirror-index to set a default
    cmd = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
    _ret = subprocess.Popen(cmd, cwd=mirror_path, close_fds=True, stdout=subprocess.PIPE)
    branch = ""
    output = ""
    while True:
        output = _ret.stdout.readline()
        if not output and _ret.poll() is not None:
            break
        branch += output.decode('utf-8')
    _ret.wait()
    branch = branch.strip()

    if not branch or branch == "":
        logger.critical('Unable to determine base branch.')
        return 1

    # Create the destination
    os.makedirs(dest, exist_ok=False)

    #### Load the index and create a list of things we need to parse

    # this is the list of things that MAY be in the default.xml file, we need
    # to have a list to later process that file and exclude things we've already
    # done.
    processed_list = []

    ### Create the target mirror-index...
    # Transform and export the mirror index
    logger.plain('Transforming index...')

    index = Layer_Index(indexcfg=settings.INDEXES, base_branch=branch, replace=settings.REPLACE, mirror=mirror_path)

    branchid = -1
    base_branch = branch
    bitbake_branch = branch
    for lindex in index.index:
        if 'CFG' in lindex:
            base_branch = lindex['CFG']['BRANCH']
            bitbake_branch = branch

        for b in lindex['branches']:
            if 'name' in b and b['name'] == base_branch:
                branchid = b['id']
                if 'bitbake_branch' in b and b['bitbake_branch'] != "":
                    bitbake_branch = b['bitbake_branch']
                break

        logger.info('Discovered base_branch: %s (%s)' % (base_branch, branchid))
        logger.info('Discovered bitbake_branch: %s' % bitbake_branch)

        for layer in lindex['layerItems']:
            logger.info('Processing layer %s...' % layer['name'])

            # Identify, manipulate and copy the layer...
            if 'vcs_url' in layer:
                full_url = layer['vcs_url'].replace('#BASE_URL#/', '')
                base_url = layer['vcs_url'].split('/')[-1]

                layer['vcs_url'] = '#BASE_URL#' + '/' + base_url
                layer['vcs_web_url'] = ''
                layer['vcs_web_tree_base_url'] = ''
                layer['vcs_web_file_base_url'] = ''
                layer['mailing_list_url'] = ''

                # Find actual_branch if one is there
                revision = base_branch
                for lb in lindex['layerBranches']:
                    if lb['branch'] == branchid and lb['layer'] == layer['id']:
                        if lb['actual_branch'] != "":
                            revision = lb['actual_branch']

                src = full_url
                dst = os.path.join(dest, os.path.basename(src))

                if src not in processed_list:
                    push_or_copy(layer['name'], src, dst, revision)
                    processed_list.append(src)

            xml_dir = get_xml_dir(layer['name'], dst_base_mirror)

            def xml_dest_dir(_xml_dir, _name):
                if not _xml_dir:
                    return None
                return os.path.join(_xml_dir, _name)

            src = os.path.join(mirror_path, 'xml', '%s.inc' % layer['name'])
            if os.path.exists(src):
                xml_dst = xml_dest_dir(xml_dir, '%s.inc' % layer['name'])
                for name in transform_xml(src, xml_dst):
                    dst = os.path.join(dest, os.path.basename(name))
                    if name not in processed_list:
                        push_or_copy(layer['name'], name, dst)
                        processed_list.append(name)

            src = os.path.join(mirror_path, 'xml', '%s.xml' % layer['name'])
            if os.path.exists(src):
                xml_dst = xml_dest_dir(xml_dir, '%s.xml' % layer['name'])
                for name in transform_xml(src, xml_dst):
                    dst = os.path.join(dest, os.path.basename(name))
                    if name not in processed_list:
                        push_or_copy(layer['name'], name, dst)
                        processed_list.append(name)

            # OpenEmbedded-Core is a bit unique.  There are a few items
            # that need to be grouped by this subset entry, these are
            # items NOT included in the index or default.xml
            #
            #   wrlinux-x
            #   git-repo
            #   bitbake
            if layer['name'] == 'openembedded-core':
                # wrlinux-x (or whatever it's called) convert to bare using .git
                src = os.path.join(setup_dir, '.git')
                dst = os.path.join(dest, os.path.basename(setup_dir))
                if src not in processed_list:
                    push_or_copy(layer['name'], src, dst, branch)
                    processed_list.append(src)

                # git-repo
                src = os.path.join(os.path.dirname(full_url), 'git-repo')
                dst = os.path.join(dest, os.path.basename(src))
                if src not in processed_list:
                    push_or_copy(layer['name'], src, dst)
                    processed_list.append(src)

                # bitbake
                src = os.path.join(os.path.dirname(full_url), 'bitbake')
                dst = os.path.join(dest, os.path.basename(src))
                if src not in processed_list:
                    push_or_copy(layer['name'], src, dst, bitbake_branch)
                    processed_list.append(src)

                src = os.path.join(mirror_path, 'xml', 'bitbake.inc')
                if os.path.exists(src):
                    xml_dst = xml_dest_dir(xml_dir, 'bitbake.inc')
                    for name in transform_xml(src, xml_dst):
                        dst = os.path.join(dest, os.path.basename(name))
                        if name not in processed_list:
                            push_or_copy(layer['name'], name, dst)
                            processed_list.append(name)

                src = os.path.join(mirror_path, 'xml', 'bitbake.xml')
                if os.path.exists(src):
                    xml_dst = xml_dest_dir(xml_dir, 'bitbake.xml')
                    for name in transform_xml(src, xml_dst):
                        dst = os.path.join(dest, os.path.basename(name))
                        if name not in processed_list:
                            push_or_copy(layer['name'], name, dst)
                            processed_list.append(name)

        # dst_base_mirror may not exist if we're subsetting...
        os.makedirs(dst_base_mirror, exist_ok=True)
        index.serialize_index(lindex, os.path.join(dst_base_mirror, lindex['CFG']['DESCRIPTION']), split=True, IncludeCFG=True, mirror=True, base_url=base_url)

        # Since serialize can't subset, we do it manually...
        # if the rules change in layer_index.py, adjust them here..
        if subset_folders:
            base_branch = branch
            if 'CFG' in lindex:
                base_branch = lindex['CFG']['BRANCH']

            for layer in lindex['layerItems']:
                json = "%s__%s__%s.json" % (lindex['CFG']['DESCRIPTION'], base_branch, layer['name'])
                json = json.translate(str.maketrans('/ ', '__'))

                src = os.path.join(dst_base_mirror, json)
                mirror_dir = get_mirror_dir(layer['name'], dst_base_mirror)
                if not mirror_dir:
                    # Skipped item, remove it and continue
                    logger.plain('rm %s' % src)
                    os.remove(src)
                    continue
                dst = os.path.join(mirror_dir, json)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                logger.plain('mv %s -> %s' % (src, dst))
                os.rename(src, dst)

            # Directory is expected to be empty, remove it.
            os.rmdir(dst_base_mirror)

    #### Now process anythign else we've not yet processed
    logger.info('Processing left-overs...')

    # Now process the default.xml, and process anything not previous processed...
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

        if src in processed_list or src + '.git' in processed_list:
            continue

        dst = os.path.join(dest, os.path.basename(src))

        revision = None
        if not ('bare' in child.attrib and child.attrib['bare'] == 'True'):
            revision = default_revision
            if 'revision' in child.attrib:
                revision = child.attrib['revision']

        push_or_copy(os.path.basename(src), src, dst, revision)

    #### Update the mirror-index repositories (git add/git commit)
    logger.plain('Updating mirror-index repositories...')

    # git add file.
    if subset_folders:
        index_list = []
        for layer in subset_folders:
            if subset_folders[layer] == "[SKIP]":
                continue
            dst_mirror = get_mirror_dir(layer, dst_base_mirror)
            if dst_mirror not in index_list:
                index_list.append(dst_mirror)

        for dst_mirror in index_list:
            update_mirror(dst_mirror)
    else:
        update_mirror(dst_base_mirror)

    copy_premirrors_dl(dest)

    logger.plain('Done')
    return 0


# Define globals
if __name__ == '__main__':
    logger = logger_setup.setup_logging()
    dest, git_push, subset_file, strip_git = config_args(sys.argv[1:])

    subset_folders = None
    branch = None

    setup_dir = os.path.dirname(os.path.dirname(sys.argv[0]))

    ret = main()
    sys.exit(ret)
