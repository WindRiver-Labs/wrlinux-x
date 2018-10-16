#!/usr/bin/env python3

# Copyright (C) 2017 Wind River Systems, Inc.
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

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

#
# TODO
# - Multiple Indexes
# - Multiple bitbakes
# - Multiple remotes
#

# Get the 'setup.py' default settings (BASE_LAYERS, DEFAULT_DISTRO, ...)
import settings

# Global variables
top_layers=[]   # list of top layers
list_layers=[]  # list of top and dependent layers
json_dct={}     # layer index json cache
xmltree=None    # default.xml object

# Add 'layer index' type layer_branch records
TYPE_LAYERINDEX = 1

# Insert custom settings starting at 100
CUSTOM_SETTINGS_BASE=100

# Toaster fixture file's relative path from install directory
FIXTURE_FILE='layers/oe-core/bitbake/lib/toaster/orm/fixtures/custom.xml'

# Do not include optional layers in default layer list
INCLUDE_DEFAULT_LAYERS=False

############################################
### formatted output

def add_field(obj,attr_list,value):
    field = ET.SubElement(obj, "field")
    for attr in attr_list:
        field.set(attr[0], attr[1])
    field.text = value

def write_prolog():
    global root
    root = ET.Element("django-objects")
    root.set('version', '1.0')

def append_setting(name,value,pk):
    global root
    obj = ET.SubElement(root, "object")
    obj.set('model', 'orm.toastersetting')
    obj.set('pk', str(pk))
    add_field(obj,[('type','CharField'),('name', 'name')],name)
    add_field(obj,[('type','CharField'),('name', 'value')],value)
    return pk+1

def append_bitbake(name,giturl,branch,pk):
    global root
    obj = ET.SubElement(root, "object")
    obj.set('model', 'orm.bitbakeversion')
    obj.set('pk', str(pk))
    add_field(obj,[('type','CharField'),('name', 'name')],name)
    add_field(obj,[('type','CharField'),('name', 'giturl')],giturl)
    add_field(obj,[('type','CharField'),('name', 'branch')],branch)
    add_field(obj,[('type','CharField'),('name', 'dirpath')],'')
    return pk+1

def append_releases(name,desc,bitbake_version,branch,help):
    global root
    obj = ET.SubElement(root, "object")
    obj.set('model', 'orm.release')
    obj.set('pk', '1')
    add_field(obj,[('type','CharField'),('name', 'name')],name)
    add_field(obj,[('type','CharField'),('name', 'description')],desc)
    add_field(obj,[('rel','ManyToOneRel'),('to','orm.bitbakeversion'),('name', 'bitbake_version')],str(bitbake_version))
    add_field(obj,[('type','CharField'),('name', 'branch_name')],branch)
    add_field(obj,[('type','TextField'),('name', 'helptext')],help)

def write_default_layer_release(release,pk):
    global root
    for layer in list_layers:
        obj = ET.SubElement(root, "object")
        obj.set('model', 'orm.releasedefaultlayer')
        obj.set('pk', str(pk))
        add_field(obj,[('rel','ManyToOneRel'),('to','orm.release'),('name', 'release')],str(release))
        add_field(obj,[('type','CharField'),('name', 'layer_name')],layer)
        pk += 1
    return pk

def write_layer_release(layer_pk,layer_version_pk,layer_source):
    global root
    layers = json_dct["layerItems"]
    for layer_name in list_layers:
        for layer in layers:
            if layer_name == layer["name"]:
                break
        else:
            print("ERROR: Layer Name '%s' in not found" % layer_name)
            return
        obj = ET.SubElement(root, "object")
        obj.set('model', 'orm.layer')
        obj.set('pk', str(layer_pk))
        add_field(obj,[('type','CharField'),('name', 'name')],layer['name'])
        add_field(obj,[('type','CharField'),('name', 'layer_index_url')],'')
        add_field(obj,[('type','CharField'),('name', 'vcs_url')],layer['vcs_url'])

        # for release in releases:
        layer_id=layer["id"]
        for release in range(1, 2):
            layerBranches = json_dct["layerBranches"]
            for layer_branch in layerBranches:
                if layer_id == layer_branch["layer"]:
                    break
            else:
                print("ERROR: LayerId '%d' in layerBranches not found" % layer_id)
                return
            obj = ET.SubElement(root, "object")
            obj.set('model', 'orm.layer_version')
            obj.set('pk', str(layer_version_pk))
            add_field(obj,[('rel','ManyToOneRel'),('to','orm.layer'),('name', 'layer')],str(layer_pk))
            add_field(obj,[('type','IntegerField'),('name', 'layer_source')],str(layer_source))
            add_field(obj,[('rel','ManyToOneRel'),('to','orm.release'),('name', 'release')],str(release))
            add_field(obj,[('type','CharField'),('name', 'branch')],layer_branch['actual_branch'])
            add_field(obj,[('type','CharField'),('name', 'dirpath')],layer_branch['vcs_subdir'])
            layer_version_pk+=1
        layer_pk+=1
    return layer_pk,layer_version_pk

def write_epilog():
    parsed = minidom.parseString(ET.tostring(root, 'utf-8'))
    print(parsed.toprettyxml(indent="  "),file=output_fd)

############################################
### worker functions

def read_default_xml(xml_file):
    xmltree = ET.parse(xml_file)
    xmlroot = xmltree.getroot()
    remote_base=None
    remote_base_revision=None
    bitbake_branch=None
    bitbake_path=None
    for child in xmlroot:
        if 'remote' == child.tag and 'base' == child.attrib['name']:
            remote_base_fetch = child.attrib['fetch']
        if 'default' == child.tag and 'base' == child.attrib['remote']:
            remote_base_revision = child.attrib['revision']
        if 'default' == child.tag and 'base' == child.attrib['remote']:
            remote_base_revision = child.attrib['revision']
        if 'project' == child.tag and child.attrib['name'].endswith('bitbake'):
            bitbake_branch = child.attrib['revision']
            bitbake_path=child.attrib['name']
    return remote_base_fetch,remote_base_revision,bitbake_branch,bitbake_path

def read_layer_index_cache(json_cache):
    global json_dct
    with open(json_cache,"r") as json_data:
        json_dct = json.load(json_data)

def find_layer2id(layer_name):
    layers = json_dct["layerItems"]
    for layer in layers:
        if layer_name == layer["name"]:
            return layer["id"]
    return None

def find_id2layer(layer_id):
    layers = json_dct["layerItems"]
    for layer in layers:
        if layer_id == layer["id"]:
            return layer["name"]
    return None

def find_layerBranch2layer(layerBranch_id):
    layers = json_dct["layerItems"]
    layerBranches = json_dct["layerBranches"]
    for layerBranch in layerBranches:
        if layerBranch_id == layerBranch["id"]:
            layer_id=layerBranch["layer"]
            for layer in layers:
                if layer_id == layer["id"]:
                    return layer["name"]
    return None

def find_layer2layerBranch(layer):
    layerBranches = json_dct["layerBranches"]
    layer_id=find_layer2id(layer)
    if None == layer_id:
        print("ERROR: Index for layer '%s' not found" % add_layer)
        return None
    for layerBranch in layerBranches:
        if layer_id == layerBranch["layer"]:
            layer_branch_id=layerBranch["id"]
            break
    else:
        print("ERROR: layerbranch layer '%d' not found" % layer_id)
        return None
    return layer_id,layer_branch_id

def add_machine_layers(add_machine):
    global top_layers
    machines = json_dct["machines"]
    for machine in machines:
        if add_machine == machine["name"]:
            layerBranch_id = machine["layerbranch"]
            layer = find_layerBranch2layer(layerBranch_id)
            if None == layer:
                print("ERROR: Layer '%s' for machine '%s' not found" % (layer,add_machine))
            else:
                top_layers.append(layer)

def add_distro_layers(add_distro):
    global top_layers
    distros = json_dct["distros"]
    for distro in distros:
        if add_distro == distro["name"]:
            layerBranch_id = distro["layerbranch"]
            layer = find_layerBranch2layer(layerBranch_id)
            if None == layer:
                print("ERROR: Layer '%s' for distro '%s' not found" % (layer,add_distro))
            else:
                top_layers.append(layer)

def add_dependent_layers(add_layer,include_optional):
    global list_layers
    layers = json_dct["layerItems"]
    layerBranches = json_dct["layerBranches"]
    layerDependencies = json_dct["layerDependencies"]

    # do we already have this layer?
    if add_layer in list_layers:
        return

    # find layer ID
    layer_id,layer_branch_id = find_layer2layerBranch(add_layer)
    # find dependent layers
    for dep in layerDependencies:
        if not include_optional and not dep['required']:
            continue
        if layer_branch_id == dep['layerbranch']:
            dep_layer=find_id2layer(dep["dependency"])
            if None == dep_layer:
                print("ERROR: Index to dep layer '%d' not found" % dep_id)
            else:
                add_dependent_layers(dep_layer,include_optional)

    # add layers depth first, top last
    list_layers.append(add_layer)

############################################
### main()

def main(argv):
    global top_layers
    global list_layers
    global output_fd
    global root

    parser = argparse.ArgumentParser(description='toaster_fixture.py: create Toaster fixture file from setup output')
    parser.add_argument('--project-dir', dest='project_dir',help='Project Directory')
    parser.add_argument('--verbose', '-v', action='store_true', dest='verbose',help='Verbose mode')
    args = parser.parse_args()

    # Core paths
    script_dir=os.path.dirname(os.path.abspath(argv[0]))
    wrlinux_dir=os.path.dirname(script_dir)
    if args.project_dir:
        install_dir = args.project_dir
    else:
        install_dir = os.getcwd()

    # Read setup default.xml data
    default_xml_file=os.path.join(install_dir,'default.xml')
    if not os.path.exists(default_xml_file):
        print("ERROR: 'default.xml' does not exist. You need to run the 'setup' program.")
        exit(-1)
    else:
        remote_base_fetch,remote_base_revision,bitbake_branch,bitbake_path=read_default_xml(default_xml_file)
        bitbake_url=os.path.join(remote_base_fetch,bitbake_path)

    # Load layer index cache
    json_cache=os.path.join(install_dir,settings.INDEXES[0]['CACHE']+'.json')
    read_layer_index_cache(json_cache)

    # Discover the XML directory
    xml_dir=os.path.join(wrlinux_dir,'data/xml')
    if os.path.exists(os.path.join(install_dir,'config','mirror-index','xml')):
        xml_dir=os.path.join(install_dir,'config','mirror-index','xml')

    # Prepare the output file
    output_fd=open(os.path.join(install_dir,FIXTURE_FILE), 'w')
    write_prolog()

    # Write Toaster environment hints
    #   1. Point Toaster to the wrlinux-x directory
    root.append(ET.Comment(' HINT:WRLINUX_DIR="%s" ' % wrlinux_dir))

    # Write default setting overrides
    root.append(ET.Comment(' Set the project default values '))

    append_setting('DEFCONF_DISTRO',settings.DEFAULT_DISTRO,1)
    append_setting('DEFAULT_RELEASE',remote_base_revision,2)
    append_setting('DEFCONF_MACHINE',settings.DEFAULT_MACHINE,4)
    # append custom settings
    setting_pk=CUSTOM_SETTINGS_BASE
    setting_pk=append_setting('DEFCONF_LINUX_KERNEL_TYPE','standard',setting_pk)
    setting_pk=append_setting('DEFAULT_KTYPE_LIST','standard preempt-rt tiny',setting_pk)
    setting_pk=append_setting('CUSTOM_LAYERINDEX_SERVER','file://'+json_cache,setting_pk)
    setting_pk=append_setting('SETUP_XMLDIR',xml_dir,setting_pk)
    setting_pk=append_setting('SETUP_GITURL',remote_base_fetch,setting_pk)
    setting_pk=append_setting('SETUP_PATH_FILTER','s|layers/[a-zA-Z0-9_\\-.]*||',setting_pk)

    # Write bitbake version
    root.append(ET.Comment(' Bitbake versions which correspond to the metadata release '))
    bitbake_pk=1
    bitbake_pk=append_bitbake(remote_base_revision,bitbake_url,bitbake_branch,bitbake_pk)

    # Write releases
    root.append(ET.Comment(' Releases available '))
    append_releases(remote_base_revision,"Wind River Linux " + remote_base_revision,1,remote_base_revision,
        "Toaster will run your builds using the tip of the Wind River Linux '%s' branch." % remote_base_revision)

    # Write base default layers
    for layer in settings.BASE_LAYERS.split():
        top_layers.append(layer)

    # Write DEFAULT_MACHINE layer
    add_machine_layers(settings.DEFAULT_MACHINE)

    # Write DEFAULT_DISTRO layer
    add_distro_layers(settings.DEFAULT_DISTRO)

    # Resolve dependent layers, exclude optional layers
    for layer in top_layers:
        add_dependent_layers(layer,INCLUDE_DEFAULT_LAYERS)

    # Write default layer list per release
    root.append(ET.Comment(' Default project layers for each release '))
    default_layers_pk=1
    default_layers_pk=write_default_layer_release(1,default_layers_pk)

    # Write layer list
    root.append(ET.Comment(' Default layers from wrlinux defaults '))
    layer_pk,layer_version_pk = write_layer_release(1,1,TYPE_LAYERINDEX)

    write_epilog()
    output_fd.close()

    if args.verbose:
        print("Done:")
        print("  Layers=%d, LayerRelease=%d, LayerVersions=%d, Custom Settings=%d" % (len(list_layers),layer_pk,layer_version_pk,setting_pk-CUSTOM_SETTINGS_BASE))
        print("  Default Layers=%s" % list_layers)


if __name__ == '__main__':
    main(sys.argv)
