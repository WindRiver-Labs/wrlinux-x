EXPORTFUNCS+=" wr_repo_export ;"

wr_repo_export() {
	# Ensure subsequent 'repo' calls use the correct URL
	export REPO_URL=${BASEURL}/git-repo
}
