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

# Please keep these sorted.
import logging
import os
import shutil
import subprocess
import sys
import time

import utils_setup

# Setup-specific modules
import logger_setup
from argparse_wrl import Argparse_Wrl

from layer_index import Layer_Index

import settings

logger = logger_setup.setup_logging()

# Redirect stdout and stderr to the custom logger.  This allows us to use
# python modules that may output only via stdout/stderr.
sys.stdout = logger_setup.LoggerOut(logger.info)
sys.stderr = logger_setup.LoggerOut(logger.error)

class Setup():

    tool_list = ['repo', 'git']

    default_xml = 'default.xml'
    default_repo_quiet = '--quiet'

    class_config_dir = 'config'
    class_log_dir = 'log'

    check_repo_install_dir = '.repo/repo/.git'
    check_repo_sync_file = '.repo/projects/'

    replacement = {}

    BINTOOLS_SSL_DIR="/bin/buildtools/sysroots/x86_64-wrlinuxsdk-linux/usr/share/ca-certificates/mozilla"
    BINTOOLS_SSL_CERT= "/bin/buildtools/sysroots/x86_64-wrlinuxsdk-linux/etc/ssl/certs/ca-certificates.crt"

    def __init__(self):
        # Set various default values
        # Default -j for repo init
        self.jobs = str(settings.REPO_JOBS)

        # Pull in the defaults from the environment (set by setup.sh)
        self.base_url = os.getenv('OE_BASEURL')
        self.base_branch = os.getenv('OE_BASEBRANCH')
        self.buildtools_branch = os.getenv('OE_BUILDTOOLS_BRANCH')
        self.buildtools_remote = os.getenv('OE_BUILDTOOLS_REMOTE')

        # Real project or a mirror?
        self.mirror = False

        # Default configuration
        self.distros = [ settings.DEFAULT_DISTRO ]
        self.machines = [ settings.DEFAULT_MACHINE ]
        self.layers = []
        self.recipes = []
        self.wrtemplates = []
        self.kernel = settings.DEFAULT_KTYPE

        self.all_layers = False
        self.dl_layers = False

        self.no_recommend = False

        self.no_network = False
        self.allowed_network = None

        self.remotes = {}
        self.requiredlayers = []
        self.recommendedlayers = []

        # Default quiet:
        self.quiet = self.default_repo_quiet
        self.repo_verbose = False

        # Default depth
        self.depth = None

        # Default to NOT force-sync
        self.force_sync = None

        self.debug_lvl = 0

        # Set the install_dir
        # Use the path from this file.  Note bin has to be dropped.
        self.install_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')

        # Default location for the related XML files
        self.xml_dir = os.path.join(self.install_dir, 'data/xml')

        # Set the directory where we're running.
        self.project_dir = os.getcwd()

        self.conf_dir = os.path.join(self.project_dir, self.class_config_dir)


        # Environment setup
        self.env = os.environ.copy()
        self.setup_env()

        # Check for all the tools and create a dictionary of the path
        self.tools = {i : self.get_path(i) for i in self.tool_list}

        # Config flags
        self.list_distros = False
        self.list_machines = False
        self.list_layers = False
        self.list_recipes = False
        self.list_wrtemplates = False

    def exit(self, ret=0):
        logger.debug("setup.py finished (ret=%s)" % (ret))
        sys.exit(ret)

    def start_file_logging(self):
        log_dir = os.path.join(self.conf_dir, self.class_log_dir)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = '%s/%s.log' % (log_dir, time.strftime('%Y-%m-%d-%H:%M:%S+0000', time.gmtime()))
        logger_setup.setup_logging_file(log_file)

    def main(self, orig_args):
        parser = Argparse_Wrl(self)
        # We want to default to help mode lacking any args.
        if not orig_args or not orig_args[1:]:
            orig_args.append('--help')
        parser.evaluate_args(orig_args[1:])
        self.setup_args = " ".join(orig_args[1:])

        self.start_file_logging()
        if not self.base_url:
            logger.error('Unable to determine base url, you may need to specify --base-url=')

        if not self.base_branch:
            logger.error('Unable to determine base branch, you may need to specify --base-branch=')

        if not self.base_url or not self.base_branch:
            self.exit(1)

        self.load_layer_index()

        if self.list_distros:
            self.index.list_distros(self.base_branch)

        if self.list_machines:
            self.index.list_machines(self.base_branch)

        if self.list_layers:
            self.index.list_layers(self.base_branch)

        if self.list_recipes:
            self.index.list_recipes(self.base_branch)

        if self.list_wrtemplates:
            self.index.list_wrtemplates(self.base_branch)

        if self.list_distros or self.list_machines or self.list_layers or self.list_recipes or self.list_wrtemplates:
            sys.exit(0)

        logger.debug('setup.py started')
        logger.debug('Calling setup main with arguments %s' % str(orig_args))

        # Log debug which may have been missed due to log level.
        logger.debug("PATH=%s" % self.env["PATH"])

        logger.debug("Tools are:")
        for key in self.tools:
            logger.debug("%s -> %s" % (key, self.tools[key]))

        logger.plain('Setting distro to "%s"' % (",".join(self.distros)))
        logger.plain('Setting machine to "%s"' % (",".join(self.machines)))
        if self.layers != []:
            logger.plain('Setting layers to "%s"' % (",".join(self.layers)))
        if self.recipes != []:
            logger.plain('Setting recipes to "%s"' % (",".join(self.recipes)))
        if self.wrtemplates != []:
            logger.plain('Setting templates to "%s"' % (",".join(self.wrtemplates)))

        self.process_layers()

        self.project_setup()

        self.__prep_replacements()
        if self.mirror != True:
            # We only want to do this if we're not mirroring...
            self.update_project()
        else:
            # Setup an index for others to use if we're mirroring...
            self.update_mirror()
            self.update_mirror_index()

        self.update_manifest()

        self.update_gitignore()

        self.commit_files()

        self.repo_sync()

        self.exit(0)

    def load_mirror_index(self, remote_mirror, folder=""):
        # See if there is a mirror index available from the BASE_URL
        mirror_index = os.path.join(self.conf_dir, 'mirror-index')
        try:
            cmd = [self.tools['git'], 'ls-remote', remote_mirror, self.base_branch]
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=self.project_dir, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            try:
                remote_mirror += "/.git"
                cmd = [self.tools['git'], 'ls-remote', remote_mirror, self.base_branch]
                utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=self.project_dir, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            except:
                # No mirror, return
                return None

        logger.plain('Loading the mirror index from %s (%s)...' % (remote_mirror, self.base_branch))
        # This MIGHT be a valid mirror..
        if not os.path.exists(mirror_index):
            os.makedirs(mirror_index)
            cmd = [self.tools['git'], 'init' ]
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=mirror_index)

        try:
            cmd = [self.tools['git'], 'fetch', '-f', '-n', '-u', remote_mirror, self.base_branch + ':' + folder + self.base_branch]
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=mirror_index)
        except:
            # Could not fetch, return
            return None

        logger.debug('Found mirrored index.')
        cmd = [self.tools['git'], 'checkout', folder + self.base_branch ]
        utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=mirror_index)
        cmd = [self.tools['git'], 'reset', '--hard' ]
        utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=mirror_index)

        return mirror_index


    def load_layer_index(self):
        # Load Layer_Index

        mirror_index_path = None

        from windshare import Windshare
        ws = Windshare(debug=self.debug_lvl)

        # Determine if this is a windshare install
        (ws_base_url, ws_base_folder, ws_entitlement_url) = ws.get_windshare_urls(self.base_url)
        if ws_base_url and ws_base_url != "" and ws.load_folders(ws_entitlement_url):
            logger.plain('Detected Windshare configuration.  Processing entitlements and indexes.')

            for folder in ws.folders:
                mirror_index_path = ws.load_mirror_index(self, ws_base_url, folder)

            ws.write_local_mirror_index(self, mirror_index_path)

            # We need to adjust the base_url so everything works properly...
            self.base_url = ws_base_url

            # Adjust the location of the buildtools (was based on the original base_url)
            if self.buildtools_remote:
                self.buildtools_remote = ws_base_folder + '/' + self.buildtools_remote
        else:
            logger.debug('No Windshare configuration detected.')

        # Check if we have a mirror-index, and load it if we do...
        if not mirror_index_path:
            mirror_index_path = self.load_mirror_index(self.base_url + '/mirror-index')

        # Mirror also has a copy of the associated XML bits
        if mirror_index_path:
            self.xml_dir = os.path.join(mirror_index_path, 'xml')

        # Setup replace strings as late as possible.  The various self.* values
        # may be modified prior to this place.
        replace = []
        replace = replace + settings.REPLACE
        replace = replace + [
                   ( '#INSTALL_DIR#', self.install_dir ),
                   ( '#BASE_URL#', self.base_url ),
                   ( '#BASE_BRANCH#', self.base_branch ),
                  ]

        self.index = Layer_Index(indexcfg=settings.INDEXES, base_branch=self.base_branch, replace=replace, mirror=mirror_index_path)

    def process_layers(self):
        from collections import deque

        # We allow duplicates in the queue, they're filtered later
        # Queue of required objects
        requiredQueue = deque([])
        # Queue of recommended objects
        recommendedQueue = deque([])

        logger.debug('Starting')
        # if this switches to false, we have to exit at the end of this function
        allfound = True

        # It all starts with BASE_LAYERS, so always include this. (only from index 0)
        lindex = self.index.index[0]
        branchid = self.index.getBranchId(lindex, self.get_branch(lindex=lindex))
        if branchid:
            for lname in settings.BASE_LAYERS.split():
                base_layerBranch = self.index.getLayerBranch(lindex, branchid, name=lname)

                if not base_layerBranch or not branchid:
                    raise Exception('Unable to find base layer: %s in the Layer_Index' % (lname))

                for lb in base_layerBranch:
                    requiredQueue.append( (lindex, lb) )

        # process the configuration arguments (find the layers we need for the project)
        # if an item is 'layer:item', then the 'foo' part must match a layer name.
        def procConfig(layer=None, distro=None, machine=None, recipe=None, wrtemplate=None):
            item = ["", layer][layer != None]
            item = item + ["", distro][distro != None]
            item = item + ["", machine][machine != None]
            item = item + ["", recipe][recipe != None]
            item = item + ["", wrtemplate][wrtemplate != None]

            type = ["", 'layer'][layer != None]
            type = type + ["", 'distro'][distro != None]
            type = type + ["", 'machine'][machine != None]
            type = type + ["", 'recipe'][recipe != None]
            type = type + ["", 'template'][wrtemplate != None]

            if (':' in item):
                # User told us which layer, so ignore the other bits -- they can be used later...
                layer = item.split(':')[0]
                distro = None
                machine = None
                recipe = None
                wrtemplate = None

            # TODO: We do not actually verify the item we asked for (if a layer was specified) is available
            found = False
            for lindex in self.index.index:
                branchid = self.index.getBranchId(lindex, self.get_branch(lindex=lindex))
                if not branchid:
                    continue
                for layerBranch in self.index.getLayerBranch(lindex, branchid, name=layer, distro=distro, machine=machine, recipe=recipe, wrtemplate=wrtemplate) or []:
                    requiredQueue.append( (lindex, layerBranch) )
                    found = True
                if found:
                    break

            if not found:
                logger.critical('%s "%s" not found' % (type, item))
                return False

            return True

        for l in self.layers:
            if not procConfig(layer=l):
                allfound = False

        for l in self.distros:
            if not procConfig(distro=l):
                allfound = False

        for l in self.machines:
            if not procConfig(machine=l):
                allfound = False

        for l in self.recipes:
            if not procConfig(recipe=l):
                allfound = False

        for l in self.wrtemplates:
            if not procConfig(wrtemplate=l):
                allfound = False

        # Add all layers -- if necessary
        if self.all_layers == True:
            for lindex in self.index.index:
                branchid = self.index.getBranchId(lindex, self.get_branch(lindex=lindex))
                if not branchid:
                    continue
                for l in lindex['layerItems']:
                    for layerBranch in self.index.getLayerBranch(lindex, branchid, layerItem=l) or []:
                        # dl layers are always added as recommends in an --all-layers mode
                        if '-dl-' in l['name'] or l['name'].endswith('-dl'):
                            recommendedQueue.append( (lindex, layerBranch) )
                        else:
                            requiredQueue.append( (lindex, layerBranch) )

        if not allfound:
            logger.critical('Please correct the missing items, exiting.')
            self.exit(1)

        # Compute requires and recommended layers...

        # List of 'collection' and layer 'name'.  This list is used to avoid
        # including duplicates.  Collection is matched first, then name -- as not
        # all layer indexes may contain 'collection'
        depCacheCol = []
        depCacheName = []

        def checkCache(lindex, layerBranch, addCache=False):
            (collection, name, vcs_url) = self.index.getLayerInfo(lindex, layerBranch=layerBranch)

            if collection in depCacheCol or name in depCacheName:
                return True

            if addCache:
                if collection:
                    depCacheCol.append(collection)
                if name:
                    depCacheName.append(name)
            return False

        def resolveIndexOrder(lindex, layerBranch, Queue):
            # We want to recompute the dependency in INDEXES order...
            (collection, name, vcs_url) = self.index.getLayerInfo(lindex, layerBranch)
            found = False
            for pindex in self.index.index:
                # We already know it'll be in this index, so we just use it as-is...
                if pindex == lindex:
                    break

                # Look for the collection (or name if no collection) in the indexes in
                # priority order...
                pbranchid = self.index.getBranchId(pindex, self.get_branch(lindex=pindex))
                if collection:
                    new_layerBranches = self.index.getLayerBranch(pindex, pbranchid, collection=collection)
                    if new_layerBranches and new_layerBranches != []:
                        for lb in new_layerBranches:
                            logger.info('Resolving dependency %s from %s to %s from %s' % (name, lindex['CFG']['DESCRIPTION'], name, pindex['CFG']['DESCRIPTION']))
                            Queue.append( (pindex, lb) )
                        lindex = None
                        layerBranch = None
                        break

                if name:
                    new_layerBranches = self.index.getLayerBranch(pindex, pbranchid, name=name)
                    if new_layerBranches and new_layerBranches != []:
                        for lb in new_layerBranches:
                            logger.info('Resolving dependency %s from %s to %s from %s' % (name, lindex['CFG']['DESCRIPTION'], name, pindex['CFG']['DESCRIPTION']))
                            Queue.append( (pindex, lb) )
                        lindex = None
                        layerBranch = None
                        break

            return (lindex, layerBranch)

        while requiredQueue:
            (lindex, layerBranch) = requiredQueue.popleft()

            (lindex, layerBranch) = resolveIndexOrder(lindex, layerBranch, requiredQueue)

            if not lindex or not layerBranch:
                continue

            if not checkCache(lindex, layerBranch, True):
                self.requiredlayers.append( (lindex, layerBranch) )
                (required, recommended) = self.index.getDependencies(lindex, layerBranch)
                for dep in required:
                    requiredQueue.append( (lindex, dep) )

                for dep in recommended:
                    recommendedQueue.append( (lindex, dep) )

        while recommendedQueue:
            (lindex, layerBranch) = recommendedQueue.popleft()

            (lindex, layerBranch) = resolveIndexOrder(lindex, layerBranch, recommendedQueue)

            if not lindex or not layerBranch:
                continue

            if not checkCache(lindex, layerBranch, True):
                if self.dl_layers != True:
                    layers = self.index.find_layer(lindex, id=layerBranch['layer'])
                    if layers and ('-dl-' in layers[0]['name'] or layers[0]['name'].endswith('-dl')):
                        # Skip the download layer
                        continue
                self.recommendedlayers.append( (lindex, layerBranch) )
                (required, recommended) = self.index.getDependencies(lindex, layerBranch)
                for dep in required + recommended:
                    recommendedQueue.append( (lindex, dep) )

        # Also compute the various remotes
        from urllib.parse import urlparse

        self.remotes['base'] = self.base_url

        def process_remote(lindex, layerBranch):
            for layer in self.index.find_layer(lindex, id=layerBranch['layer']):
                vcs_url = layer['vcs_url']

                found = False
                for remote in self.remotes:
                    if vcs_url.startswith(self.remotes[remote]):
                        found = True
                        break
                if not found:
                    url = urlparse(vcs_url)
                    if not url.scheme:
                        self.remotes['local'] = '/'
                        found = True

                    if not found:
                        for (remoteurl, remotename) in settings.REMOTES:
                            if vcs_url.startswith(remoteurl):
                                self.remotes[remotename] = remoteurl
                                found = True
                                break

                    if not found:
                        self.remotes[url.scheme + '_' + url.netloc.translate(str.maketrans('/:', '__'))] = url.scheme + '://' + url.netloc

        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            process_remote(lindex, layerBranch)

        def display_layer(lindex, layerBranch):
            branchid = self.index.getBranchId(lindex, self.get_branch(lindex=lindex))

            for layer in self.index.find_layer(lindex, id=layerBranch['layer']):
                vcs_url = layer['vcs_url']

                path = 'layers/' + "".join(vcs_url.split('/')[-1:])

                if (layer['name'] == 'openembedded-core'):
                    bitbakeBranch = self.index.getBranch(lindex, layerBranch['branch'])['bitbake_branch']
                    logger.debug('bitbake: %s %s %s' % ( settings.BITBAKE, path + '/bitbake', bitbakeBranch ))

                actual_branch = layerBranch['actual_branch'] or self.index.getBranch(lindex, branchid)['name']
                logger.debug('%s: %s %s %s' % (layer['name'], vcs_url, path, actual_branch ))


        logger.debug('Computed required layers:')
        for (lindex, layerBranch) in self.requiredlayers:
            display_layer(lindex, layerBranch)

        logger.debug('Computed recommended layers:%s' % (["", ' (skipping)'][self.no_recommend == True]))
        for (lindex, layerBranch) in self.recommendedlayers:
            display_layer(lindex, layerBranch)

        # Recommends are disabled, filter it...
        if self.no_recommend == True:
            if self.dl_layers == True:
                newRecommendedlayers = []
                for (lindex, layerBranch) in self.recommendedlayers:
                    layers = self.index.find_layer(lindex, id=layerBranch['layer'])
                    if layers and ('-dl-' in layers[0]['name'] or layers[0]['name'].endswith('-dl')):
                        newRecommendedlayers.append( (lindex, layerBranch) )
                self.recommendedlayers = newRecommendedlayers
            else:
                self.recommendedlayers = []

        logger.debug('Done')

    def project_setup(self):
        logger.debug('Starting')
        self.__setup_local_layer()

        if self.mirror != True:
            # We need to make sure the environment-setup link is always current
            for (dirpath, dirnames, filenames) in os.walk(os.path.join(self.project_dir, 'bin/buildtools')):
                for filename in filenames:
                    if filename.startswith('environment-setup-'):
                        if os.path.exists(os.path.join(self.project_dir, filename)):
                            if os.path.islink(os.path.join(self.project_dir, filename)):
                                dest = os.readlink(os.path.join(self.project_dir, filename))
                                if dest == os.path.join(dirpath, filename):
                                    continue
                            os.unlink(os.path.join(self.project_dir, filename))
                        os.symlink(os.path.join(dirpath, filename), os.path.join(self.project_dir, filename))

        logger.debug('Done')

    def update_project(self):
        logger.debug('Starting')
        if not os.path.exists(self.project_dir + '/.templateconf'):
            tmplconf = open(self.project_dir + '/.templateconf', 'w')
            tmplconf.write('# Project template settings\n')
            tmplconf.write('TEMPLATECONF=${TEMPLATECONF:-$OEROOT/config}\n')
            tmplconf.close()

        self.copySample(self.install_dir + '/data/samples/README.sample', self.project_dir + '/README')
        self.copySample(self.install_dir + '/data/samples/bblayers.conf.sample', self.project_dir + '/config/bblayers.conf.sample')
        self.copySample(self.install_dir + '/data/samples/conf-notes.sample', self.project_dir + '/config/conf-notes.txt')
        self.copySample(self.install_dir + '/data/samples/local.conf.sample', self.project_dir + '/config/local.conf.sample')
        if os.path.exists(self.install_dir + '/data/samples/site.conf.sample'):
            self.copySample(self.install_dir + '/data/samples/site.conf.sample', self.project_dir + '/config/site.conf.sample')

    def update_mirror(self):
        self.copySample(self.install_dir + '/data/samples/README-MIRROR.sample', self.project_dir + '/README')

    def __prep_replacements(self):
        self.replacement['layers'] = []
        self.replacement['machines'] = {}
        self.replacement['distros'] = {}

        def addLayer(lindex, layerBranch):
            branchid = self.index.getBranchId(lindex, self.get_branch(lindex=lindex))

            paths = []
            for layer in self.index.find_layer(lindex, id=layerBranch['layer']):
                vcs_url = layer['vcs_url']

                path = 'layers/' + "".join(vcs_url.split('/')[-1:])
                if layerBranch['vcs_subdir']:
                    path += '/' + layerBranch['vcs_subdir']

                paths.append(path)

            return paths

        # Add layers to 'LAYERS'
        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            self.replacement['layers'] = self.replacement['layers'] + addLayer(lindex, layerBranch)

        # Add machines to 'MACHINES'
        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            for machine in lindex['machines']:
                if machine['layerbranch'] == layerBranch['id']:
                    desc = machine['description'] or machine['name']
                    self.replacement['machines'][machine['name']] = desc

        # Add distro to 'DISTROS'
        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            for distro in lindex['distros']:
                if distro['layerbranch'] == layerBranch['id']:
                    desc = distro['description'] or distro['name']
                    self.replacement['distros'][distro['name']] = desc



    def copySample(self, src, dst):
        src = open(src, 'r')
        dst = open(dst, 'w')

        for line in src:
            if '####LAYERS####' in line:
                for l in self.replacement['layers']:
                    dst.write(line.replace('####LAYERS####', '##OEROOT##/%s' % (l)))
                continue
            if '####SETUP_ARGS####' in line:
                dst.write(line.replace('####SETUP_ARGS####', self.setup_args))
                continue
            if '####MACHINES####' in line:
                for (name, desc) in sorted(self.replacement['machines'].items(), key=lambda t: t[0]):
                    dst.write('# %s\n' % desc.strip())
                    dst.write(line.replace('####MACHINES####', name))
                continue
            if '####DEFAULTMACHINE####' in line:
                name = self.machines[0]
                if ':' in name:
                    name = ':'.join(name.split(':')[1:])
                dst.write(line.replace('####DEFAULTMACHINE####', name))
                continue
            if '####DISTROS####' in line:
                for (name, desc) in sorted(self.replacement['distros'].items(), key=lambda t: t[0]):
                    dst.write('# %s\n' % desc.strip())
                    dst.write(line.replace('####DISTROS####', name))
                continue
            if '####DEFAULTDISTRO####' in line:
                name = self.distros[0]
                if ':' in name:
                    name = ':'.join(name.split(':')[1:])
                dst.write(line.replace('####DEFAULTDISTRO####', name))
                continue
            if '####DEFAULTWRTEMPLATE####' in line:
                dst.write(line.replace('####DEFAULTWRTEMPLATE####', ' '.join(self.wrtemplates)))
                continue
            if '####DEFAULTKTYPE####' in line:
                dst.write(line.replace('####DEFAULTKTYPE####', self.kernel))
                continue
            dst.write(line)

        src.close()
        dst.close()

    def update_mirror_index(self):
        logger.debug('Starting')
        path = os.path.join(self.project_dir, 'mirror-index')

        logger.plain('Exporting mirror-index %s...' % (path))
        if not os.path.exists(path):
            cmd = [self.tools['git'], 'init', path]
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=self.project_dir)

        try:
            cmd = [self.tools['git'], 'checkout', '-b', self.base_branch]
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=path)
        except:
            # if we failed, then simply try to switch branches
            cmd = [self.tools['git'], 'checkout', self.base_branch]
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=path)

        # Make sure the directory is empty, use -f to ignore failures
        for (dirpath, dirnames, filenames) in os.walk(path):
            if dirpath.endswith('/.git') or path + '/.git' in dirpath:
                continue
            for filename in filenames:
                os.remove(os.path.join(dirpath, filename))

        # Construct a list of all layers we've downloaded, by url, including sublayers not activated
        url_cache = {}
        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            for layer in self.index.find_layer(lindex, id=layerBranch['layer']):
                vcs_url = layer['vcs_url']
                if not vcs_url in url_cache:
                    url_cache[vcs_url] = []
                url_cache[vcs_url].append((lindex, layerBranch['branch']))

        # Serialize the information for each of the layers (and their sublayers)
        for vcs_url in url_cache:
            for (lindex, branchid) in url_cache[vcs_url]:
                for layer in lindex['layerItems']:
                    if layer['vcs_url'] in url_cache:
                        for lb in self.index.getLayerBranch(lindex, branchid=branchid, layerItem=layer):
                            self.index.serialize_index(lindex, os.path.join(path, lindex['CFG']['DESCRIPTION']), split=True, layerBranches=[lb], IncludeCFG=True, mirror=True, base_url=self.base_url)
                        name = layer['name']
                        destdir = os.path.join(path, 'xml')
                        srcfile = os.path.join(self.xml_dir, '%s.inc' % (name))
                        if os.path.exists(srcfile):
                            os.makedirs(destdir, exist_ok=True)
                            shutil.copy(srcfile, destdir)
                        srcfile = os.path.join(self.xml_dir, '%s.xml' % (name))
                        if os.path.exists(srcfile):
                            os.makedirs(destdir, exist_ok=True)
                            shutil.copy(srcfile, destdir)

                        # Special processing for the openembedded-core layer
                        if name == 'openembedded-core':
                            srcfile = os.path.join(self.xml_dir, 'bitbake.inc')
                            if os.path.exists(srcfile):
                                os.makedirs(destdir, exist_ok=True)
                                shutil.copy(srcfile, destdir)
                            srcfile = os.path.join(self.xml_dir, 'bitbake.xml')
                            if os.path.exists(srcfile):
                                os.makedirs(destdir, exist_ok=True)
                                shutil.copy(srcfile, destdir)

        # git add file.
        cmd = [self.tools['git'], 'add', '-A', '.']
        utils_setup.run_cmd(cmd, environment=self.env, cwd=path)

        try:
            cmd = [self.tools['git'], 'diff-index', '--quiet', 'HEAD', '--']
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=path, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            logger.debug('Updating mirror-index')
            cmd = [self.tools['git'], 'commit', '-m', 'Updated index - %s' % (self.setup_args)]
            utils_setup.run_cmd(cmd, environment=self.env, cwd=path)
        logger.debug('Done')


    def update_manifest(self):
        logger.debug('Starting')

        fxml = open(os.path.join(self.project_dir, self.default_xml), 'w')
        fxml.write('<manifest>\n')

        remote = 'base'
        fxml.write('    <remote  name="%s" fetch="%s"/>\n' % (remote, self.remotes[remote]))
        fxml.write('    <default revision="%s" remote="%s" sync-j="%s"/>\n' % (self.base_branch, remote, self.jobs))

        for remote in sorted(self.remotes):
            if remote == 'base':
                continue
            fxml.write('    <remote  name="%s" fetch="%s"/>\n' % (remote, self.remotes[remote]))

        def open_xml_tag(name, url, remote, path, revision):
            fxml.write('    <project name="%s" remote="%s" path="%s" revision="%s">\n' % (url, remote, path, revision))

        def inc_xml(name, url, remote, path, revision):
            # incfile is included inline and has to work as elements of the 'project'
            incfile = os.path.join(self.xml_dir, '%s.inc' % (name))
            logger.debug('Looking for %s' % (incfile))
            if os.path.exists(incfile):
                fbase = open(incfile, 'r')
                for line in fbase:
                    fxml.write(line)
                fbase.close()

        def close_xml_tag(name, url, remote, path, revision):
            fxml.write('    </project>\n')

        def add_xml(name, url, remote, path, revision):
            # xmlfile is included after the entry and is completely standalone
            xmlfile = os.path.join(self.xml_dir, '%s.xml' % (name))
            logger.debug('Looking for %s' % (xmlfile))
            if os.path.exists(xmlfile):
                fbase = open(xmlfile, 'r')
                for line in fbase:
                    fxml.write(line)
                fbase.close()

        def write_xml(name, url, remote, path, revision):
            open_xml_tag(name, url, remote, path, revision)
            inc_xml(name, url, remote, path, revision)
            close_xml_tag(name, url, remote, path, revision)
            add_xml(name, url, remote, path, revision)

        if self.mirror == True and self.buildtools_remote and self.buildtools_branch:
            write_xml('buildtools', self.buildtools_remote, 'base', self.buildtools_remote, self.buildtools_branch)

        def process_xml_layers(allLayers):
            def process_xml_layer(lindex, layerBranch):
                branchid = self.index.getBranchId(lindex, self.get_branch(lindex=lindex))

                for layer in self.index.find_layer(lindex, id=layerBranch['layer']):
                    revision = layerBranch['actual_branch'] or self.index.getBranch(lindex, branchid)['name']

                    vcs_url = layer['vcs_url']

                    for remote in self.remotes:
                        if vcs_url.startswith(self.remotes[remote]):
                            break

                    url = vcs_url[len(self.remotes[remote]):]
                    url = url.strip('/')

                    path = 'layers/' + "".join(url.split('/')[-1:])

                    entry = {
                           'name' : layer['name'],
                           'remote' : remote,
                           'path' : path,
                           'revision' : revision,
                        }

                    if url not in cache:
                        cache[url] = []

                    if entry['name'] == 'openembedded-core':
                        bitbakeurl = '/'.join(url.split('/')[:-1] + [ settings.BITBAKE ])
                        bitbakeBranch = self.index.getBranch(lindex, layerBranch['branch'])['bitbake_branch']
                        bitbake_entry = {
                                'name' : 'bitbake',
                                'remote' : remote,
                                'path' : path + '/bitbake',
                                'revision' : bitbakeBranch,
                            }
                        if bitbakeurl not in cache:
                            cache[bitbakeurl] = []
                        cache[bitbakeurl].append(bitbake_entry)

                    cache[url].append(entry)

            # We need to construct a list of layers with same urls...
            cache = {}

            for (lindex, layerBranch) in allLayers:
                process_xml_layer(lindex, layerBranch)

            from collections import OrderedDict

            for url in OrderedDict(sorted(cache.items(), key=lambda t: t[0])):
                name = cache[url][0]['name']
                remote = cache[url][0]['remote']
                path = cache[url][0]['path']
                revision = cache[url][0]['revision']

                open_xml_tag(name, url, remote, path, revision)

                for entry in cache[url]:
                    inc_xml(entry['name'], url, remote, path, revision)

                close_xml_tag(name, url, remote, path, revision)

                for entry in cache[url]:
                    add_xml(entry['name'], url, remote, path, revision)

        process_xml_layers(self.requiredlayers + self.recommendedlayers)

        fxml.write('</manifest>\n')
        fxml.close()

        logger.debug('Done')

    def update_gitignore(self):
        logger.debug('Starting')

        import xml.etree.ElementTree as ET

        ign_list = [
                    '.repo*',
                    '*.pyc',
                    '*.pyo',
                    '*.swp',
                    '*.orig',
                    '*.rej',
                    '*~',
                    '/bin/buildtools*',
                    '/environment-setup-*',
                    '/layers/*',
                    '!layers/local',
                    ]

        tree = ET.parse(os.path.join(self.project_dir, 'default.xml'))
        root = tree.getroot()
        for linkfile in root.iter('linkfile'):
            ign_list.append(linkfile.attrib['dest'])

        with open(os.path.join(self.project_dir, '.gitignore'), 'a+') as f:
            f.seek(0)
            existed = f.readlines()
            for l in ign_list:
                item = '%s\n' % l
                if item not in existed:
                    f.write(item)

        logger.debug('Done')

    def commit_files(self):
        logger.debug('Starting')

        # List of all files that may change due to config
        filelist = [
            'README',
            'default.xml',
            '.gitignore',
            '.gitconfig',
            ]

        # If we are mirroring, skip all of these...
        if self.mirror != True:
            filelist.append('layers/local')
            filelist.append('.templateconf')
            filelist.append('config/bblayers.conf.sample')
            filelist.append('config/conf-notes.txt')
            filelist.append('config/local.conf.sample')

            if os.path.exists('config/site.conf.sample'):
                filelist.append('config/site.conf.sample')

        # Add log dir if it contains files
        if os.listdir('config/log'):
            filelist.append('config/log')

        # git init
        if not os.path.exists(self.project_dir + '/.git'):
            cmd = [self.tools['git'], 'init', self.project_dir]
            if self.quiet == self.default_repo_quiet:
                cmd.append(self.quiet)
            utils_setup.run_cmd(cmd, environment=self.env, cwd=self.conf_dir)

            # Add self.install_dir as a submodule if it is in self.project_dir
            if self.install_dir.startswith(self.project_dir + '/'):
                logger.debug('Add %s as a submodule' % self.install_dir)
                cmd = [self.tools['git'], 'submodule', 'add', \
                        './' + os.path.relpath(self.install_dir, self.project_dir)]
                utils_setup.run_cmd(cmd, environment=self.env, cwd=self.project_dir)
                filelist.append(self.install_dir)
                filelist.append('.gitmodules')

        # git add manifest. (Since these files are new, always try to add them)
        cmd = [self.tools['git'], 'add', '--'] + filelist
        utils_setup.run_cmd(cmd, environment=self.env, cwd=self.project_dir)

        try:
            cmd = [self.tools['git'], 'diff-index', '--quiet', 'HEAD', '--'] + filelist
            utils_setup.run_cmd(cmd, log=2, environment=self.env, cwd=self.project_dir, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            logger.plain('Updated project configuration')
            # Command failed -- so self.default_xml changed...
            cmd = [self.tools['git'], 'commit', '-m', 'Configuration change - %s' % (self.setup_args), '--'] + filelist
            utils_setup.run_cmd(cmd, environment=self.env, cwd=self.project_dir)

        logger.debug('Done')

    def repo_sync(self):
        logger.debug('Starting')

        if os.path.exists(os.path.join(self.project_dir, self.check_repo_install_dir)):
            cmd = ['-j', self.jobs]
            self.call_repo_sync(cmd)
        else:
            # repo init
            cmd = ['-m', self.default_xml, '-u',  self.project_dir]
            if self.mirror == True:
                cmd.append('--mirror')

            cmd.append('--no-repo-verify')
            self.call_repo_init(cmd)

            # repo sync
            cmd = ['-j', self.jobs]
            self.call_initial_repo_sync(cmd)

        logger.debug('Done')

    def __setup_local_layer(self):
        """Setup the local layer in /layers/local - if required."""
        logger.debug('Checking local layer')

        if os.path.exists(os.path.join(self.project_dir,'layers/local')):
            return

        if self.mirror is True:
            return


        logger.debug('Starting local layer')

        if not os.path.exists(os.path.join(self.project_dir, 'layers')):
            os.makedirs(os.path.join(self.project_dir, 'layers'))

        if not os.path.exists(os.path.join(self.project_dir, 'layers/local')):
            shutil.copytree(os.path.join(self.install_dir, 'data/local_layer'), os.path.join(self.project_dir, 'layers/local'))

        logger.debug('Done')

    def setup_env(self):
        self.set_ssl_cert()
        self.set_repo_git_env()
        self.add_bin_path()

    def add_bin_path(self):
        self.env["PATH"] = self.install_dir + "/bin:" + self.env["PATH"]

    def set_repo_git_env(self):
        # Set HOME to install_dir to use install_dir/.gitconfig settings.  Otherwise the user will
        # be prompted for information.
        self.env["HOME"] = self.project_dir

    def set_ssl_cert(self):
        fn = self.project_dir + self.BINTOOLS_SSL_CERT
        dn = self.project_dir + self.BINTOOLS_SSL_DIR
        self.env["GIT_SSL_CAINFO"] = fn
        self.env["CURL_CA_BUNDLE"] = fn
        self.env["SSL_CERT_FILE"] = fn
        self.env["SSL_CERT_DIR"] = dn
        os.environ["SSL_CERT_FILE"] = fn
        os.environ["SSL_CERT_DIR"] = dn

    def call_repo_init(self, args):
        logger.debug('Starting')
        repo = self.tools['repo']
        directory = os.path.join(self.project_dir, self.check_repo_install_dir)
        if os.path.exists(directory):
            logger.info('Done: detected repo init already run since %s exists' % directory)
            return
        cmd = args
        cmd.insert(0, repo)
        cmd.insert(1, 'init')
        if self.depth:
            cmd.append(self.depth)
        log_it = 1
        if self.repo_verbose is not True and self.quiet == self.default_repo_quiet:
            cmd.append(self.quiet)
            log_it = 0
        try:
            utils_setup.run_cmd(cmd, environment=self.env, log=log_it)
        except Exception as e:
            raise
        logger.debug('Done')

    # This only exists to check if we have fully sync'ed the project
    # Updating should use call_repo_sync
    def call_initial_repo_sync(self, args):
        logger.debug('Starting')
        sync_file= os.path.join(self.project_dir, self.check_repo_sync_file)
        local_only = 0
        orig_args = list(args)
        if os.path.exists(sync_file):
            logger.info('Detected repo sync already run since %s exists' % sync_file)
            logger.info('Only running local update.')
            args.append('--local-only')
            local_only = 1
        try:
            self.call_repo_sync(args)
        except Exception as e:
            if not local_only:
                raise
            else:
                logger.info('Using --local-only failed.  Trying full sync.')
                try:
                    self.call_repo_sync(orig_args)
                except Exception as e2:
                    raise

        logger.debug('Done')

    def call_repo_sync(self, args):
        logger.debug('Starting')
        repo = self.tools['repo']
        cmd = args
        cmd.insert(0, repo)
        cmd.insert(1, 'sync')
        cmd.insert(2, '--prune')
        if self.force_sync:
            cmd.append(self.force_sync)
        log_it = 1
        if self.repo_verbose is not True and self.quiet == self.default_repo_quiet:
            cmd.append(self.quiet)
            log_it = 0
        utils_setup.run_cmd(cmd, environment=self.env, log=log_it)
        logger.debug('Done')

    def get_branch(self, lindex=None):
        if lindex:
            return self.index.getIndexBranch(default=self.base_branch, lindex=lindex)
        return self.base_branch

    def get_path(self, tool):
        cmd = self.which(tool)
        if (not cmd):
            logger.critical('Cannot find %s in path!' % tool)
            logger.critical('Path was: %s' % os.environ['PATH'])
            self.exit(1)
        return cmd

    # Helpers: Set_*, which..
    def set_repo_verbose(self, verbose):
        self.repo_verbose = verbose

    def set_jobs(self, jobs):
        logger.debug('Setting jobs to %s' % jobs)
        self.jobs = jobs

    def set_depth(self, depth):
        if int(depth) <= 1:
            logger.info('repo depth %s is invalid, setting to 2' % depth)
            depth = '2'
        logger.debug('Setting depth to %s' % depth)
        self.depth = '--depth=%s' % depth

    def set_force_sync(self, sync):
        logger.debug('Setting force-sync to %s' % sync)
        if sync is True:
            self.force_sync = '--force-sync'

    def set_debug(self):
        self.debug_lvl += 1
        self.set_debug_env()
        self.quiet = None
        logger.setLevel(logging.DEBUG)
        logger.debug('logging level set to DEBUG')

    def set_base_url(self, url):
        logger.debug('Setting base-url to %s' % url)
        self.base_url = url

    def set_base_branch(self, branch):
        logger.debug('Setting base-branch to %s' % branch)
        self.base_branch = branch

    def set_debug_env(self):
        self.env["REPO_CURL_VERBOSE"] = '1'


    def touch(self, fn):
        logger.debug("Creating %s" % fn)
        open(fn, 'a').close()

    ''' When this is python3.3, use built in version'''
    def which(self, program):
        path=self.env["PATH"]
        for path in path.split(os.path.pathsep):
            fullpath=os.path.join(path, program)
            if os.path.exists(fullpath) and os.access(fullpath,os.X_OK):
                return fullpath
        return None

if __name__ == '__main__':
    x = Setup()
    x.main(sys.argv)

