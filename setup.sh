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

# python2 is needed as 03_wrl_askpass.sh uses setup_askpass which is written in python2
which python2 > /dev/null
if [ $? -ne 0 ]; then
	echo >&2 "WRLinux setup requires 'python2'."
	echo >&2 "Please install python2."
	exit 1
fi

# The working python should link to python2
python_path=`which python 2>/dev/null`
[ -n "${python_path}" ] && {
	python_bn=$(basename $(readlink -f ${python_path}))
	python_bn=${python_bn%%.*}
	[ ${python_bn} = "python2" ] || {
		echo >&2 "The ${python_path} should link to python2 for WRLinux setup."
		exit 1
	}
}

GIT_USERNAME="customer"
GIT_USEREMAIL="customer@company.com"

# Requires python3
CMD="bin/setup.py"

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

# Setup the minimal defaults first..
# BASEDIR, BASEURL and BASEBRANCH
BASEDIR=$(readlink -f "$(dirname "$0")")

# Argument parsing, define a limited set of args
setup_add_arg --base-url BASEURL keep
setup_add_arg --base-branch BASEBRANCH keep

help=0
parse_arguments "$@"
unset PASSARGS

# setup git url
REMOTEURL=$(cd "$BASEDIR" ; git config remote.origin.url 2>/dev/null)

# BASEURL is one directory above the git checkout
BASEREPO=""
if [ -z "${BASEURL}" ]; then
	BASEURL=$(echo "$REMOTEURL" | sed -e 's,/$,,' -e 's,/[^/]*$,,')
	BASEREPO=${REMOTEURL##$BASEURL\/}
fi

# First check if this is an absolute path (starts w/ '/')
# If it's not, we then check if it's a valid URL (contains ://)
if [ "${BASEURL:0:1}" != '/' ]; then
	if [ "${BASEURL#*://}" == "${BASEURL}" ]; then
		echo >&2
		echo "ERROR: The BASEURL ($BASEURL) is not in a supported format." >&2
		if [ -n "${BASEREPO}" ]; then
			echo "The BASEURL was derived from the URL of $BASEREPO ($REMOTEURL)." >&2
			echo "Either update the repository URL or use the --base-url argument to override." >&2
		fi
		echo >&2
		echo "BASEURL must use an absolute file path, or a properly formatted remote URL" >&2
		echo "such as:" >&2
		echo "  /home/user/path or file:///home/user/path" >&2
		echo "  http://hostname/path" >&2
		echo "  https://hostname/path" >&2
		echo "  git://hostname/path" >&2
		echo "  ssh://user@hostname/path" >&2
		echo >&2
		exit 1
	fi
fi

if [ -z "${BASEBRANCH}" ]; then
	BASEBRANCH=$(git --git-dir="$BASEDIR/.git" rev-parse --abbrev-ref HEAD)
	if [ "$BASEBRANCH" = "HEAD" ]; then
		# Maybe this is a tag instead?
		BASEBRANCH=$(git --git-dir="$BASEDIR/.git" describe HEAD 2>/dev/null)
		if [ $? -ne 0 ]; then
			# No reasonable branch/tag name found...
			BASEBRANCH=""
		else
			BASEBRANCH="refs/tags/$BASEBRANCH"
                fi
	fi
fi

# Load custom setup additions
if [ -d "${BASEDIR}/data/environment.d" ]; then
	for envfile in ${BASEDIR}/data/environment.d/*.sh ; do
		. $envfile
	done
fi

# We need to reparse the arguments as we've now loaded the environment.d
# extensions
help=0
parse_arguments "$@"

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
		echo "May be on a detached HEAD, HEAD must be on a branch or tag. ($BASEDIR)" >&2
		echo "You can avoid this by passing the branch using --base-branch=" >&2
		exit 1
	fi

        # Is this a tag?  If so, don't allow tags w/ '-'
	if [ "$BASEBRANCH" != "${BASEBRANCH##refs/tags/}" ]; then
		if [ "$BASEBRANCH" != "${BASEBRANCH//-*}" ]; then
			echo "Checkout may be on a detached HEAD, this HEAD does not appear to" >&2
			echo "correspond to a specific, tag.  (It appears you may be working with" >&2
			echo "tag ${BASEBRANCH//-*}.  If this is correct, use" >&2
			echo "--base-branch=${BASEBRANCH//-*} in the arguments to" >&2
			echo "$0."
			exit 1
		fi
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

	# Configure the current directory so repo works seemlessly
	add_gitconfig "user.name" "${GIT_USERNAME}"
	add_gitconfig "user.email" "${GIT_USEREMAIL}"
	add_gitconfig "color.ui" "false"
	add_gitconfig "color.diff" "false"
	add_gitconfig "color.status" "false"
fi # if help -ne 1

# The following checks are from oe-buildenv-internal
py_v27_check=$(python2 -c 'import sys; print sys.version_info >= (2,7,3)')
if [ "$py_v27_check" != "True" ]; then
	echo >&2 "OpenEmbedded requires 'python2' to be python v2 (>= 2.7.3), not python v3."
	echo >&2 "Please upgrade your python v2."
	exit 1
fi
unset py_v27_check

# We potentially have code that doesn't parse correctly with older versions 
# of Python, and rather than fixing that and being eternally vigilant for 
# any other new feature use, just check the version here.
py_v34_check=$(python3 -c 'import sys; print(sys.version_info >= (3,4,0))' 2>/dev/null)
if [ "$py_v34_check" != "True" ]; then
	echo >&2 "BitBake requires Python 3.4.0 or later as 'python3'"
	exit 1
fi
unset py_v34_check

# This can happen if python3/urllib was not built with SSL support.
python3 -c 'import urllib.request ; dir(urllib.request.HTTPSHandler)' >/dev/null 2>&1
if [ $? -ne 0 ]; then
	echo >&2 "The setup tool requires Python 3.4.0 or later with support for 'urllib.request.HTTPSHandler'"
	exit 1
fi

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
