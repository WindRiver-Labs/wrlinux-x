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

# The windshare distribution mechanism has unique requirements for dividing
# the components into specific entitled sections.  We need to take these
# 'folders' and reconstruct the related items (mirror-index, xml files, etc)
# into a flat view that works like a regular mirror would.

import json
import xml.etree.ElementTree as ET

import os

import logger_setup

import utils_setup

logger = logger_setup.setup_logging()
class Windshare():
    def __init__(self):
        self.folders = None
        self.indexes = {}
        self.xmls = {}

    def get_windshare_urls(self, base_url):
        # Folder root is one directory higher then the base_url
        ws_base_url = "/".join(base_url.split('/')[:-1])

        # What folder are we in?
        ws_base_folder = base_url.split('/')[-1]

        # Magic URL to the entitlement file
        # TODO: Get the REAL url...
        # We may have to do additional processing if this is file or web based...
        ws_entitlement_url = ws_base_url + '/wrlinux-9.json'

        logger.debug("Windshare URLs: %s %s %s" % (ws_base_url, ws_base_folder, ws_entitlement_url))
        return (ws_base_url, ws_base_folder, ws_entitlement_url)

    def load_folders(self, url=None):
        assert url is not None

        def _get_json_response(wsurl=None):
            assert wsurl is not None

            from urllib.parse import urlparse

            up = urlparse(wsurl)
            if not up.scheme:
                # Check for it on the disk...
                if os.path.exists(wsurl):
                    parsed = json.load(open(path, 'rt', encoding='utf-8'))
                else:
                    return None
            else:
                # Go out to the network...
                res = utils_setup.fetch_url(wsurl)
                parsed = json.loads(res.read().decode('utf-8'))

            return parsed

        try:
            entitlement = _get_json_response(url)

            if entitlement and 'dataFolderTrueFolders' in entitlement:
                self.folders = entitlement['dataFolderTrueFolders']
            else:
                return False
        except Exception as e:
            logger.debug('Unable to fetch entitlement: %s' % e)
            return False

        return True

    # Note base_url is _NOT_ setup.base_url, it is the root of the folders dir
    def load_mirror_index(self, setup, base_url, folder):
        mirror_index_path = setup.load_mirror_index(base_url + '/' + folder + '/mirror-index', folder=folder + "_")
        if not mirror_index_path:
            raise Exception("Unable to load mirror index %s." % (base_url + '/' + folder + '/mirror-index'))

        # Mirror index returns with the fetched item checked out...
        #cmd = [setup.tools['git'], 'checkout', folder + "_" + setup.base_branch ]
        #utils_setup.run_cmd(cmd, environment=setup.env, cwd=mirror_index_path)

        for (dirpath, _, filenames) in os.walk(mirror_index_path):
            if dirpath.endswith('/.git') or '/.git/' in dirpath:
                continue
            for filename in filenames:
                if filename.endswith('.json'):
                    try:
                        (_, _, jlayer) = filename[:-5].split('__')
                    except:
                        raise Exception('Unable to parse windshare json file %s (%s).' % (filename, folder + "_" + setup.base_branch))

                    path = os.path.join(dirpath, filename)
                    pindex = json.load(open(path, 'rt', encoding='utf-8'))

                    if 'layerItems' in pindex:
                        newItems = []
                        for entry in pindex['layerItems']:
                            # Verify this is the jlayer, otherwise remove it as it won't be in this folder!
                            if entry['name'] != jlayer:
                                continue
                            entry['vcs_url'] = entry['vcs_url'].replace('#BASE_URL#', '#BASE_URL#' + '/' + folder)
                            newItems.append(entry)
                        pindex['layerItems'] = newItems

                    self.indexes[filename] = pindex

                elif filename.endswith('.xml') or filename.endswith('.inc'):
                    self.xmls[filename] = []
                    path = os.path.join(dirpath, filename)

                    # Prefix the <project name= entries with the folder/
                    with open(path, 'rt') as fin:
                        for _line in fin:
                            _line = _line.rstrip()
                            try:
                                _root = ET.fromstring(_line)
                            except Exception:
                                logger.warning('Unable to parse XML %s: %s' % (filename, _line))
                                self.xmls[filename].append(_line)
                                continue

                            if _root.tag != 'project':
                                self.xmls[filename].append(_line)
                                continue

                            for attrib in _root.attrib:
                                if attrib == 'name':
                                    _root.attrib['name'] = folder + '/' + _root.attrib['name']

                            for _child in _root:
                                for attrib in _child.attrib:
                                    if attrib == 'name':
                                        _child.attrib['name'] = folder + '/' + _child.attrib['name']

                            self.xmls[filename].append(ET.tostring(_root, encoding='unicode'))
                else:
                    logger.warning('When processing Windshare mirror index, Unexpected file %s...' % filename)

        return mirror_index_path

    def write_local_mirror_index(self, setup, mirror_index_path):
        import subprocess
        import utils_setup

        # We need access to the sortRestApi function...
        from layer_index import Layer_Index
        li = Layer_Index()

        # We want to move to a generic named branch, now that we've done the fixups.
        try:
            cmd = [setup.tools['git'], 'checkout', '--orphan', setup.base_branch ]
            utils_setup.run_cmd(cmd, environment=setup.env, cwd=mirror_index_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            cmd = [setup.tools['git'], 'checkout', setup.base_branch ]
            utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path, stderr=subprocess.PIPE)
            cmd = [setup.tools['git'], 'reset', '--hard' ]
            utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path, stderr=subprocess.PIPE)

        # Remove obsolete entries only
        for (dirpath, _, filenames) in os.walk(mirror_index_path):
            if dirpath.endswith('/.git') or '/.git/' in dirpath:
                continue
            for filename in filenames:
                if filename not in self.indexes and filename not in self.xmls:
                    logger.debug('ws mirror-index remove obsolete %s' % os.path.join(dirpath, filename))
                    os.remove(os.path.join(dirpath, filename))

        for entry in self.indexes:
            logger.debug('Writing windshare index %s...' % entry)
            fpath = os.path.join(mirror_index_path, entry)
            json.dump(li.sortRestApi(self.indexes[entry]), open(fpath, 'wt'), indent=4)

        for entry in self.xmls:
            logger.debug('Writing windshare xml %s...' % entry)
            os.makedirs(os.path.join(mirror_index_path, 'xml'), exist_ok=True)
            fpath = os.path.join(mirror_index_path, 'xml', entry)
            with open(fpath, 'wt') as fout:
                for _line in self.xmls[entry]:
                    fout.write(_line + '\n')

        cmd = [setup.tools['git'], 'add', '-A', '.']
        utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path, stderr=subprocess.PIPE)

        try:
            cmd = [setup.tools['git'], 'diff-index', '--quiet', 'HEAD', '--']
            utils_setup.run_cmd(cmd, environment=setup.env, cwd=mirror_index_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # We expect to fail to this code
            logger.debug('Updating windshare mirror-index')
            cmd = [setup.tools['git'], 'commit', '-m', 'Updated index - %s' % (setup.setup_args)]
            utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path, stderr=subprocess.PIPE)

