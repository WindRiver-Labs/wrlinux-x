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

# Buildtools location can change -- this is the path on top of the BASEURL
BUILDTOOLS_REMOTE="layers/buildtools/buildtools-standalone-20161013"

# Where to install the build tools
BUILDTOOLS="bin/buildtools"

# Arch of the SDK to load
SDKARCH=$(uname -p)

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
		--buildtools-branch=*)
			BUILDTOOLSBRANCH="${arg#*=}"
			;;
	esac
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
		exit 1
	fi
	if [ -z "${BUILDTOOLSBRANCH}" ]; then
		BUILDTOOLSBRANCH="${BASEBRANCH}"
	fi

	# By default we fetch the buildtools from the wrlinux-X directory
	# Otherwise we will fetch it into this project directory
	if [ -d buildtools.git ]; then
		BUILDTOOLS_GIT="${BUILDTOOLS_GIT:-buildtools.git}"
	else
		BUILDTOOLS_GIT="${BUILDTOOLS_GIT:-${BASEDIR}/buildtools.git}"
	fi
	FETCH_BUILDTOOLS=0

	# Install them into the project directory
	EXTRACT_BUILDTOOLS=0

	BUILDTOOLS_REF=$(echo ${BUILDTOOLS_REMOTE} | sed -e 's,.*/buildtools-standalone-,,')

	# FIXME, needs to be per-user - somehow.
	add_gitconfig "user.name" "${GIT_USERNAME}"
	add_gitconfig "user.email" "${GIT_USEREMAIL}"
	add_gitconfig "color.ui" "false"
	add_gitconfig "color.diff" "false"
	add_gitconfig "color.status" "false"

	if [ ! -d "${BUILDTOOLS_GIT}" ]; then
		FETCH_BUILDTOOLS=1

		# Create empty buildtools.git cache and determine the right location
		(mkdir -p "${BUILDTOOLS_GIT}" 2>/dev/null && cd "${BUILDTOOLS_GIT}" && git init)
		if [ $? -ne 0 ]; then
			echo "Unable to create ${BUILDTOOLS_GIT} directory.  Falling back to project directory." >&2
			BUILDTOOLS_GIT="buildtools.git"
			(mkdir -p ${BUILDTOOLS_GIT} 2>/dev/null && cd ${BUILDTOOLS_GIT} && git init)
			if [ $? -ne 0 ]; then
				echo "Still unable to create ${BUILDTOOLS_GIT} directory.  Please check permissions." >&2
				exit 1
			fi
		fi
	else
		# Did the buildtools URL change?
		BUILDTOOLSURL=$(git config -f ${BUILDTOOLS_GIT}/.git/config local.last.url)
		if [ "${BUILDTOOLSURL}" != "${BASEURL}/${BUILDTOOLS_REMOTE}" ]; then
			FETCH_BUILDTOOLS=1
		fi
	fi

	if [ ${FETCH_BUILDTOOLS} -eq 1 ]; then
		echo "Fetching buildtools.."
		(cd ${BUILDTOOLS_GIT} && git fetch -f -n -u "${BASEURL}/${BUILDTOOLS_REMOTE}" ${BUILDTOOLSBRANCH}:${BUILDTOOLS_REF})
		if [ $? -ne 0 ]; then
			echo "Error fetching buildtools repository ${BASEURL}/${BUILDTOOLS_REMOTE}" >&2
			exit 1
		fi
		# Set a flag so we know where the fetch was from...
		(
			cd ${BUILDTOOLS_GIT}
			git config "local.${BUILDTOOLS_REF}.url" "${BASEURL}/${BUILDTOOLS_REMOTE}"
			git config local.last.url "${BASEURL}/${BUILDTOOLS_REMOTE}"
			git checkout "${BUILDTOOLS_REF}"
		)
		if [ $? -ne 0 ]; then
			echo "Unable to checkout branch ${BUILDTOOLS_REF}." >&2
			exit 1
		fi
		echo "Done"

		EXTRACT_BUILDTOOLS=1
	fi

	if [ ! -d "${BUILDTOOLS}.${BUILDTOOLS_REF}" ]; then
		EXTRACT_BUILDTOOLS=1
	fi

	if [ ${EXTRACT_BUILDTOOLS} -eq 1 ]; then
		# Needs python.
		buildtoolssdk=$(find "${BUILDTOOLS_GIT}" -name "${SDKARCH}-buildtools-nativesdk-standalone-*.sh" 2>/dev/null | sort | head -n1)
		if [ -z "${buildtoolssdk}" ]; then
			echo "Unable to find ${SDKARCH} buildtools-nativesdk-standalone archive in ${PWD}/buildtools/" >&2
			exit 1
		fi
		echo "Installing buildtools.."
		if [ -d "${BUILDTOOLS}.${BUILDTOOLS_REF}" ]; then
			rm -rf "${BUILDTOOLS}.${BUILDTOOLS_REF}"
		fi
		${buildtoolssdk} -d "${BUILDTOOLS}.${BUILDTOOLS_REF}" -y
		if [ $? -ne 0 ]; then
			echo "Error installing the buildtools-nativesdk-standalone archive: ${buildtoolssdk}" >&2
			exit 1
		fi
		rm -f ${BUILDTOOLS}
		ln -s $(basename ${BUILDTOOLS}).${BUILDTOOLS_REF} ${BUILDTOOLS}
		echo "Done"
	fi
	unset FETCH_BUILDTOOLS EXTRACT_BUILDTOOLS

	ENVIRON=$(find -L ${BUILDTOOLS} -name "environment-setup-${SDKARCH}-*-linux" | head -n1)
	if [ -z "${ENVIRON}" ]; then
		echo "Error unable to load buildtools environment-setup file." >&2
		exit 1
	fi
	. "${ENVIRON}"
	if [ $? -ne 0 ]; then
		echo "Unable to load the buildtools environment setup file." >&2
		exit 1
	fi
fi # if help -ne 1

# Requires python3
CMD="${BASEDIR}/bin/setup.py"

if [ $help -eq 1 ] && ! which python3 &> /dev/null; then
	ENVIRON=$(find -L ${BUILDTOOLS} -name "environment-setup-${SDKARCH}-*-linux" | head -n1)
	if [ -n "${ENVIRON}" ]; then
		. "${ENVIRON}"
	fi

	if ! which python3 &> /dev/null; then
		# We don't have python3, give them help anyway
		CMD="${BASEDIR}/bin/setup_help.py"
	fi
fi

# Python 3 required utf-8 support to work properly, adjust the LANG to en_US.UTF-8.
# Pass the computed url and branch to ${cmd}
LANG='en_US.UTF-8' REPO_URL=${BASEURL}/tools/git-repo WR_BASEURL=${BASEURL} WR_BASEBRANCH=${BASEBRANCH} WR_BUILDTOOLS_REMOTE=${BUILDTOOLS_REMOTE} ${CMD} "$@"
