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

# type, url/path, description, cache
# type:  restapi-web   - REST API from a LayerIndex-web
#        restapi-files - REST API, but only from files
#        export        - Exported DB from a LayerIndex-web -- reads file(s)

logger = logger_setup.setup_logging()
class Layer_Index():
    # Index in REST-API format...  This is used by external items.
    index = []

    def __init__(self, indexcfg, base_branch, replace=[]):
        self.index = []

        for cfg in indexcfg:
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

            if indextype == 'restapi-web':
                if branch:
                    lindex = self.load_API_Index(indexurl, indexname, branches=[branch])
                else:
                    lindex = self.load_API_Index(indexurl, indexname, branches=None)
            elif indextype == 'restapi-files':
                lindex = self.load_serialized_index(indexurl, name=indexname)
            elif indextype == 'export':
                lindex = self.load_django_export(indexurl, name=indexname)
            else:
                # Unknown index type...
                logger.error('Unknown index type  %s' % indextype)
                raise SyntaxError

            # Cache the data we loaded... if we loaded data.
            if lindex and indexcache:
                dir = os.path.dirname(indexcache)
                if dir:
                    os.makedirs(dir, exist_ok=True)
                self.serialize_index(lindex, indexcache, split=False)

            # If we couldn't pull from the regular location, pull from the cache!
            if lindex is None and indexcache and os.path.exists(indexcache + '.json'):
                lindex = self.load_serialized_index(indexcache, name=indexname, branches=[branch])

            if not lindex or 'branches' not in lindex or 'layerItems' not in lindex or 'layerBranches' not in lindex:
                # It's empty, skip it...
                continue

            # Start data transforms...
            lindex['CFG'] = cfg

            if lindex and 'distros' in lindex:
                # Default setup is actually implemented as 'nodistro'
                for (idx, dist) in enumerate(lindex['distros']):
                    if dist['name'] == "defaultsetup":
                        dist['name'] = 'nodistro'
                        lindex['distros'][idx] = dist

            for entry in lindex['layerItems']:
                for obj in entry:
                    # Run replace on any 'url' items.
                    if 'url' in obj:
                        vcs_url = entry[obj]
                        for (find, rep) in replace:
                            vcs_url = vcs_url.replace(find, rep)
                        entry[obj] = vcs_url

            # Everything works off layerBranches, so make sure to keep it sorted!
            lindex['layerBranches'] = self.sortEntry(lindex['layerBranches'])

            if lindex:
                self.index.append(lindex)


    def load_API_Index(self, url, name=None, branches=None):
        """
            Fetches layer information from a remote layer index.
            The return value is a dictionary containing API, branch,
            layer, branch, dependency, recipe, machine, distro,
            and template information.

            url is the url to the rest api of the layer index, such as:
            http://layers.openembedded.org/layerindex/api/

            branches is a list of branches to filter on
        """
        lindex = {}

        assert url is not None

        logger.plain('Loading %s from url %s...' % (name, url))

        try:
            from urllib.request import urlopen, URLError
            from urllib.parse import urlparse
        except ImportError:
            from urllib2 import urlopen, URLError
            from urlparse import urlparse

        proxy_settings = os.environ.get("http_proxy", None)

        def _get_json_response(apiurl=None):
            assert apiurl is not None

            logger.debug("Fetching %s..." % apiurl)

            _parsedurl = urlparse(apiurl)
            path = _parsedurl.path

            try:
                res = urlopen(apiurl)
            except URLError as e:
                raise Exception("Failed to read %s: %s" % (path, e.reason))

            parsed = json.loads(res.read().decode('utf-8'))

            logger.debug("done.")
            return parsed

        try:
            lindex['apilinks'] = _get_json_response(url)
        except Exception as e:
            import traceback
            if proxy_settings is not None:
                logger.error("Using proxy %s" % proxy_settings)
            logger.error("Index %s: could not connect to %s:"
                      "%s\n%s" % (name, url, e, traceback.format_exc()))
            return None

        filter = ""
        if branches:
            filter = "?filter=name:%s" \
                     % "OR".join(branches)
        lindex['branches'] = _get_json_response(lindex['apilinks']['branches'] + filter)

        if not lindex['branches']:
            logger.info("No valid branches (%s) found at url %s." % (branches or "", url))
            return lindex

        filter = ""
        if branches:
            filter = "?filter=branch__name:%s" \
                     % "OR".join(branches)
        lindex['layerBranches'] = _get_json_response(lindex['apilinks']['layerBranches'] + filter)
        if not lindex['layerBranches']:
            logger.info("No layers on branches (%s) found at url %s." % (branches or "", url))
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

        logger.plain('done.')

        return lindex

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

        def add_cmp_lists(listone, listtwo):
            # Copy the items from listone, into listtwo -- if it isn't already
            # there..  if it is there, verify it's the same or raise an error...
            if not listone:
                return listtwo

            for one in reversed(listone):
                found = False
                for two in listtwo:
                    if one['id'] == two['id']:
                        found = True
                        # Contents need to be the same!
                        if one != two:
                            # Something is out of sync here...
                            raise
                        break
                if not found:
                    listtwo.append(one)
            return listtwo

        def loadCache(path):
            logger.debug('Loading json file %s' % path)
            pindex = json.load(open(path, 'rt', encoding='utf-8'))

            for entry in pindex:
                if 'CFG' == entry or 'apilinks' == entry:
                    lindex[entry] = pindex[entry]
                    continue
                if entry not in lindex:
                    lindex[entry] = []
                lindex[entry] = add_cmp_lists(pindex[entry], lindex[entry])

            logger.debug('done.')

        if os.path.exists(path) and os.path.isdir(path):
            logger.info('Loading %s from path %s...' % (name, path))
            for (dirpath, dirnames, filenames) in os.walk(path):
                for filename in filenames:
                    if not filename.endswith('.json'):
                        continue
                    fpath = os.path.join(dirpath, filename)
                    loadCache(fpath)
            logger.info('done.')
        elif os.path.exists(path):
            logger.info('Loading %s from path %s...' % (name, path))
            loadCache(path)
            logger.info('done.')
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

        def add_cmp_lists(listone, listtwo):
            # Copy the items from listone, into listtwo -- if it isn't already
            # there..  if it is there, verify it's the same or raise an error...
            if not listone:
                return listtwo

            for one in reversed(listone):
                found = False
                for two in listtwo:
                    if one['id'] == two['id']:
                        found = True
                        # Contents need to be the same!
                        if one != two:
                            # Something is out of sync here...
                            raise
                        break
                if not found:
                    listtwo.append(one)
            return listtwo

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
                lindex[entry] = add_cmp_lists(pindex[entry], lindex[entry])

            logger.debug('done.')

        if os.path.exists(path) and os.path.isdir(path):
            logger.info('Loading %s from path %s...' % (name, path))
            for (dirpath, dirnames, filenames) in os.walk(path):
                for filename in filenames:
                    if not filename.endswith('.json'):
                        continue
                    fpath = os.path.join(dirpath, filename)
                    loadDB(fpath)
            logger.info('done.')
        elif os.path.exists(path):
            logger.info('Loading %s from path %s...' % (name, path))
            loadDB(path)
            logger.info('done.')
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

    def serialize_index(self, lindex, path, split=False):
        # If we're not splitting, we must be caching...
        if not split:
            dir = os.path.dirname(path)
            base = os.path.basename(path)
            fname = base.translate(str.maketrans('/ ', '__'))
            fpath = os.path.join(dir, fname)

            # Need to filter out local information
            pindex = {}
            for entry in lindex:
                if 'CFG' == entry or 'apilinks' == entry:
                    continue
                pindex[entry] = lindex[entry]

            json.dump(self.sortRestApi(pindex), open(fpath + '.json', 'wt'), indent=4)
            return

        # We serialize based on the layerBranches, this allows us to subset
        # everything in a logical way...
        for lb in lindex['layerBranches']:
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
                if 'CFG' == entry or 'apilinks' == entry or 'branches' == entry or 'layerBranches' == entry or 'layerItems' == entry:
                    continue
                pindex[entry] = filter_item(lb, entry)

            for branch in lindex['branches']:
                if branch['id'] == lb['branch']:
                    pindex['branches'] = [branch]

            pindex['layerBranches'] = [lb]
            pindex['layerItems'] = self.find_layer(lindex, layerBranch=lb)

            dir = os.path.dirname(path)
            base = os.path.basename(path)
            fname = base + '__' + pindex['branches'][0]['name'] + '__' + pindex['layerItems'][0]['name']
            fname = fname.translate(str.maketrans('/ ', '__'))
            fpath = os.path.join(dir, fname)

            json.dump(self.sortRestApi(pindex), open(fpath + '.json', 'wt'), indent=4)

    def serialize_django_export(self, lindex, path, split=False):
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
                if 'CFG' == entry or 'apilinks' == entry:
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
                if 'CFG' == entry or 'apilinks' == entry:
                    continue
                pindex[entry] = lindex[entry]

            json.dump(convertToDjango(self.sortRestApi(pindex)), open(fpath + '.json', 'wt'), indent=4)
            return

        # We serialize based on the layerBranches, this allows us to subset
        # everything in a logical way...
        for lb in lindex['layerBranches']:
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
                if 'CFG' == entry or 'apilinks' == entry or 'branches' == entry or 'layerBranches' == entry or 'layerItems' == entry:
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

    def getLayerBranch(self, lindex, branchid, layerBranchId=None, name=None, distro=None, machine=None, recipe=None, wrtemplate=None, layerItem=None):
        result = []
        if layerBranchId:
            for lb in lindex['layerBranches']:
                if branchid == lb['branch'] and layerBranchId == lb['id']:
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
                for layer in self.find_layer(lindex, id=ld['dependency']):
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
