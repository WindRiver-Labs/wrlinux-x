# Buildtools location can change -- this is the path on top of the BASEURL
BUILDTOOLS_REMOTE="${BUILDTOOLS_REMOTE:-layers/buildtools/buildtools-standalone-20161122}"

# Where to cache the git fetch
BUILDTOOLS_GIT="${BUILDTOOLS_GIT:-bin/buildtools.git}"

# Where to install the build tools
BUILDTOOLS="${BUILDTOOLS:-bin/buildtools}"

# Arch of the SDK to load
SDKARCH=$(uname -p)

ARGPARSE+=" --buildtools-branch=*:BUILDTOOLSBRANCH"

ADDFUNCS+=" buildtools_setup ;"

EXPORTFUNCS+=" buildtools_export ;"

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
			exit 1
		fi
	else
		# Did the buildtools URL change?
		LASTREF=$(git config -f ${BUILDTOOLS_GIT}/.git/config local.last.ref)
		if [ "${LASTREF}" != "${BUILDTOOLS_REF}" ]; then
			FETCH_BUILDTOOLS=1
		fi
	fi

	if [ ${FETCH_BUILDTOOLS} -eq 1 ]; then
		if ! git ls-remote "${BASEURL}/${BUILDTOOLS_REMOTE}" >/dev/null 2>&1 ; then
			# If 'full' URL doesn't work, retry with a flattened view
			NEW_REMOTE=$(echo ${BUILDTOOLS_REMOTE} | sed -e 's,.*/buildtools-standalone-,buildtools-standalone-,')
			if ! git ls-remote "${BASEURL}/${NEW_REMOTE}" >/dev/null 2>&1 ; then
				echo "Unable to find ${BASEURL}/${BUILDTOOLS_REMOTE} or ${BASEURL}/${NEW_REMOTE}" >&2
				exit 1
			else
				BUILDTOOLS_REMOTE=${NEW_REMOTE}
			fi
		fi

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
			git config local.last.ref "${BUILDTOOLS_REF}"
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
}


buildtools_export() {
	if [ -z "${BUILDTOOLSBRANCH}" ]; then
		BUILDTOOLSBRANCH="${BASEBRANCH}"
	fi

	export OE_BUILDTOOLS_BRANCH=${BUILDTOOLSBRANCH}
	export OE_BUILDTOOLS_REMOTE=${BUILDTOOLS_REMOTE}
}
