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

# This will export the layer index cache so it can be imported into
# a stand-a-lone layerindex-Web session
#
# You will need to adjust the items below...
#
# run this program w/ the CWD of wrlinux-x, or adjust the INDEXES settings
#
# output file will be /tmp/output.json
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
# cp /tmp/output/<name>.json layerindex/fixtures/.
# python3 manage.py loaddata <name>.json
#
# To start webserver
# python3 manage.py runserver

import os
import sys

REPLACE = [
            ( '#BASE_URL#', 'git://git.wrs.com/' ),
          ]

INDEXES = [
    {
        'DESCRIPTION' : 'Wind River Linux Index',
        'TYPE' : 'export',
        'URL' : 'data/index',
        'CACHE' : None,
    },
]

OUTPUT = '/tmp/output'

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
