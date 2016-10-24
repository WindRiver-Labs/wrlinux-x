ADDFUNCS+=" wr_repo_setup ;"

wr_repo_setup() {
	# Ensure subsequent 'repo' calls use the correct URL
	export REPO_URL=${BASEURL}/tools/git-repo
}
