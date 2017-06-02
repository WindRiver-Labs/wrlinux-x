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

import json

import sys
import os


from collections import OrderedDict

import logger_setup

import utils_setup

# type, url/path, description, cache
# type:  restapi-web   - REST API from a LayerIndex-web
#        restapi-files - REST API, but only from files
#        export        - Exported DB from a LayerIndex-web -- reads file(s)

logger = logger_setup.setup_logging()
class Layer_Index():
    # Index in REST-API format...  This is used by external items.
    index = []

    def __init__(self, indexcfg=[], base_branch=None, replace=[], mirror=None):
        self.index = []

        # Do we have local mirror entries to load?
        m_index = {}

        if mirror:
            for (dirpath, dirnames, filenames) in os.walk(mirror):
                if dirpath.endswith('/.git') or '/.git/' in dirpath or dirpath.endswith('/xml') or '/xml/' in dirpath:
                    continue
                for filename in filenames:
                    pindex = self.load_serialized_index(os.path.join(dirpath, filename), name='Mirrored Index')
                    # A mirror can be made up of multiple indexes, so we need to identify which one they belong to
                    if pindex and pindex['CFG']['DESCRIPTION'] in m_index:
                        lindex = m_index[pindex['CFG']['DESCRIPTION']]
                        for entry in pindex:
                            if 'apilinks' == entry:
                                continue
                            if 'CFG' == entry:
                                # Conflicts don't matter here, just accept it
                                lindex[entry] = pindex[entry]
                                continue
                            if entry not in lindex:
                                lindex[entry] = []
                            lindex[entry] = self.__add_cmp_lists(pindex[entry], lindex[entry])
                    else: # Not already know
                        m_index[pindex['CFG']['DESCRIPTION']] = pindex

        for cfg in indexcfg:
            lindex = None

            branch = base_branch
            indextype = None
            indexurl = None
            indexname = None
            indexcache = None

            if 'TYPE' in cfg:
                indextype = cfg['TYPE']

            if 'URL' in cfg:
                indexurl = cfg['URL']

            if 'DESCRIPTION' in cfg:
                indexname = cfg['DESCRIPTION']

            if 'CACHE' in cfg:
                indexcache = cfg['CACHE']

            if 'BRANCH' in cfg:
                branch = cfg['BRANCH']

            # Replace magic values with real values...
            for (find, rep) in replace:
                indexurl = indexurl.replace(find, rep)
                if branch:
                    branch = branch.replace(find, rep)

            # Do we have an mirrored version? If so use it, skip regular processing
            if indexname in m_index:
                logger.plain('Using index %s from the mirror index...' % (indexname))
                lindex = m_index[indexname]
            else:
               logger.plain('Loading index %s from %s...' % (indexname, indexurl))

            # If not previously loaded from the mirror, attempt to load...
            if not lindex:
                if indextype == 'restapi-web':
                    lindex = self.load_API_Index(indexurl, indexname, branches=branch)
                elif indextype == 'restapi-files':
                    lindex = self.load_serialized_index(indexurl, name=indexname)
                elif indextype == 'export':
                    lindex = self.load_django_export(indexurl, name=indexname)
                elif not lindex:
                    # Unknown index type...
                    logger.error('Unknown index type %s' % indextype)
                    raise SyntaxError

            # If we couldn't pull from the regular location, pull from the cache!
            if lindex is None and indexcache and os.path.exists(indexcache + '.json'):
                logger.plain('Falling back to the index cache %s...' % (indexcache))
                lindex = self.load_serialized_index(indexcache + '.json', name=indexname, branches=[branch])

            if not lindex or 'branches' not in lindex or 'layerItems' not in lindex or 'layerBranches' not in lindex:
                logger.warning('Index %s was empty... Ignoring.' % indexname)
                continue

            # Start data transforms...
            for entry in lindex['layerItems']:
                for obj in entry:
                    # Run replace on any 'url' items.
                    if 'url' in obj:
                        vcs_url = entry[obj]
                        for (find, rep) in replace:
                            vcs_url = vcs_url.replace(find, rep)
                        entry[obj] = vcs_url

            # Cache the data we loaded... (after replacements) if we loaded data.
            if lindex and indexcache:
                dir = os.path.dirname(indexcache)
                if dir:
                    os.makedirs(dir, exist_ok=True)
                self.serialize_index(lindex, indexcache, split=False)

            lindex['CFG'] = cfg
            lindex['CFG']['BRANCH'] = branch

            if lindex and 'distros' in lindex:
                # Default setup is actually implemented as 'nodistro'
                for (idx, dist) in enumerate(lindex['distros']):
                    if dist['name'] == "defaultsetup":
                        dist['name'] = 'nodistro'
                        lindex['distros'][idx] = dist

            # Everything works off layerBranches, so make sure to keep it sorted!
            lindex['layerBranches'] = self.sortEntry(lindex['layerBranches'])

            if lindex:
                self.index.append(lindex)


    def load_API_Index(self, url, name=None, branches=None):
        """
            Fetches layer information from a remote layer index.
            The return value is a dictionary containing API,
            layer, branch, dependency, recipe, machine, distro,
            and template information.

            url is the url to the rest api of the layer index, such as:
            http://layers.openembedded.org/layerindex/api/

            branches is a str or list of branches to filter on
        """
        lindex = {}

        assert url is not None

        logger.debug('Loading %s from url %s...' % (name, url))

        def _get_json_response(apiurl=None, retry=True):
            assert apiurl is not None

            res = utils_setup.fetch_url(apiurl)

            try:
                parsed = json.loads(res.read().decode('utf-8'))
            except ConnectionResetError:
                if retry:
                    logger.debug("%s: Connection reset by peer.  Retrying..." % url)
                    parsed = _get_json_response(apiurl=apiurl, retry=False)
                    logger.debug("%s: retry successful.")
                else:
                    logger.critical("%s: Connection reset by peer." % url)
                    logger.critical("Is there a firewall blocking your connection?")
                    sys.exit(1)

            return parsed

        from urllib.request import URLError
        try:
            lindex['apilinks'] = _get_json_response(url)
        except URLError as e:
            logger.warning("Index %s: could not connect to %s: %s" % (name, url, msg, e.reason))
            return None

        filter = ""
        # If it's list, keep it, if it's a string change it to a list
        if branches and type(branches) == type(str()):
            branches = [branches]
        if branches:
            filter = "?filter=name:%s" \
                     % "OR".join(branches)
        lindex['branches'] = _get_json_response(lindex['apilinks']['branches'] + filter)

        if not lindex['branches']:
            logger.warning("No valid branches (%s) found at url %s." % (branches or "*", url))
            return lindex

        filter = ""
        if branches:
            filter = "?filter=branch__name:%s" \
                     % "OR".join(branches)
        lindex['layerBranches'] = _get_json_response(lindex['apilinks']['layerBranches'] + filter)
        if not lindex['layerBranches']:
            logger.warning("No layers on branches (%s) found at url %s." % (branches or "*", url))
            return lindex

        layerids = []
        for i, layerBranch in enumerate(lindex['layerBranches']):
            layerids.append("%s" % layerBranch['layer'])

        lindex['layerItems'] = _get_json_response(lindex['apilinks']['layerItems'])

        filter = ""
        if branches:
            filter = "?filter=layerbranch__branch__name:%s" \
                     % "OR".join(branches)
        lindex['layerDependencies'] = _get_json_response(lindex['apilinks']['layerDependencies'] + filter)

        filter = ""
        if branches:
            filter = "?filter=layerbranch__branch__name:%s" \
                     % "OR".join(branches)
        lindex['machines'] = _get_json_response(lindex['apilinks']['machines'] + filter)

        filter = ""
        if branches:
            filter = "?filter=layerbranch__branch__name:%s" \
                     % "OR".join(branches)
        lindex['recipes'] = _get_json_response(lindex['apilinks']['recipes'] + filter)

        filter = ""
        if branches:
            filter = "?filter=layerbranch__branch__name:%s" \
                     % "OR".join(branches)
        if 'distros' in lindex['apilinks']:
            lindex['distros'] = _get_json_response(lindex['apilinks']['distros'] + filter)
        else:
            # Not all layer indexes have a distribution API.  If not we need to emulate nodistro.
            lindex['distros'] = []
            idx = 1
            for branch in lindex['branches']:
                for lb in self.getLayerBranch(lindex, branch['id'], name='openembedded-core'):
                    lindex['distros'].append({"layerbranch": lb['id'], "id": idx, "description": "default", "updated": "2016-01-01T00:00:00+0000", "name": "nodistro"})
                    idx = idx + 1

        filter = ""
        if branches:
            filter = "?filter=layerbranch__branch__name:%s" \
                     % "OR".join(branches)
        if 'wrtemplates' in lindex['apilinks']:
            lindex['wrtemplates'] = _get_json_response(lindex['apilinks']['wrtemplates'] + filter)
        else:
            lindex['wrtemplates'] = []

        logger.debug('...loading %s from url %s, done.' % (name, url))

        return lindex

    # Merge listone and listtwo, returning listtwo
    def __add_cmp_lists(self, listone, listtwo):
        # Copy the items from listone, into listtwo -- if it isn't already
        # there..  if it is there, verify it's the same or raise an error...
        if not listone:
            return listtwo

        for one in reversed(listone):
            found = False
            for two in listtwo:
                if 'id' in one and 'id' in two:
                    if one['id'] == two['id']:
                        found = True
                        # Contents need to be the same!
                        if one != two:
                            # Something is out of sync here...
                            raise
                        break
                else:
                    # This is not a valid object
                    raise
            if not found:
                listtwo.append(one)
        return listtwo

    def load_serialized_index(self, path, name=None, branches=None):
        lindex = {}
        lindex['branches'] = []
        lindex['layerItems'] = []
        lindex['layerBranches'] = []
        lindex['layerDependencies'] = []
        lindex['recipes'] = []
        lindex['machines'] = []
        lindex['distros'] = []
        lindex['wrtemplates'] = []

        assert path is not None

        def loadCache(path):
            logger.debug('Loading json file %s' % path)
            pindex = json.load(open(path, 'rt', encoding='utf-8'))

            for entry in pindex:
                if 'apilinks' == entry:
                    continue
                if 'CFG' == entry:
                    # Conflicts don't matter here, just accept it
                    lindex[entry] = pindex[entry]
                    continue
                if entry not in lindex:
                    lindex[entry] = []
                lindex[entry] = self.__add_cmp_lists(pindex[entry], lindex[entry])

            logger.debug('...loading json file %s, done.' % path)

        if os.path.exists(path) and os.path.isdir(path):
            logger.debug('Loading %s from path %s...' % (name, path))
            for (dirpath, dirnames, filenames) in os.walk(path):
                for filename in filenames:
                    if not filename.endswith('.json'):
                        continue
                    fpath = os.path.join(dirpath, filename)
                    loadCache(fpath)
            logger.debug('...loading %s from path %s, done.' % (name, path))
        elif os.path.exists(path):
            logger.debug('Loading %s from path %s...' % (name, path))
            loadCache(path)
            logger.debug('...loading %s from path %s, done.' % (name, path))
        else:
            logger.error("Index %s: could not find path %s" % (name, path))
            return None

        return lindex

    def load_django_export(self, path, name=None, branches=None):
        lindex = {}
        lindex['branches'] = []
        lindex['layerItems'] = []
        lindex['layerBranches'] = []
        lindex['layerDependencies'] = []
        lindex['recipes'] = []
        lindex['machines'] = []
        lindex['distros'] = []
        lindex['wrtemplates'] = []

        assert path is not None

        def loadDB(path):
            def constructObject(entry):
                obj = entry['fields'].copy()
                obj['id'] = entry['pk']
                return obj

            pindex = {}

            logger.debug('Loading json file %s' % path)
            dbindex = json.load(open(path, 'rt', encoding='utf-8'))

            # We discard anything that doesn't start with 'layerindex.'
            # the other data is adminstrative and stuff we should not mess with
            for entry in dbindex:
                if 'model' in entry:
                    model = entry['model']
                    if model.startswith('layerindex.'):
                        if 'branch' == model[11:]:
                            name = 'branches'
                        elif 'layeritem' == model[11:]:
                            name = 'layerItems'
                        elif 'layerbranch' == model[11:]:
                            name = 'layerBranches'
                        elif 'layerdependency' == model[11:]:
                            name = 'layerDependencies'
                        elif 'recipe' == model[11:]:
                            name = 'recipes'
                        elif 'machine' == model[11:]:
                            name = 'machines'
                        elif 'distro' == model[11:]:
                            name = 'distros'
                        elif 'wrtemplate' == model[11:]:
                            name = 'wrtemplates'
                        else:
                            name = model[11:]

                        if name not in pindex:
                            pindex[name] = []
                        pindex[name].append(constructObject(entry))

            for entry in pindex:
                if entry not in lindex:
                    lindex[entry] = []
                lindex[entry] = self.__add_cmp_lists(pindex[entry], lindex[entry])

            logger.debug('...loading json file %s, done.' % path)

        if os.path.exists(path) and os.path.isdir(path):
            logger.debug('Loading %s from path %s...' % (name, path))
            for (dirpath, dirnames, filenames) in os.walk(path):
                for filename in filenames:
                    if not filename.endswith('.json'):
                        continue
                    fpath = os.path.join(dirpath, filename)
                    loadDB(fpath)
            logger.debug('...loading %s from path %s, done.' % (name, path))
        elif os.path.exists(path):
            logger.debug('Loading %s from path %s...' % (name, path))
            loadDB(path)
            logger.debug('...loading %s from path %s, done.' % (name, path))
        else:
            logger.error("Index %s: could not find path %s" % (name, path))
            return None

        return lindex

    # Provide a function to sort layer index content (restapi format)
    # When serializing the data this is import to limit
    # changes to the files...
    def sortEntry(self, item):
        newitem = item
        try:
            if type(newitem) == type(dict()):
                newitem = OrderedDict(sorted(newitem.items(), key=lambda t: t[0]))
            elif type(newitem) == type(list()):
                newitem.sort(key=lambda obj: obj['id'])
                for index, entry in enumerate(newitem):
                    newitem[index] = self.sortEntry(newitem[index])
        except:
            pass

        return newitem

    # Sort and return a new restapi style index
    def sortRestApi(self, index):
        lindex = self.sortEntry(index)
        for entry in lindex:
            lindex[entry] = self.sortEntry(lindex[entry])
        return lindex

    # layerBranches must be a list of layerBranch entries to parse, it only affects
    # output when 'split' is True.
    def serialize_index(self, lindex, path, split=False, layerBranches=None, IncludeCFG=False, mirror=False, base_url=None):
        # If we're not splitting, we must be caching...
        if not split:
            dir = os.path.dirname(path)
            base = os.path.basename(path)
            fname = base.translate(str.maketrans('/ ', '__'))
            fpath = os.path.join(dir, fname)

            # Need to filter out local information
            pindex = {}
            for entry in lindex:
                if (IncludeCFG == False and 'CFG' == entry) or 'apilinks' == entry:
                    continue
                pindex[entry] = lindex[entry]

            json.dump(self.sortRestApi(pindex), open(fpath + '.json', 'wt'), indent=4)
            return

        # We serialize based on the layerBranches, this allows us to subset
        # everything in a logical way...
        if not layerBranches:
            layerBranches = lindex['layerBranches']
        for lb in layerBranches:
            pindex = {}

            def filter_item(lb, objects):
                filtered = []
                for obj in lindex[objects]:
                    if 'layerbranch' in obj:
                        if obj['layerbranch'] == lb['id']:
                            filtered.append(obj)
                    elif 'layer' in obj:
                        for layer in self.find_layer(lindex, layerBranch=lb):
                            if  obj['layer'] == layer['id']:
                                filtered.append(obj)
                    else:
                        # No simple filter method, just include it...
                        filtered.append(obj)
                return filtered

            for entry in lindex:
                if (IncludeCFG == False and 'CFG' == entry) or 'apilinks' == entry or 'branches' == entry or 'layerBranches' == entry or 'layerItems' == entry:
                    continue
                elif (IncludeCFG == True and 'CFG' == entry):
                    pindex[entry] = lindex[entry]
                    continue
                pindex[entry] = filter_item(lb, entry)

            for branch in lindex['branches']:
                if branch['id'] == lb['branch']:
                    pindex['branches'] = [branch]

            # We must include the layerbranch for what we are processing...
            pindex['layerBranches'] = [lb]

            # We also need to include the layerbranch for any required dependencies...
            (required, recommended) = self.getDependencies(lindex, lb)
            for req_lb in required:
                found = False
                for p_lb in pindex['layerBranches']:
                    if p_lb['id'] == req_lb['id']:
                        found = True
                        break
                if found == False:
                    pindex['layerBranches'].append(req_lb)

            # We need to include the layerItems for each layerBranch
            pindex['layerItems'] = []
            for p_lb in pindex['layerBranches']:
                for li in self.find_layer(lindex, layerBranch=p_lb):
                    found = False
                    for p_li in pindex['layerItems']:
                        if p_li['id'] == li['id']:
                            found = True
                            break
                    if found == False:
                        pindex['layerItems'].append(li)

            # If we're mirroring, we need to adjust the URL for the
            # mirror to work properly.  Replace remote with BASE_URL.
            # (This uses the same logic as the default.xml construction)
            if mirror == True:
                from urllib.parse import urlparse

                from copy import deepcopy
                pindex['layerItems'] = deepcopy(pindex['layerItems'])
                for layer in pindex['layerItems']:
                    vcs_url = layer['vcs_url']

                    if base_url and vcs_url.startswith(base_url):
                        layer['vcs_url'] = layer['vcs_url'].replace(base_url, '#BASE_URL#')
                    else:
                        url = urlparse(vcs_url)

                        if url.scheme:
                            layer['vcs_url'] = layer['vcs_url'].replace(url.scheme + '://' + url.netloc, '#BASE_URL#')

            dir = os.path.dirname(path)
            base = os.path.basename(path)
            fname = base + '__' + pindex['branches'][0]['name'] + '__' + pindex['layerItems'][0]['name']
            fname = fname.translate(str.maketrans('/ ', '__'))
            fpath = os.path.join(dir, fname)

            json.dump(self.sortRestApi(pindex), open(fpath + '.json', 'wt'), indent=4)

    # layerBranches must be a list of layerBranch entries to parse, it only affects
    # output when 'split' is True.
    def serialize_django_export(self, lindex, path, split=False, layerBranches=None, IncludeCFG=False):
        def convertToDjango(restindex):
            dbindex = []

            def constructObject(entry, model):
                obj = OrderedDict()
                obj['pk'] = entry['id']
                obj['model'] = model
                obj['fields'] = OrderedDict(sorted(entry.items(), key=lambda t: t[0]))
                del obj['fields']['id']

                if model == 'layerindex.branch' and 'update_environment' in obj['fields']:
                    if 'pythonenvironment' not in restindex:
                        # We have 'lost' the environment, so workaround it being missing...
                        obj['fields']['update_environment'] = None

                return obj

            # Convert the restindex to a dbindex
            for entry in restindex:
                if (IncludeCFG == False and 'CFG' == entry) or 'apilinks' == entry:
                    continue
                elif 'branches' == entry:
                    model = 'layerindex.branch'
                elif 'layerItems' == entry:
                    model = 'layerindex.layeritem'
                elif 'layerBranches' == entry:
                    model = 'layerindex.layerbranch'
                elif 'layerDependencies' == entry:
                    model = 'layerindex.layerdependency'
                elif 'recipes' == entry:
                    model = 'layerindex.recipe'
                elif 'machines' == entry:
                    model = 'layerindex.machine'
                elif 'distros' == entry:
                    model = 'layerindex.distro'
                elif 'wrtemplates' == entry:
                    model = 'layerindex.wrtemplate'
                else:
                    model = 'layerindex.' + entry

                for item in restindex[entry]:
                    dbindex.append(constructObject(item, model))

            return dbindex

        # Just write out a single master file..
        if not split:
            dir = os.path.dirname(path)
            base = os.path.basename(path)
            fname = base.translate(str.maketrans('/ ', '__'))
            fpath = os.path.join(dir, fname)

            # Need to filter out local information
            pindex = {}
            for entry in lindex:
                if (IncludeCFG == False and 'CFG' == entry) or 'apilinks' == entry:
                    continue
                pindex[entry] = lindex[entry]

            json.dump(convertToDjango(self.sortRestApi(pindex)), open(fpath + '.json', 'wt'), indent=4)
            return

        # We serialize based on the layerBranches, this allows us to subset
        # everything in a logical way...
        if not layerBranches:
            layerBranches = lindex['layerBranches']
        for lb in layerBranches:
            pindex = {}

            def filter_item(lb, objects):
                filtered = []
                for obj in lindex[objects]:
                    if 'layerbranch' in obj:
                        if obj['layerbranch'] == lb['id']:
                            filtered.append(obj)
                    elif 'layer' in obj:
                        for layer in self.find_layer(lindex, layerBranch=lb):
                            if obj['layer'] == layer['id']:
                                filtered.append(obj)
                    else:
                        # No simple filter method, just include it...
                        filtered.append(obj)
                return filtered

            for entry in lindex:
                if (IncludeCFG == False and 'CFG' == entry) or 'apilinks' == entry or 'branches' == entry or 'layerBranches' == entry or 'layerItems' == entry:
                    continue
                pindex[entry] = filter_item(lb, entry)

            pindex['layerBranches'] = [lb]
            pindex['layerItems'] = self.find_layer(lindex, layerBranch=lb)

            for branch in lindex['branches']:
                if branch['id'] == lb['branch']:
                    pindex['branches'] = [branch]

            dir = os.path.dirname(path)
            base = os.path.basename(path)
            fname = base + '__' + pindex['branches'][0]['name'] + '__' + pindex['layerItems'][0]['name']
            fname = fname.translate(str.maketrans('/ ', '__'))
            fpath = os.path.join(dir, fname)

            json.dump(convertToDjango(self.sortRestApi(pindex)), open(fpath + '.json', 'wt'), indent=4)


    def find_layer(self, lindex, id=None, name=None, layerBranch=None, layerBranchId=None, distro=None, machine=None, recipe=None, wrtemplate=None):
        result = []

        if layerBranch:
            id = layerBranch['layer']

        # Only one layerItem per lindex, so break once we find it
        if id:
            for layer in lindex['layerItems']:
                if layer['id'] == id:
                    result.append(layer)
                    break
            return result

        if name:
            for layer in lindex['layerItems']:
                if layer['name'] == name:
                    result.append(layer)
                    break
            return result

        layerBranchIds = []
        if layerBranchId:
            layerBranchIds.append(layerBranchId)

        if distro:
            for dist in lindex['distros']:
                if dist['name'] == distro:
                    layerBranchIds.append(dist['layerbranch'])

        if machine:
            for mach in lindex['machines']:
                if mach['name'] == machine:
                    layerBranchIds.append(mach['layerbranch'])

        if recipe:
            for rec in lindex['recipes']:
                if rec['pn'] == recipe:
                    layerBranchIds.append(rec['layerbranch'])

        if wrtemplate:
            for tmpl in lindex['wrtemplates']:
                if tmpl['name'] == wrtemplate:
                    layerBranchIds.append(tmpl['layerbranch'])

        if layerBranchIds:
            for layerBranch in lindex['layerBranches']:
                for layerBranchId in layerBranchIds:
                    if layerBranch['id'] == layerBranchId:
                        for layer in lindex['layerItems']:
                            if layer['id'] == layerBranch['layer']:
                                result.append(layer)
            return result

        return None

    def list_layers(self, base_branch):
        import unicodedata
        for lindex in self.index:
            logger.plain ('Index: %s' % (lindex['CFG']['DESCRIPTION'] or lindex['CFG']['URL']))
            logger.plain ('%s %s' % (('{:25}'.format('layer'), 'summary')))
            logger.plain ('{:-^80}'.format(""))
            branchid = self.getBranchId(lindex, self.getIndexBranch(default=base_branch, lindex=lindex))
            if branchid:
                for lb in lindex['layerBranches']:
                    if lb['branch'] == branchid:
                        for layer in self.find_layer(lindex, layerBranch=lb):
                            name = layer['name']
                            summary = layer['summary'] or name
                            logger.plain('%s %s' % ('{:25}'.format(name), summary[:52]))
            logger.plain ('')

    def list_obj(self, base_branch, object, display):
        for lindex in self.index:
            logger.plain ('Index: %s' % (lindex['CFG']['DESCRIPTION'] or lindex['CFG']['URL']))
            logger.plain ('%s %s %s' % (('{:24}'.format(display), '{:34}'.format('description'), '{:19}'.format('layer'))))
            logger.plain ('{:-^80}'.format(""))
            branchid = self.getBranchId(lindex, self.getIndexBranch(default=base_branch, lindex=lindex))
            if branchid:
                # there are more layerBranches then objects (usually)...
                for lb in lindex['layerBranches']:
                    for layer in self.find_layer(lindex, layerBranch=lb):
                        for obj in lindex[object]:
                            if obj['layerbranch'] == lb['id'] and lb['branch'] == branchid:
                                lname = layer['name']
                                name = obj['name']
                                description = (obj['description'] or name).strip()
                                logger.plain('%s %s %s' % ('{:24}'.format(name), '{:34}'.format(description[:34]), lname))
            logger.plain ('')

    def list_distros(self, base_branch):
        self.list_obj(base_branch, 'distros', 'distro')

    def list_machines(self, base_branch):
        self.list_obj(base_branch, 'machines', 'machine')

    def list_wrtemplates(self, base_branch):
        self.list_obj(base_branch, 'wrtemplates', 'templates')

    def list_recipes(self, base_branch):
        for lindex in self.index:
            logger.plain ('Index: %s' % (lindex['CFG']['DESCRIPTION'] or lindex['CFG']['URL']))
            logger.plain ('%s %s %s' % (('{:15}'.format('recipe'), '{:9}'.format('version'), 'summary')))
            logger.plain ('{:-^80}'.format(""))
            branchid = self.getBranchId(lindex, self.getIndexBranch(default=base_branch, lindex=lindex))
            if branchid:
                # there are more layerBranches then objects (usually)...
                for lb in lindex['layerBranches']:
                    for layer in self.find_layer(lindex, layerBranch=lb):
                        for obj in lindex['recipes']:
                            if obj['layerbranch'] == lb['id'] and lb['branch'] == branchid:
                                lname = layer['name']
                                pn = obj['pn']
                                pv = obj['pv']
                                summary = (obj['summary'] or pn).strip()
                                logger.plain('%s %s %s' % ('{:15}'.format(pn), '{:9}'.format(pv), summary[:50]))
            logger.plain ('')

    def getBranchId(self, lindex, name):
        for branch in lindex['branches']:
            if branch['name'] == name:
                return branch['id']
        return None

    def getLayerBranch(self, lindex, branchid, layerBranchId=None, collection=None, name=None, distro=None, machine=None, recipe=None, wrtemplate=None, layerItem=None):
        result = []
        if layerBranchId:
            for lb in lindex['layerBranches']:
                if branchid == lb['branch'] and layerBranchId == lb['id']:
                    result.append(lb)
                    break
            return result

        if collection:
            for lb in lindex['layerBranches']:
                if 'collection' in lb and collection == lb['collection']:
                    result.append(lb)
                    break
            return result

        layerItems = []
        if layerItem:
            layerItems.append(layerItem)

        if name:
            layerItem = self.find_layer(lindex, name=name)
            if layerItem:
                layerItems = layerItems + layerItem

        if distro:
            layerItem = self.find_layer(lindex, distro=distro)
            if layerItem:
                layerItems = layerItems + layerItem

        if machine:
            layerItem = self.find_layer(lindex, machine=machine)
            if layerItem:
                layerItems = layerItems + layerItem

        if recipe:
            layerItem = self.find_layer(lindex, recipe=recipe)
            if layerItem:
                layerItems = layerItems + layerItem

        if wrtemplate:
            layerItem = self.find_layer(lindex, wrtemplate=wrtemplate)
            if layerItem:
                layerItems = layerItems + layerItem

        if layerItems:
            for layerItem in layerItems:
                for lb in lindex['layerBranches']:
                    if branchid == lb['branch'] and layerItem['id'] == lb['layer']:
                        result.append(lb)
            return result

        return None

    def getDependencies(self, lindex, layerBranch):
        required = []
        recommended = []
        for ld in lindex['layerDependencies']:
            if layerBranch['id'] == ld['layerbranch']:
                layers = self.find_layer(lindex, id=ld['dependency'])
                if (not layers or layers == []) and ld['required'] == True:
                    logger.warning('%s: Unable to find dependency %s -- Skipping' % (self.find_layer(lindex, layerBranch=layerBranch)[0]['name'], ld['dependency']))
                for layer in layers:
                    for lb in self.getLayerBranch(lindex, layerBranch['branch'], layerItem=layer):
                        if not lb:
                            continue
                        if not 'required' in ld or ld['required'] == True:
                            #print('li_getdep_dep: %s (%s) req %s (%s)' % (self.find_layer(lindex, layerBranch=layerBranch)['name'], layerBranch['id'], self.find_layer(lindex, layerBranch=lb)['name'], ld['dependency']) )
                            required.append(lb)
                        else:
                            #print('li_getdep_dep: %s (%s) rec %s (%s)' % (self.find_layer(lindex, layerBranch=layerBranch)['name'], layerBranch['id'], self.find_layer(lindex, layerBranch=lb)['name'], ld['dependency']) )
                            recommended.append(lb)

        return (required, recommended)

    def getLayerInfo(self, lindex, layerBranch):
        collection = None
        name = None
        vcs_url = None
        if 'collection' in layerBranch:
            collection = layerBranch['collection']
        for layer in self.find_layer(lindex, layerBranch=layerBranch):
            if layer:
                name = layer['name']
                vcs_url = layer['vcs_url']
                break

        return (collection, name, vcs_url)

    def getBranch(self, lindex, branchid):
        for branch in lindex['branches']:
            if branch['id'] == branchid:
                return branch
        return None

    def getBitbakeBranch(self, lindex, branchid):
        branch = self.getBranch(lindex, branchid)
        if branch:
            return branch['bitbake_branch'] or branch['name']
        return None

    def getIndexBranch(self, default=None, lindex=None):
        if lindex and 'CFG' in lindex and 'BRANCH' in lindex['CFG']:
            return lindex['CFG']['BRANCH']
        return default
