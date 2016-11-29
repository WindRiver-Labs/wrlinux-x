EXPORTFUNCS+=" wr_repo_export ;"

# Special windshare folders to search
REPO_FOLDERS="WRLinux-9-LTS-CVE WRLinux-9-LTS WRLinux-9-Base"

# $1 - url to verify
wr_repo_check() {
	git ls-remote "$1" >/dev/null 2>&1
	return $?
}

wr_repo_export() {
	REPO_URL=${BASEURL}/git-repo
	if ! wr_repo_check "${REPO_URL}" ; then
		for folder in ${REPO_FOLDERS} ; do
			REPO_URL=${BASEURL}/${folder}/git-repo
			if ! wr_repo_check "${REPO_URL}" ; then
				REPO_URL=""
				continue
			fi
			break
		done
	fi

	if [ -z "${REPO_URL}" ]; then
		echo "Unable to find git-repo repository.  Search path:" >&2
		echo "${BASEURL}/git-repo" >&2
		for folder in ${REPO_FOLDERS} ; do
			echo "${BASEURL}/${folder}/git-repo" >&2
		done
		exit 1
	fi

	# Ensure subsequent 'repo' calls use the correct URL
	export REPO_URL
}
