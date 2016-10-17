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

# This will let us load a layer index from one source, and make
# it so we can load it into another for a stand-a-lone layerindex-Web
# session.
#
# You will need to adjust the items below...
#
# output file - see 'OUTPUT' below
#
# INDEXES - where to pull the data from
#
# REPLACES - what replacements to make on the -url- parts
#
# Once configured, run the program then follow the steps below...
#
# To setup a new layerindex-Web session:
#
# git clone git://git.wrs.com/tools/layerindex-web
# cd layerindex-web
# virtualenv -p python3 venv
# . ./venv/bin/activate
# pip3 install -r requirements.txt
#
# (configure settings.py -- see README)
#   I recommend (adjust paths as necessary):
#
#      USE_TZ = True
#
#      DEBUG = True
#
#      DATABASES = {
#          'default': {
#              'ENGINE': 'django.db.backends.sqlite3',
#              'NAME': '/home/mhatle/git/layerIndex/wr9-db',
#              'USER': '',
#              'PASSWORD': '',
#              'HOST': '',
#              'PORT': '',
#          }
#      }
#
#      SECRET_KEY = "<put something here>"
#
#      LAYER_FETCH_DIR = "/home/mhatle/git/layerIndex/wr9-layers"
#
#      BITBAKE_REPO_URL = "git://git.wrs.com/bitbake"
#
#
# python3 manage.py syncdb
#   # Answer yes to creating an admin user
# python3 manage.py migrate
#
# cp <OUTPUT>.json layerindex/fixtures/.
# python3 manage.py loaddata <name>.json
#
# To start webserver
# python3 manage.py runserver

# We load from git.wrs.com and transform to msp-git.wrs.com
# Adjusting both the git URL and the webgit URL
REPLACE = [
            ( 'git://git.wrs.com/', '#BASE_URL#' ),
            ( 'http://git.wrs.com/cgit/', '#BASE_WEB#' ),
            ( '#BASE_URL#', 'git://msp-git.wrs.com/' ),
            ( '#BASE_WEB#', 'http://msp-git.wrs.com/cgi-bin/cgit.cgi/' ),
          ]

# Note the WRLINUX_9_BASE branch is hard coded.  This is required only
# if useing the restapi-web for a transform
INDEXES = [
    {
        'DESCRIPTION' : 'Wind River Developer Layer Index',
        'TYPE' : 'restapi-web',
        'URL' : 'http://layers.wrs.com/layerindex/api/',
        'CACHE' : None,
        'BRANCH' : 'WRLINUX_9_BASE',
    },
]

OUTPUT = '/tmp/transform'


import os
import sys

from layer_index import Layer_Index

index = Layer_Index(INDEXES, base_branch="")

for lindex in index.index:
    for entry in lindex['layerItems']:
        for obj in entry:
            # Run replace on any 'url' items.
            if 'url' in obj:
                vcs_url = entry[obj]
                for (search, replace) in REPLACE:
                    vcs_url = vcs_url.replace(search, replace)
                entry[obj] = vcs_url

    os.makedirs(OUTPUT, exist_ok=True)
    index.serialize_django_export(lindex, OUTPUT + '/' + lindex["name"], split=False)
