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

if [ -z "${BASH_VERSION}" ]; then
	echo "This script must be run with bash." >&2
	exit 1
fi

GIT_USERNAME="customer"
GIT_USEREMAIL="customer@company.com"

# Requires python3
CMD="bin/setup.py"

# Only requires python2
CMD_HELP="bin/setup_help.py"

# Adds arguments to the arg processing
#   1 - argument
#   2 - variable to define
#   3 - keep or discard (if defined, keep)
#       there may be arguments you don't want passed to the .py script
setup_add_arg() {
	found=0
	for parse in ${ARGPARSE[@]}; do
		comp=${parse%%:*}
		if [ "${comp}" = "$1" ]; then
			found=1
		fi
	done

	if [ ${found} -eq 0 ]; then
		ARGPARSE[${#ARGPARSE[@]}]="$1:$2:$3"
	fi
}

# Functions that add functionality during early processing
setup_add_func() {
	ADDFUNCS[${#ADDFUNCS[@]}]="$1"
}

# Functions that export variables (or need to run very late)
setup_export_func() {
	EXPORTFUNCS[${#EXPORTFUNCS[@]}]="$1"
}

# Functions that run on shutdown
setup_shutdown_func() {
	SHUTDOWNFUNCS[${#SHUTDOWNFUNCS[@]}]="$1"
}

# Takes value_name default_value
# value_name is set to the first value found in the list:
# git config, git config --global, and finally default_value
add_gitconfig() {
	VAR=$(git config "$1" || git config --global "$1" || echo "$2")
	git config -f .gitconfig "${1}" "${VAR}"
}

shutdown() {
	for func in "${SHUTDOWNFUNCS[@]}"; do
		# During shutdown, we don't care about return codes
		$func
	done
}

# Input: argument list
# Output: 'help=1' or unset
#          PASSARGS set to the arguments to pass on
parse_arguments() {
	local found keep comp next val
	while [ $# -ge 1 ] ; do
		found=0
		if [ "$1" = "--help" -o "$1" = "-h" ]; then
			# Default into a --help module which is part of setup.py
			help=1
			PASSARGS[${#PASSARGS[@]}]="$1"
			shift
			continue
		fi
		for parse in ${ARGPARSE[@]}; do
			comp=${parse%%:*}
			next=${parse#${comp}:}
			val=${next%%:*}
			next=${next#${val}:}
			if [ "${next}" != "${val}" ]; then
				keep=${next}
			else
				keep=""
			fi
			case "$1" in
				${comp}=*)
					eval ${val}=\${1#*=}
					if [ -n "${keep}" ]; then
						PASSARGS[${#PASSARGS[@]}]="$1"
					fi
					shift
					found=1
					break
					;;
				${comp})
					eval ${val}=\${2}
					if [ -n "${keep}" ]; then
						PASSARGS[${#PASSARGS[@]}]="$1"
						# Only check whether $2 is set or not, set to "" or '--foo'
						# should work because:
						# - set to "": keep align with argparse since it works in this way.
						# - set to "--foo": argparse knows it's not the arg of $1,
						#                   but another option, and can handle it correctly.
						if [ -n "${2+x}" ]; then
							PASSARGS[${#PASSARGS[@]}]="$2"
						fi
					fi
					if [ -z "${2+x}" ]; then
						shift 1
					else
						shift 2
					fi
					found=1
					break
					;;
			esac
		done
		if [ $found -ne 1 ]; then
			PASSARGS[${#PASSARGS[@]}]="$1"
			shift
		fi
	done
}

BASEDIR=$(readlink -f "$(dirname "$0")")

# Load custom setup additions
if [ -d "${BASEDIR}/data/environment.d" ]; then
	for envfile in ${BASEDIR}/data/environment.d/*.sh ; do
		. $envfile
	done
fi

# Argument parsing, define a limited set of args
setup_add_arg --base-url BASEURL keep
setup_add_arg --base-branch BASEBRANCH keep

help=0
parse_arguments "$@"

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

	for func in "${ADDFUNCS[@]}"; do
		$func
		rc=$?
		if [ $rc -ne 0 ]; then
			echo "Stopping: an error occurred in $func." >&2
			shutdown
			exit $rc
		fi
	done

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
	if ! which python3 &> /dev/null; then
		CMD="${CMD_HELP}"
	fi
fi # if help -ne 1

# Python 3 required utf-8 support to work properly, adjust the LANG to en_US.UTF-8.
export LANG='en_US.UTF-8'

# Pass the computed url and branch to ${cmd}
export OE_BASEURL=${BASEURL}
export OE_BASEBRANCH=${BASEBRANCH}

for func in "${EXPORTFUNCS[@]}"; do
	$func
	rc=$?
	if [ $rc -ne 0 ]; then
		echo "Stopping: an error occurred in $func." >&2
		shutdown
		exit $rc
	fi
done

# Switch to the python script
${BASEDIR}/${CMD} "${PASSARGS[@]}"
rc=$?

shutdown

# Preserve the return code from the python script
exit $rc
