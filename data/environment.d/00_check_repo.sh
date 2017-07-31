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

# Verify that we don't have a .repo directory in a parent dir
# since repo does not permit this

setup_add_func check_repo

check_repo() {
	# Cleanup the path if necessary
	path=$(cd $PWD ; pwd)

	while
	        path=$(dirname $path)
		[ -n "$path" -a "$path" != "/" ]
	do
		if [ -e $path/.repo ]; then
			echo "ERROR: A parent path has a .repo subdirectory: $path" >&2
			echo "git-repo, which is used by the setup program, does not permit a nested" >&2
			echo "repository structure.  You must run setup in a different location or" >&2
			echo "remove the directory $path/.repo" >&2
			exit 1
		fi
	done
}
