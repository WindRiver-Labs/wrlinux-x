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
import sys

import logger_setup

import utils_setup

logger = logger_setup.setup_logging()
class Windshare():
    def __init__(self, debug=0):
        self.folders = None
        self.indexes = {}
        self.xmls = {}
        self.debug = debug

        # This is only used if we want to instruct the system to ask the user
        # for credentials, if a better credential manager is not available.
        self.interactive = 0

    def get_windshare_urls(self, base_url):
        from urllib.parse import urlsplit, urlunsplit

        (uscheme, uloc, upath, uquery, ufragid) = urlsplit(base_url)

        # What folder are we in?
        ws_base_folder = os.path.basename(upath)

        logger.debug('Product base folder = %s' % ws_base_folder)

        if not ws_base_folder or ws_base_folder == "":
            # Invalid URL
            logger.debug('Invalid base folder, not Windshare.')
            return (None, None, None)

        # Folder root is one directory higher then the base_url
        upath = os.path.dirname(upath)
        ws_base_url = urlunsplit((uscheme, uloc, upath, uquery, ufragid))

        if uscheme and (uscheme != "http" and uscheme != "https"):
            logger.debug('Scheme (%s) not valid for Windshare.' % uscheme)
            return (None, None, None)

        # Magic URL to the entitlement file
        ws_entitlement_url = ws_base_url + '/wrlinux-9.json'

        logger.debug('Entitlement url %s' % ws_entitlement_url)

        # If no uscheme, this is file access, check here if an entitlement
        # file exists.  If not, we know we're not windshare.
        if not uscheme and not os.path.exists(ws_entitlement_url):
            logger.debug('Local file path, file does not exist.  Not a Windshare install.')
            return (None, None, None)

        return (ws_base_url, ws_base_folder, ws_entitlement_url)

    def load_folders(self, url=None):
        assert url is not None

        def _get_json_response(wsurl=None, retry=True):
            assert wsurl is not None

            from urllib.parse import urlparse

            up = urlparse(wsurl)
            if not up.scheme:
                # Check for it on the disk...
                if os.path.exists(wsurl):
                    parsed = json.load(open(wsurl, 'rt', encoding='utf-8'))
                else:
                    return None
            else:
                # Go out to the network...
                res = utils_setup.fetch_url(wsurl, debuglevel=self.debug, interactive=self.interactive)

                try:
                    result = res.read().decode('utf-8')
                except ConnectionResetError:
                    if retry:
                        logger.debug("%s: Connection reset by peer.  Retrying..." % wsurl)
                        result = _get_json_response(wsurl=wsurl, retry=False)
                        logger.debug("%s: retry successful." % wsurl)
                    else:
                        logger.critical("%s: Connection reset by peer." % wsurl)
                        logger.critical("Is there a firewall blocking your connection?")
                        sys.exit(1)

                logger.debug('Result:\n%s' % result)
                parsed = json.loads(result)

            return parsed

        try:
            from urllib.request import URLError

            entitlement = _get_json_response(url)

            if entitlement and 'dataFolderTrueFolders' in entitlement:
                self.folders = entitlement['dataFolderTrueFolders']
            else:
                return False
        except URLError as e:
            # Authentication failure, we need to stop now.
            if hasattr(e, 'code') and e.code == 401:
                sys.exit(1)
            return False
        except Exception as e:
            logger.debug('Unable to fetch entitlement: %s (%s)' % (type(e), e))
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

        # We need access to the sortRestApi function...
        from layer_index import Layer_Index
        li = Layer_Index()

        # We want to move to a generic named branch, now that we've done the fixups.
        try:
            cmd = [setup.tools['git'], 'checkout', '--orphan', setup.base_branch ]
            utils_setup.run_cmd(cmd, environment=setup.env, cwd=mirror_index_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            cmd = [setup.tools['git'], 'checkout', setup.base_branch ]
            utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path)
            cmd = [setup.tools['git'], 'reset', '--hard' ]
            utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path)

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
        utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path)

        try:
            cmd = [setup.tools['git'], 'diff-index', '--quiet', 'HEAD', '--']
            utils_setup.run_cmd(cmd, environment=setup.env, cwd=mirror_index_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # We expect to fail to this code
            logger.debug('Updating windshare mirror-index')
            cmd = [setup.tools['git'], 'commit', '-m', 'Updated index - %s' % (setup.setup_args)]
            utils_setup.run_cmd(cmd, log=2, environment=setup.env, cwd=mirror_index_path)

