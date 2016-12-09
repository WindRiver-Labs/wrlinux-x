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

# Download, install and load the buildtools tarball (as needed)

# Buildtools location can change -- this is the path on top of the BASEURL
BUILDTOOLS_REMOTE="${BUILDTOOLS_REMOTE:-buildtools-standalone-20161208}"

# Special windshare folders to search
BUILDTOOLS_FOLDERS="WRLinux-9-LTS-CVE WRLinux-9-LTS WRLinux-9-Base"

# Where to cache the git fetch
BUILDTOOLS_GIT="${BUILDTOOLS_GIT:-bin/buildtools.git}"

# Where to install the build tools
BUILDTOOLS="${BUILDTOOLS:-bin/buildtools}"

# Arch of the SDK to load
SDKARCH=${SDKARCH:-$(uname -m)}

setup_add_arg --buildtools-branch BUILDTOOLSBRANCH keep

setup_add_func buildtools_setup

setup_export_func buildtools_export

. ${BASEDIR}/data/environment.d/setup_utils

buildtools_setup() {
	if [ -z "${BUILDTOOLSBRANCH}" ]; then
		BUILDTOOLSBRANCH="${BASEBRANCH}"
	fi

	FETCH_BUILDTOOLS=0

	# Install them into the project directory
	EXTRACT_BUILDTOOLS=0

	BUILDTOOLS_REF=$(echo ${BUILDTOOLS_REMOTE} | sed -e 's,.*/buildtools-standalone-,,')

	if [ ! -d "${BUILDTOOLS_GIT}" ]; then
		FETCH_BUILDTOOLS=1

		(mkdir -p ${BUILDTOOLS_GIT} && git init ${BUILDTOOLS_GIT})
		if [ $? -ne 0 ]; then
			echo "Unable to create ${BUILDTOOLS_GIT} directory." >&2
			return 1
		fi
	else
		# Did the buildtools URL change?
		LASTREF=$(git config -f ${BUILDTOOLS_GIT}/.git/config local.last.ref)
		if [ "${LASTREF}" != "${BUILDTOOLS_REF}" ]; then
			FETCH_BUILDTOOLS=1
		fi
	fi

	if [ ${FETCH_BUILDTOOLS} -ne 1 ]; then
		# We need this in order to have the right path for subsequent mirror operations
		BUILDTOOLS_REMOTE=$(git config -f ${BUILDTOOLS_GIT}/.git/config local.${BUILDTOOLS_REF}.path)
	else
		echo "Searching for ${BUILDTOOLS_REMOTE}..."

		if ! setup_check_url "${BASEURL}/${BUILDTOOLS_REMOTE}" ; then
			ORIG_BT_REMOTE=${BUILDTOOLS_REMOTE}
			# Additional places to search...
			for folder in ${BUILDTOOLS_FOLDERS} layers/buildtools; do
				NEW_REMOTE=${folder}/${BUILDTOOLS_REMOTE}
				if setup_check_url "${BASEURL}/${NEW_REMOTE}" ; then
					BUILDTOOLS_REMOTE=${NEW_REMOTE}
				fi
			done
			if [ "${BUILDTOOLS_REMOTE}" = "${ORIG_BT_REMOTE}" ]; then
				echo "Unable to find ${BUILDTOOLS_REMOTE}.  Search path:">&2
				for folder in ${BUILDTOOLS_FOLDERS} layers/buildtools; do
					echo "	${BASEURL}/${folder}/${BUILDTOOLS_REMOTE}" >&2
				done
				return 1
			fi
		fi

		echo "Fetching buildtools.."
		(cd ${BUILDTOOLS_GIT} && git fetch -f -n -u "${BASEURL}/${BUILDTOOLS_REMOTE}" ${BUILDTOOLSBRANCH}:${BUILDTOOLS_REF})
		if [ $? -ne 0 ]; then
			echo "Error fetching buildtools repository ${BASEURL}/${BUILDTOOLS_REMOTE}" >&2
			return 1
		fi
		# Set a flag so we know where the fetch was from...
		(
			cd ${BUILDTOOLS_GIT}
			git config "local.${BUILDTOOLS_REF}.url" "${BASEURL}/${BUILDTOOLS_REMOTE}"
			git config "local.${BUILDTOOLS_REF}.path" "${BUILDTOOLS_REMOTE}"
			git config local.last.ref "${BUILDTOOLS_REF}"
			git checkout "${BUILDTOOLS_REF}"
		)
		if [ $? -ne 0 ]; then
			echo "Unable to checkout branch ${BUILDTOOLS_REF}." >&2
			return 1
		fi
		echo "Done"

		EXTRACT_BUILDTOOLS=1
	fi

	if [ ! -d "${BUILDTOOLS}.${BUILDTOOLS_REF}" ]; then
		EXTRACT_BUILDTOOLS=1
	fi

	if [ ${EXTRACT_BUILDTOOLS} -ne 1 ]; then
		ENVIRON=$(find -L ${BUILDTOOLS} -name "environment-setup-${SDKARCH}-*-linux" | head -n1)
		if [ -z "${ENVIRON}" ]; then
			# Something is wrong, try to fix it!
			EXTRACT_BUILDTOOLS=1
		fi
	fi

	if [ ${EXTRACT_BUILDTOOLS} -eq 1 ]; then
		# Needs python.
		buildtoolssdk=$(find "${BUILDTOOLS_GIT}" -name "${SDKARCH}-buildtools-nativesdk-standalone-*.sh" 2>/dev/null | sort | head -n1)
		if [ -z "${buildtoolssdk}" ]; then
			echo "Unable to find buildtools-nativesdk-standalone archive for ${SDKARCH}." >&2
			echo >&2
			echo "SDKARCH values found:" >&2
			echo $(find "${BUILDTOOLS_GIT}" -name "*-buildtools-nativesdk-standalone-*.sh" | xargs -n 1 basename | cut -d '-' -f 1) >&2
			echo >&2
			echo "If one of these is compatible, set SDKARCH in your environment." >&2
			echo >&2
			return 1
		fi
		echo "Installing buildtools.."
		if [ -d "${BUILDTOOLS}.${BUILDTOOLS_REF}" ]; then
			rm -rf "${BUILDTOOLS}.${BUILDTOOLS_REF}"
		fi
		trap : INT
		${buildtoolssdk} -d "${BUILDTOOLS}.${BUILDTOOLS_REF}" -y
		if [ $? -ne 0 ]; then
			echo >&2
			echo "Error installing the buildtools-nativesdk-standalone archive: ${buildtoolssdk}" >&2
			# We try to cleanup, but an over zealous (sigint) user can stop the rm as well.
			rm -rf ${BUILDTOOLS}.${BUILDTOOLS_REF}
			return 1
		fi
		trap - INT
		rm -f ${BUILDTOOLS}
		ln -s $(basename ${BUILDTOOLS}).${BUILDTOOLS_REF} ${BUILDTOOLS}
		echo "Done"
	fi
	unset FETCH_BUILDTOOLS EXTRACT_BUILDTOOLS

	ENVIRON=$(find -L ${BUILDTOOLS} -name "environment-setup-${SDKARCH}-*-linux" | head -n1)
	if [ -z "${ENVIRON}" ]; then
		echo "Error unable to load buildtools environment-setup file." >&2
		return 1
	fi
	. "${ENVIRON}"
	if [ $? -ne 0 ]; then
		echo "Unable to load the buildtools environment setup file." >&2
		return 1
	fi
	BUILDTOOLS_LOADED=1
	return 0
}


buildtools_export() {
	if [ -z "${BUILDTOOLSBRANCH}" ]; then
		BUILDTOOLSBRANCH="${BASEBRANCH}"
	fi

	export OE_BUILDTOOLS_BRANCH=${BUILDTOOLSBRANCH}
	export OE_BUILDTOOLS_REMOTE=${BUILDTOOLS_REMOTE}
	return 0
}
