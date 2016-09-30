#!/usr/bin/env python3

# Drop when we move to the future (the future is python 3.)
from __future__ import print_function

# Please keep these sorted.
import logging
import os
import shutil
import subprocess
import sys
import time

# Setup-specific modules
from argparse_setup import Argparse_Setup

from layer_index import Layer_Index

import settings

class Setup():

    tool_list = ['repo', 'git']

    default_jobs = '4'
    default_xml = 'default.xml'
    default_project_dir = 'project'
    default_repo_quiet = '--quiet'

    class_config_dir = 'config'
    class_log_dir = 'log'

    check_repo_install_dir = '.repo/repo/.git'
    check_repo_sync_file = '.repo/projects/'

    FILE_LOG_FORMAT='%(asctime)s %(levelname)8s [%(filename)s:%(lineno)s - %(funcName)20s(): %(message)s'
    SCREEN_LOG_FORMAT='%(asctime)s %(levelname)8s: %(message)s'

    BINTOOLS_SSL_DIR="/bin/buildtools/sysroots/x86_64-wrlinuxsdk-linux/usr/share/ca-certificates/mozilla"
    BINTOOLS_SSL_CERT= "/bin/buildtools/sysroots/x86_64-wrlinuxsdk-linux/etc/ssl/certs/ca-certificates.crt"

    logging.TO_FILE = 5
    def __init__(self):
        # Set various default values
        # Default -j for repo init
        self.jobs = self.default_jobs

        # Pull in the defaults from the environment (set by setup.sh)
        self.base_url = os.getenv('WR_BASEURL')
        self.base_branch = os.getenv('WR_COREBRANCH')

        # Real project or a mirror?
        self.mirror = False

        # Default configuration
        self.distributions = [ settings.DEFAULT_DISTRO ]
        self.machines = [ settings.DEFAULT_MACHINE ]
        self.layers = []
        self.recipes = []
        self.WRtemplates = []
        self.kernel = settings.DEFAULT_KTYPE

        self.all_layers = False
        self.dl_layers = False

        self.no_recommend = False

        self.no_network = False
        self.allowed_network = None

        self.remotes = {}
        self.requiredlayers = []
        self.recommendedlayers = []

        # Set other useful values...
        self.start_time = time.strftime('%(asctime)s', time.gmtime())

        # Default quiet:
        self.quiet = self.default_repo_quiet
        self.logging = 0

        self.debug_lvl = 0

        # Set the install_dir
        # Use the path from this file.  Note bin has to be dropped.
        self.install_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')

        # Set the directory where we're running.
        self.project_dir = os.getcwd()

        self.conf_dir = os.path.join(self.project_dir, self.class_config_dir)

        # Logging timezone is UTC
        self.log_dir= os.path.join(self.conf_dir, self.class_log_dir)

        # Environment setup
        self.env = os.environ.copy()
        self.setup_env()

        # Check for all the tools and create a dictionary of the path
        self.tools = {i : self.get_path(i) for i in self.tool_list}

        # Config flags
        self.list_distributions = False
        self.list_machines = False
        self.list_layers = False
        self.list_recipes = False
        self.list_WRtemplates = False

    def exit(self, ret=0):
        logging.debug("setup.py finished (ret=%s)" % (ret))
        sys.exit(ret)

    def start_logging(self):
        if not self.logging:
            self.logging = 1

        if not os.path.exists(self.conf_dir):
            os.makedirs(self.conf_dir)

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        log_file = '%s/%s.log' % (self.log_dir, time.strftime('%Y-%m-%d-%H:%M:%S+0000', time.gmtime()))
        logging.basicConfig(filename=log_file, format=self.FILE_LOG_FORMAT, level=logging.TO_FILE)
        logging.addLevelName(logging.TO_FILE, 'TO_FILE')
        logging.Formatter.converter = time.gmtime

        # Duplicate INFO logging to screen.
        self.screen_out = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(self.SCREEN_LOG_FORMAT)
        self.screen_out.setFormatter(formatter)
        self.screen_out.setLevel(logging.INFO)
        logging.getLogger().addHandler(self.screen_out)

        logging.info("Logging to %s" % log_file);

    def main(self, orig_args):
        parser = Argparse_Setup(self)
        # We want to default to help mode lacking any args.
        if not orig_args or not orig_args[1:]:
            orig_args.append('--help')
        parser.evaluate_args(orig_args[1:])
        self.configure_args = parser.argparse_conf.configure_arguments

        if not self.base_url:
            logging.error('Unable to determine base url, you may need to specify --base-url=')

        if not self.base_branch:
            logging.error('Unable to determine base branch, you may need to specify --core-branch=')

        if not self.base_url or not self.base_branch:
            self.exit(1)

        # Load Layer_Index
        replace = []
        replace = replace + settings.REPLACE
        replace = replace + [
                   ( '#INSTALL_DIR#', self.install_dir ),
                   ( '#BASE_URL#', self.base_url ),
                   ( '#BASE_BRANCH#', self.base_branch ),
                  ]
        self.index = Layer_Index(indexcfg=settings.INDEXES, base_branch=self.base_branch, replace=replace)

        if self.list_distributions:
            self.index.list_distributions(self.base_branch)

        if self.list_machines:
            self.index.list_machines(self.base_branch)

        if self.list_layers:
            self.index.list_layers(self.base_branch)

        if self.list_recipes:
            self.index.list_recipes(self.base_branch)

        if self.list_WRtemplates:
            self.index.list_WRtemplates(self.base_branch)

        if self.list_distributions or self.list_machines or self.list_layers or self.list_recipes or self.list_WRtemplates:
            sys.exit(0)

        self.start_logging()
        logging.debug('setup.py started')
        logging.debug('Calling setup main with arguments %s', str(orig_args))
        logging.debug("configure args are: %s" % " ".join(self.configure_args))

        # Log debug which may have been missed due to log level.
        logging.debug("PATH=%s" % self.env["PATH"])

        logging.debug("Tools are:")
        for key in self.tools:
            logging.debug("%s -> %s", key, self.tools[key])

        logging.info('Setting distro to "%s"' % (self.distributions))
        logging.info('Setting machine to "%s"' % (self.machines))
        logging.info('Setting layers to "%s"' % (self.layers))
        logging.info('Setting recipes to "%s"' % (self.recipes))
        logging.info('Setting templates to "%s"' % (self.WRtemplates))

        self.process_layers()

        self.project_setup()

        self.update_project()
        self.update_manifest()

        self.commit_files()

        self.repo_sync()

        self.exit(0)

    def process_layers(self):
        from collections import deque

        # We allow duplicates in the queue, they're filtered later
        # Queue of required objects
        requiredQueue = deque([])
        # Queue of recommended objects
        recommendedQueue = deque([])

        logging.debug('Starting')
        # if this switches to false, we have to exit at the end of this function
        allfound = True

        # It all startes with BASE_LAYERS, so always include this. (only from index 0)
        lindex = self.index.index[0]
        branchid = self.index.getBranchId(lindex, self.base_branch)
        if branchid:
            for lname in settings.BASE_LAYERS.split():
                base_layerBranch = self.index.getLayerBranch(lindex, branchid, name=lname)

                if not base_layerBranch or not branchid:
                    raise StandardError('Unable to find base layer: %s in the Layer_Index' % (lname))

                for lb in base_layerBranch:
                    requiredQueue.append( (lindex, lb) )

        # process the configuration arguments (find the layers we need for the project)
        # if an item is 'layer:item', then the 'foo' part must match a layer name.
        def procConfig(layer=None, distribution=None, machine=None, recipe=None, WRtemplate=None):
            item = ['', layer][layer != None] + ['', distribution][distribution != None]
            item = item + ['', machine][machine != None] + ['', recipe][recipe != None]
            item = item + ['', WRtemplate][WRtemplate != None]

            type = ['', 'layer'][layer != None] + ['', 'distribution'][distribution != None]
            type = type + ['', 'machine'][machine != None] + ['', 'recipe'][recipe != None]
            type = type + ['', 'template'][WRtemplate != None]

            if (':' in item):
                # User told us which layer, so ignore the other bits -- they can be used later...
                layer = item.split(':')[0]
                distribution = None
                machine = None
                recipe = None
                WRtemplate = None

            # TODO: We do not actually verify the item we asked for (if a layer was specified) is available
            found = False
            for lindex in self.index.index:
                branchid = self.index.getBranchId(lindex, self.base_branch)
                if not branchid:
                    continue
                for layerBranch in self.index.getLayerBranch(lindex, branchid, name=layer, distribution=distribution, machine=machine, recipe=recipe, WRtemplate=WRtemplate) or []:
                    requiredQueue.append( (lindex, layerBranch) )
                    found = True
                if found:
                    break

            if not found:
                logging.critical('%s "%s" not found' % (type, item))
                return False

            return True

        for l in self.layers:
            if not procConfig(layer=l):
                allfound = False

        for l in self.distributions:
            if not procConfig(distribution=l):
                allfound = False

        for l in self.machines:
            if not procConfig(machine=l):
                allfound = False

        for l in self.recipes:
            if not procConfig(recipe=l):
                allfound = False

        for l in self.WRtemplates:
            if not procConfig(WRtemplate=l):
                allfound = False

        # Add all layers -- if necessary
        if self.all_layers == True:
            for lindex in self.index.index:
                branchid = self.index.getBranchId(lindex, self.base_branch)
                if not branchid:
                    continue
                for l in lindex['layerItems']:
                    for layerBranch in self.index.getLayerBranch(lindex, branchid, layerItem=l) or []:
                        # dl layers are always added as recommends in an --all-layers mode
                        if '-dl-' in l['name'] or l['name'].endswith('-dl'):
                            recommendedQueue.append( (lindex, layerBranch) )
                        requiredQueue.append( (lindex, layerBranch) )

        if not allfound:
            logging.critical('Please correct the missing items, exiting.')
            self.exit(1)

        # Compute requires and recommended layers...

        # List of 'collection' and layer 'name'.  This list is used to avoid
        # including duplicates.  Collection is matched first, then name -- as not
        # all layer indexes may contain 'collection'
        depCacheCol = []
        depCacheName = []

        def checkCache(lindex, layerBranch, addCache=False):
            collection = ""
            if 'collection' in layerBranch:
                collection = layerBranch['collection']
            for layer in self.index.find_layer(lindex, layerBranch=layerBranch):
                name = ""
                if layer:
                    name = layer['name']
                    break
            if collection in depCacheCol or name in depCacheName:
                return True
            if addCache:
                if collection:
                    depCacheCol.append(collection)
                if name:
                    depCacheName.append(name)
            return False

        while requiredQueue:
            (lindex, layerBranch) = requiredQueue.popleft()
            if not checkCache(lindex, layerBranch, True):
                self.requiredlayers.append( (lindex, layerBranch) )
                (required, recommended) = self.index.getDependencies(lindex, layerBranch)
                for dep in required:
                    requiredQueue.append( (lindex, dep) )

                for dep in recommended:
                    recommendedQueue.append( (lindex, dep) )

        while recommendedQueue:
            (lindex, layerBranch) = recommendedQueue.popleft()
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
        try:
            from urllib.request import urlopen, URLError
            from urllib.parse import urlparse
        except ImportError:
            from urllib2 import urlopen, URLError
            from urlparse import urlparse

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
                    elif vcs_url.startswith('git://git.openembedded.org'):
                        self.remotes['openembedded'] = 'git://git.openembedded.org'
                    elif vcs_url.startswith('git://git.yoctoproject.org'):
                        self.remotes['yoctoproject'] = 'git://git.yoctoproject.org'
                    else:
                        self.remotes[url.scheme + '_' + url.netloc.translate(str.maketrans('/:', '__'))] = url.scheme + '://' + url.netloc

        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            process_remote(lindex, layerBranch)

        def display_layer(lindex, layerBranch):
            branchid = self.index.getBranchId(lindex, self.base_branch)

            for layer in self.index.find_layer(lindex, id=layerBranch['layer']):
                vcs_url = layer['vcs_url']

                path = 'layers/' + "".join(vcs_url.split('/')[-1:])

                if (layer['name'] == 'openembedded-core'):
                    bitbakeBranch = self.index.getBranch(lindex, layerBranch['branch'])['bitbake_branch']
                    logging.debug('bitbake: %s %s %s' % ( settings.BITBAKE, path + '/bitbake', bitbakeBranch ))

                actual_branch = layerBranch['actual_branch'] or self.index.getBranch(lindex, branchid)['name']
                logging.debug('%s: %s %s %s' % (layer['name'], vcs_url, path, actual_branch ))


        logging.debug('Computed required layers:')
        for (lindex, layerBranch) in self.requiredlayers:
            display_layer(lindex, layerBranch)

        logging.debug('Computed recommended layers:%s' % (["", ' (skipping)'][self.no_recommend == True]))
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

        logging.debug('Done')

    def project_setup(self):
        logging.debug('Starting')
        if not os.path.exists(self.project_dir + '/.git'):
            if self.mirror != True:
                self.setup_local_layer()

            if self.mirror != True:
                for (dirpath, dirnames, filenames) in os.walk(os.path.join(self.project_dir, 'bin/buildtools')):
                    for filename in filenames:
                        if filename.startswith('environment-setup-'):
                            os.symlink(os.path.join(dirpath, filename), os.path.join(self.project_dir, filename))

            # Run this last as it does the initial project commit
            self.setup_git_project_dir()
        logging.debug('Done')

    def update_project(self):
        logging.debug('Starting')
        if not os.path.exists(self.project_dir + '/.templateconf'):
            tmplconf = open(self.project_dir + '/.templateconf', 'w')
            tmplconf.write('# Project template settings\n')
            tmplconf.write('TEMPLATECONF=${TEMPLATECONF:-$OEROOT/config}\n')
            tmplconf.close()

        layers = []
        configure_args = " ".join(self.configure_args)
        machines = {}
        defaultmachine = self.machines[0]
        distributions = {}
        defaultdistribution = self.distributions[0]
        defaultktype = self.kernel

        def addLayer(lindex, layerBranch):
            branchid = self.index.getBranchId(lindex, self.base_branch)

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
            layers = layers + addLayer(lindex, layerBranch)

        # Add machines to 'MACHINES'
        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            for machine in lindex['machines']:
                if machine['layerbranch'] == layerBranch['id']:
                    desc = machine['description'] or machine['name']
                    machines[machine['name']] = desc

        # Add distribution to 'DISTROS'
        for (lindex, layerBranch) in self.requiredlayers + self.recommendedlayers:
            for distribution in lindex['distributions']:
                if distribution['layerbranch'] == layerBranch['id']:
                    desc = distribution['description'] or distribution['name']
                    distributions[distribution['name']] = desc

        def copySample(src, dst):
            src = open(src, 'r')
            dst = open(dst, 'w')

            for line in src:
                if '####LAYERS####' in line:
                    for l in layers:
                        dst.write(line.replace('####LAYERS####', '##OEROOT##/%s' % (l)))
                    continue
                if '####CONFIGURE_ARGS####' in line:
                    dst.write(line.replace('####CONFIGURE_ARGS####', configure_args))
                    continue
                if '####MACHINES####' in line:
                    for (name, desc) in sorted(machines.items(), key=lambda t: t[0]):
                        dst.write('# %s\n' % desc.strip())
                        dst.write(line.replace('####MACHINES####', name))
                    continue
                if '####DEFAULTMACHINE####' in line:
                    name = defaultmachine
                    if ':' in name:
                        name = ':'.join(name.split(':')[1:])
                    dst.write(line.replace('####DEFAULTMACHINE####', name))
                    continue
                if '####DISTROS####' in line:
                    for (name, desc) in sorted(distributions.items(), key=lambda t: t[0]):
                        dst.write('# %s\n' % desc.strip())
                        dst.write(line.replace('####DISTROS####', name))
                    continue
                if '####DEFAULTDISTRO####' in line:
                    name = defaultdistribution
                    if ':' in name:
                        name = ':'.join(name.split(':')[1:])
                    dst.write(line.replace('####DEFAULTDISTRO####', name))
                    continue
                if '####DEFAULTKTYPE####' in line:
                    dst.write(line.replace('####DEFAULTKTYPE####', defaultktype))
                    continue
                dst.write(line)

            src.close()
            dst.close()

        copySample(self.install_dir + '/data/samples/README.sample', self.project_dir + '/README')
        copySample(self.install_dir + '/data/samples/bblayers.conf.sample', self.project_dir + '/config/bblayers.conf.sample')
        copySample(self.install_dir + '/data/samples/conf-notes.sample', self.project_dir + '/config/conf-notes.txt')
        copySample(self.install_dir + '/data/samples/local.conf.sample', self.project_dir + '/config/local.conf.sample')
        copySample(self.install_dir + '/data/samples/site.conf.sample', self.project_dir + '/config/site.conf.sample')

    def update_manifest(self):
        logging.debug('Starting')

        fxml = open(os.path.join(self.project_dir, self.default_xml), 'w')
        fxml.write('<manifest>\n')

        remote = 'base'
        fxml.write('    <remote  name="%s" fetch="%s"/>\n' % (remote, self.remotes[remote]))
        fxml.write('    <default revision="%s" remote="%s" sync-j="%s"/>\n' % (self.base_branch, remote, self.default_jobs))

        for remote in self.remotes:
            if remote == 'base':
                continue
            fxml.write('    <remote  name="%s" fetch="%s"/>\n' % (remote, self.remotes[remote]))

        def open_xml_tag(name, url, remote, path, revision):
            fxml.write('    <project name="%s" remote="%s" path="%s" revision="%s">\n' % (url, remote, path, revision))

        def inc_xml(name, url, remote, path, revision):
            # incfile is included inline and has to work as elements of the 'project'
            incfile = os.path.join(self.install_dir, 'data/xml/%s.inc' % (name))
            logging.debug('Looking for %s' % (incfile))
            if os.path.exists(incfile):
                fbase = open(incfile, 'r')
                for line in fbase:
                    fxml.write(line)
                fbase.close()

        def close_xml_tag(name, url, remote, path, revision):
            fxml.write('    </project>\n')

        def add_xml(name, url, remote, path, revision):
            # xmlfile is included after the entry and is completely standalone
            xmlfile = os.path.join(self.install_dir, 'data/xml/%s.xml' % (name))
            logging.debug('Looking for %s' % (xmlfile))
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

        if self.mirror == True:
            if (not os.path.exists(self.project_dir + '/wrlinux-x')):
                write_xml('wrlinux-x', 'wrlinux-x', 'base', 'wrlinux-x', self.base_branch)

            write_xml('git-repo', 'tools/git-repo', 'base', 'tools/git-repo', 'master') # hard coded for now...
            write_xml('buildtools', 'layers/buildtools/buildtools-standalone-20160929', 'base', 'layers/buildtools/buildtools-standalone-20160929', 'master')

        def process_xml_layers(allLayers):
            def process_xml_layer(lindex, layerBranch):
                branchid = self.index.getBranchId(lindex, self.base_branch)

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

                # OpenEmbedded-core is unique, we need to add bitbake
                if name == 'openembedded-core':
                    bitbakeBranch = self.index.getBranch(lindex, layerBranch['branch'])['bitbake_branch']
                    write_xml('bitbake', settings.BITBAKE, remote, path + '/bitbake', bitbakeBranch)

                open_xml_tag(name, url, remote, path, revision)

                for entry in cache[url]:
                    inc_xml(entry['name'], url, remote, path, revision)

                close_xml_tag(name, url, remote, path, revision)

                for entry in cache[url]:
                    add_xml(entry['name'], url, remote, path, revision)

        process_xml_layers(self.requiredlayers + self.recommendedlayers)

        fxml.write('</manifest>\n')
        fxml.close()

        logging.debug('Done')

    def commit_files(self):
        logging.debug('Starting')

        # List of all files that may change due to config
        filelist = [
            '.templateconf',
            'config/bblayers.conf.sample',
            'config/conf-notes.txt',
            'config/local.conf.sample',
            'config/site.conf.sample',
            'default.xml',
            ]

        # git add manifest.
        cmd = [self.tools['git'], 'add', '--']
        for file in filelist:
            cmd.append(file)
        self.run_cmd(cmd, cwd=self.project_dir)

        cmd = [self.tools['git'], 'diff-index', '--quiet', 'HEAD', '--']
        for file in filelist:
            cmd.append(file)
        ret = subprocess.Popen(cmd, cwd=self.project_dir, close_fds=True)
        ret.wait()
        if (ret.returncode != 0):
            logging.warning('Updated project configuration')
            # Command failed -- so self.default_xml changed...
            cmd = [self.tools['git'], 'commit', '-m', 'Configuration change - %s' % (" ".join(self.configure_args)), '--']
            for file in filelist:
                cmd.append(file)
            self.run_cmd(cmd, cwd=self.project_dir)

        logging.debug('Done')

    def repo_sync(self):
        logging.debug('Starting')

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

        logging.debug('Done')

    def setup_local_layer(self):
        logging.debug('Starting')
        import shutil
        if not os.path.exists(os.path.join(self.project_dir, 'layers')):
            os.mkdir(os.path.join(self.project_dir, 'layers'))
        if not os.path.exists(os.path.join(self.project_dir, 'layers/local')):
            shutil.copytree(os.path.join(self.install_dir, 'data/local_layer'), os.path.join(self.project_dir, 'layers/local'))
        logging.debug('Done')

    def setup_git_project_dir(self):
        logging.debug('Starting')

        # git init
        cmd = [self.tools['git'], 'init', self.project_dir]
        if self.quiet == self.default_repo_quiet:
            cmd.append(self.quiet)
        self.run_cmd(cmd, cwd=self.conf_dir)

        open(os.path.join(self.project_dir, '.gitignore'), 'a').close()

        # git add file.
        cmd = [self.tools['git'], 'add', '.']
        self.run_cmd(cmd, cwd=self.project_dir)

        # Perform the initial commit
        cmd = [self.tools['git'], 'commit', '-am', 'Initial Project Setup']
        if self.quiet == self.default_repo_quiet:
            cmd.append(self.quiet)
        self.run_cmd(cmd, cwd=self.conf_dir)

        logging.debug('Done')

    def git_commit_file_conf_dir(self, fn, msg):
        logging.debug('Starting')
        if not os.path.isabs(fn):
            fn = self.conf_dir + "/" + fn

        # git add file.
        cmd = [self.tools['git'], 'add', fn]
        self.run_cmd(cmd, cwd=self.conf_dir)

        #git commit log dir
        cmd = [self.tools['git'], 'commit', '-am', msg]
        if self.quiet == self.default_repo_quiet:
            cmd.append(self.quiet)
        self.run_cmd(cmd, cwd=self.conf_dir)
        logging.debug('Done')

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

    def call_repo_init(self, args):
        logging.debug('Starting')
        repo = self.tools['repo']
        directory = os.path.join(self.project_dir, self.check_repo_install_dir)
        if os.path.exists(directory):
            logging.info('Done: detected repo init already run since %s exists' % directory)
            return
        cmd = args
        cmd.insert(0, repo)
        cmd.insert(1, 'init')
        log_it = 1
        if self.quiet == self.default_repo_quiet:
            cmd.append(self.quiet)
            log_it = 0
        try:
            self.run_cmd(cmd, log=log_it)
        except StandardError as e:
            raise
        logging.debug('Done')

    # This only exists to check if we have fully sync'ed the project
    # Updating should use call_repo_sync
    def call_initial_repo_sync(self, args):
        logging.debug('Starting')
        sync_file= os.path.join(self.project_dir, self.check_repo_sync_file)
        local_only = 0
        orig_args = list(args)
        if os.path.exists(sync_file):
            logging.info('Detected repo sync already run since %s exists' % sync_file)
            logging.info('Only running local update.')
            args.append('--local-only')
            local_only = 1
        try:
            self.call_repo_sync(args)
        except StandardError as e:
            if not local_only:
                raise
            else:
                logging.info('Using --local-only failed.  Trying full sync.')
                try:
                    self.call_repo_sync(orig_args)
                except StandardError as e2:
                    raise

        logging.debug('Done')

    def call_repo_sync(self, args):
        logging.debug('Starting')
        repo = self.tools['repo']
        cmd = args
        cmd.insert(0, repo)
        cmd.insert(1, 'sync')
        log_it = 1
        if self.quiet == self.default_repo_quiet:
            cmd.append(self.quiet)
            log_it = 0
        self.run_cmd(cmd, log=log_it)
        logging.debug('Done')

    def get_path(self, tool):
        cmd = self.which(tool)
        if (not cmd):
            logging.critical('Cannot find %s in path!', tool)
            logging.critical('Path was: %s', os.environ['PATH'])
            self.exit(1)
        return cmd

    def run_cmd(self, cmd, environment=None, cwd=None, log=1, expected_ret=0, err=b'GitError', err2=b'error', err3=b'fatal'):
        err_msg = []
        if environment == None:
            environment = self.env

        logging.debug('Running cmd: "%s"' % repr(cmd))
        if cwd:
            logging.debug('From %s' % cwd)

        if log == 1:
            ret = subprocess.Popen(cmd, env=environment, cwd=cwd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            while True:
                output = ret.stdout.readline()
                if not output and ret.poll() is not None:
                    break
                if output:
                    output = output.strip()
                    if len(err_msg) > 0 or output.startswith(err) or output.startswith(err2) or output.startswith(err3):
                        err_msg.append(output)
                    logging.debug(output)

        else:
            logging.debug('output not logged for this command (%s) without verbose flag (-v).' % (cmd))
            ret = subprocess.Popen(cmd, env=environment, cwd=cwd, close_fds=True)

        ret.wait()
        if (ret.returncode != expected_ret):
            for key in environment.keys():
                logging.log(logging.TO_FILE, '%20s = %s' % (key, repr(environment[key])))
            logging.critical('cmd "%s" returned %d' % (cmd, ret.returncode))

            msg = ''
            if log:
                msg = '\n'.join(err_msg)
                msg += '\n'
            raise StandardError(msg)
        logging.debug('Finished running cmd: "%s"' % repr(cmd))



    # Helpers: Set_*, which..
    def set_jobs(self, jobs):
        logging.debug('Setting jobs to %s' % jobs)
        self.jobs = jobs

    def set_debug(self):
        self.start_logging()
        self.set_debug_env()
        self.quiet = None
        self.screen_out.setLevel(logging.DEBUG)
        formatter = logging.Formatter(self.FILE_LOG_FORMAT)
        self.screen_out.setFormatter(formatter)
        logging.debug('logging level set to DEBUG')

    def set_base_url(self, url):
        logging.debug('Setting base-url to %s' % url)
        self.base_url = url

    def set_base_branch(self, branch):
        logging.debug('Setting core-branch to %s' % branch)
        self.base_branch = branch

    def set_debug_env(self):
        self.env["REPO_CURL_VERBOSE"] = '1'


    def touch(self, fn):
        logging.debug("Creating %s", fn)
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

