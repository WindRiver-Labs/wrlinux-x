wrlinux setup program
=====================

With this tool you can either create a new project, or create a mirror that
other projects can be based on.

The setup program relies on a special version of the 'git-repo' project.  It
is similar to the 'git-repo' used by Android, but has the added abililty to
work with 'bare' clones.


Basic setup/usage workflow:

The setup program is expected to have been cloned inside of a project
directory, such as:

$ mkdir my-project
$ cd my-project
$ git clone --depth 1 --branch WRLINUX_9_BASE git://git.wrs.com/wrlinux-x

Once cloned, simply run the setup.sh (./wrlinux-x/setup.sh) to get a list
of options.  The setup program will construct a project in the current 
working directory.

You may re-run the setup program at any time to update/change the project
settings.  However, your build directory will not be touched.  You will have
to resync that with the updated project.  (Specifically bblayers.conf and
local.conf.)

To update your project, you may run 'repo sync' or re-run the setup program
with the same arguments.


Advanced Mirror workflow:

$ mkdir my-mirror
$ cd my-mirror
$ git clone --depth 1 --branch WRLINUX_9_BASE git://git.wrs.com/wrlinux-x
$ ./wrlinux/setup.sh --all-layers --dl-layers --mirror

The above command will mirror all layers, including download layers into the
current location.

To update the mirror, simply run 'repo sync' or re-run the setup.sh command
with the same arguments.


A user can reference this mirror by doing:

$ mkdir my-project
$ cd my-project
$ git clone --depth 1 --branch WRLINUX_9_BASE <path_to_mirror>/wrlinux-x

and then run the wrlinux-x/setup.sh program as described above.


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
