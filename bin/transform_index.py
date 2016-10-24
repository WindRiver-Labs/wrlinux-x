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

# This program allows you to transform layer index data from one source
# to a specific output format.  The output format can be in either restapi
# or django format.  It can be a single file, or split by layerbranch.
#
# You will need to adjust the items below to control the input/output
#
# OUTPUT - output directory to write file
#
# OUTPUT_FMT - restapi or django -- use Django for dataloads
#
# INDEXES - where to pull the data from
#
# REPLACES - what replacements to make on the -url- parts
#
# SPLIT - True or False, if True split the output


# The following will let us load a layer index from one source, and make
# it so we can load it into another for a stand-a-lone layerindex-Web
# session.
#
# Set OUTPUT_FMT to 'django'
# Set SPLIT to False
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

# This can also be used to take a database dump, either from the django DB
# or from the RestAPI and split the pieces for individual entitlement
# indexes.
#
# To get the input file, in your layerIndex run:
#   python3 manage.py dumpdata > /tmp/input.json
#
# By default the output will be organized by layerbranch in /tmp/output
#
# Split the results by base/bsp/addon
#
# example:
#   (cd /tmp/transform ; cp `grep layer_type * | grep -v \"B\" | cut -f 1 -d :` /home/mhatle/git/lpd/wrlinux-x/data/index/base/.)
#   (cd /tmp/transform ; cp `grep layer_type * | grep \"B\" | cut -f 1 -d :` /home/mhatle/git/lpd/wrlinux-x/data/index/bsps/.)
#

# We load from git.wrs.com and transform to msp-git.wrs.com
# Adjusting both the git URL and the webgit URL
REPLACE = [
            ( 'git://git.wrs.com/', '#BASE_URL#' ),
            ( 'http://git.wrs.com/cgit/', '#BASE_WEB#' ),
            ( '#BASE_URL#', 'git://msp-git.wrs.com/' ),
            ( '#BASE_WEB#', 'http://msp-git.wrs.com/cgi-bin/cgit.cgi/' ),
          ]

# Note the branch can be hard coded.  This is required only when you want
# to limit the branch from a restapi-web import.  (This does not do anything
# on other input formats.)
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
OUTPUT_FMT = 'django'
#OUTPUT_FMT = 'restapi'
SPLIT = False

import os
import sys

from layer_index import Layer_Index

index = Layer_Index(INDEXES, base_branch=None, replace=REPLACE)

for lindex in index.index:
    print('Dump %s as %s (split=%s)...' % (lindex['CFG']['DESCRIPTION'], OUTPUT_FMT, SPLIT))
    os.makedirs(OUTPUT, exist_ok=True)
    if OUTPUT_FMT == 'django':
        index.serialize_django_export(lindex, OUTPUT + '/' + lindex['CFG']['DESCRIPTION'], split=SPLIT)
    elif OUTPUT_FMT == 'restapi':
        index.serialize_index(lindex, OUTPUT + '/' + lindex['CFG']['DESCRIPTION'], split=SPLIT)
    else:
        print('Unknown output format!')

