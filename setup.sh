#!/bin/bash
#
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

GIT_USERNAME="customer"
GIT_USEREMAIL="customer@company.com"

# Requires python3
CMD="bin/setup.py"

# Only requires python2
CMD_HELP="bin/setup_help.py"

# Load custom setup additions
if [ -d "data/environment.d" ]; then
	for envfile in data/environment.d/*.sh ; do
		. $envfile
	done
fi

# Takes value_name default_value
# value_name is set to the first value found in the list:
# git config, git config --global, and finally default_value
add_gitconfig() {
	VAR=$(git config "$1" || git config --global "$1" || echo "$2")
	git config -f .gitconfig "${1}" "${VAR}"
}

BASEDIR=$(readlink -f "$(dirname "$0")")

# Argument parsing, limited set of arguments parsed here
help=0
if [ "$#" -eq 0 ]; then
	# Default into a --help module which is part of setup.py
	help=1
fi

# We only parse things this shell script cares about, actual argparse
# and looking for bad args is done by the python script this calls.
for arg in "$@" ; do
	case $arg in
		--help|-h)
			help=1
			;;
		--base-url=*)
			BASEURL="${arg#*=}"
			;;
		--base-branch=*)
			BASEBRANCH="${arg#*=}"
			;;
	esac

	# If there are additional parameters defined, deal with them here...
	for parse in $ARGPARSE; do
		comp=${parse%:*}
		val=${parse#*:}
		case "$arg" in
			${comp})
				eval ${val}="${arg#*=}"
				;;
		esac
	done
done

# setup git url
REMOTEURL=$(cd "$BASEDIR" ; git config remote.origin.url 2>/dev/null)

# BASEURL is one directory above the git checkout
if [ -z "${BASEURL}" ]; then
	BASEURL=$(echo "$REMOTEURL" | sed -e 's,/$,,' -e 's,/[^/]*$,,')
fi
if [ -z "${BASEBRANCH}" ]; then
	BASEBRANCH=$(git --git-dir="$BASEDIR/.git" rev-parse --abbrev-ref HEAD)
	if [ "$BASEBRANCH" = "HEAD" ]; then
		BASEBRANCH=""
	fi
fi

if [ $help -ne 1 ]; then
	# Before doing anything else, error out if the project directory
	# is unsafe.
	case "$PWD" in
		$BASEDIR | $BASEDIR/*)
		echo >&2 "$0: The current working directory is used as your project directory"
		echo >&2 "    Your project directory must not be in or under"
		echo >&2 "    '${BASEDIR}'"
		echo >&2 ""
		echo >&2 "    Typically a project is setup by doing:"
		echo >&2 "      $ mkdir my_project"
		echo >&2 "      $ cd my_project"
		echo >&2 "      $ git clone --branch $BASEBRANCH $REMOTEURL"
		echo >&2 "      $ .$(echo $REMOTEURL | sed "s,$BASEURL,,")/setup.sh $@"
		exit 1
		;;
	esac

	if [ -z "$BASEBRANCH" ]; then
		echo "May be on a detached HEAD, HEAD must be on a branch. ($BASEDIR)" >&2
		echo "You can avoid this by passing the branch using --base-branch=" >&2
		exit 1
	fi

	if [ -n "$ADDFUNCS" ]; then
		$ADDFUNCS
	fi

	# The following checks are from oe-buildenv-internal
	# Make sure we're not using python v3.x as 'python', we don't support it.
	py_v2_check=$(/usr/bin/env python --version 2>&1 | grep "Python 3")
	if [ -n "$py_v2_check" ]; then
		echo >&2 "OpenEmbedded requires 'python' to be python v2 (>= 2.7.3), not python v3."
		echo >&2 "Please set up python v2 as your default 'python' interpreter."
		return 1
	fi
	unset py_v2_check

	py_v27_check=$(python -c 'import sys; print sys.version_info >= (2,7,3)')
	if [ "$py_v27_check" != "True" ]; then
		echo >&2 "OpenEmbedded requires 'python' to be python v2 (>= 2.7.3), not python v3."
		echo >&2 "Please upgrade your python v2."
	fi
	unset py_v27_check

	# We potentially have code that doesn't parse correctly with older versions 
	# of Python, and rather than fixing that and being eternally vigilant for 
	# any other new feature use, just check the version here.
	py_v34_check=$(python3 -c 'import sys; print(sys.version_info >= (3,4,0))')
	if [ "$py_v34_check" != "True" ]; then
		echo >&2 "BitBake requires Python 3.4.0 or later as 'python3'"
		return 1
	fi
	unset py_v34_check

	# Configure the current directory so repo works seemlessly
	add_gitconfig "user.name" "${GIT_USERNAME}"
	add_gitconfig "user.email" "${GIT_USEREMAIL}"
	add_gitconfig "color.ui" "false"
	add_gitconfig "color.diff" "false"
	add_gitconfig "color.status" "false"
else
	# If we don't have python3, fall back to the help only version
	if which python3 &> /dev/null; then
		CMD="${CMD_HELP}"
	fi
fi # if help -ne 1

# Python 3 required utf-8 support to work properly, adjust the LANG to en_US.UTF-8.
export LANG='en_US.UTF-8'

# Pass the computed url and branch to ${cmd}
export OE_BASEURL=${BASEURL}
export OE_BASEBRANCH=${BASEBRANCH}

# Switch to the python script
exec ${BASEDIR}/${CMD} "$@"
