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

# Identify the right path for the Wind River version of git-repo
# setup the REPO_URL to point there...

ADDFUNCS+=" wr_repo_setup ;"

# Special windshare folders to search
REPO_FOLDERS="WRLinux-9-LTS-CVE WRLinux-9-LTS WRLinux-9-Base"

# $1 - url to verify
wr_repo_check() {
	git ls-remote "$1" >/dev/null 2>&1
	return $?
}

wr_repo_setup() {
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
		return 1
	fi

	# Ensure subsequent 'repo' calls use the correct URL
	export REPO_URL
	return 0
}
