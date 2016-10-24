wrlinux-9 setup
===============

With this tool you can either create a new distribution builder project, or
create a mirror that other projects can be based on.

The tool uses a layer index (such as layers.openembedded.org), as specified in
the bin/settings.py file, to determine what layers are required to construct
a distribution builder project.

The tool relies on 'repo' from the Android 'git-repo' project.  It produces
a repo style 'default.xml' file, and then calls repo to download all of
the layer components necessary.

The tool also configures various sample files that are used by 
oe-init-build-env to construct your build directory.


Workflows
---------

Basic setup/usage workflow:

The setup program is expected to have been cloned inside of a project
directory, such as:

$ mkdir my-project
$ cd my-project
$ git clone --branch <branch> <url> wrlinux-9

Once cloned, simply run the setup.sh (./wrlinux-9/setup.sh) to get a list
of options.  The setup program will construct a new git repository in the
current working directory.  This repository is used to manage the output of
the setup program.

You may re-run the setup program at any time to update/change the project
settings.  However, your build directory will not be touched.  You will have
to resync it with the updated project.  (Specifically bblayers.conf and
local.conf to the config/*.sample versions.)

To update your project, you may run 'repo sync' or re-run the setup program
with the same arguments.


Mirror workflow:

$ mkdir my-mirror
$ cd my-mirror
$ git clone --branch <branch> <url> wrlinux-9
$ ./wrlinux-9/setup.sh --all-layers --mirror

The above command will mirror all layers, including download layers into the
current location.

To update the mirror, simply run 'repo sync' or re-run the setup.sh command
with the same arguments.


A user can reference this mirror by doing:

$ mkdir my-project
$ cd my-project
$ git clone --branch master <path_to_mirror>/wrlinux-9

and then run the wrlinux-9/setup.sh program as described above.

Note: the bin/settings.py file contains url REPLACE operations that may be
required to reference the local mirror items.


License
-------

Copyright (C) 2016 Wind River Systems, Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
