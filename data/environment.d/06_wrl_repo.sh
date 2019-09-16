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

setup_add_arg --repo-url REPO_URL
setup_add_arg --repo-branch REPO_REV

setup_add_func wr_repo_setup
setup_add_func wr_repo_clone

# Special windshare folders to search
REPO_FOLDERS=""

. ${BASEDIR}/data/environment.d/setup_utils

wr_repo_find() {
	echo "Searching for git-repo..."
	REPO_URL=${BASEURL}/git-repo
	if ! setup_check_url "${REPO_URL}" ; then
		# Clear in case there are no REPO_FOLDERS
		REPO_URL=""
		for folder in ${REPO_FOLDERS} ; do
			REPO_URL=${BASEURL}/${folder}/git-repo
			if ! setup_check_url "${REPO_URL}" ; then
				REPO_URL=""
				continue
			fi
			break
		done
	fi

	if [ -z "${REPO_URL}" ]; then
		echo "Unable to find git-repo repository.  Search path:" >&2
		echo "  ${BASEURL}/git-repo" >&2
		for folder in ${REPO_FOLDERS} ; do
			echo "  ${BASEURL}/${folder}/git-repo" >&2
		done
		return 1
	fi
	return 0
}

repo_branch_fallback="stable-wr"

wr_repo_setup() {
	local update_url
	local update_rev

	update_url=true
	update_rev=true

	# If the user passed it in, we use it after we verify it!
	if [ -n "$REPO_URL" ]; then
		if ! setup_check_url "${REPO_URL}" ; then
			echo "Unable to find git-repo repository. ${REPO_URL}" >&2
			return 1
		fi
	fi

	# If we still don't know it, check the file...
	if [ -z "$REPO_URL" ]; then
		if [ -e bin/.git-repo ]; then
			REPO_URL=$(cat bin/.git-repo)
			update_url=false
		# If we still don't know it, go find it...
		elif ! wr_repo_find ; then
			return 1
		fi
	fi

	# Repo rev time...
	# User passed it in, verify it
	if [ -n "$REPO_REV" ]; then
		output=$(setup_check_url_branch "${REPO_URL}" "${REPO_REV}")
		if [ "$output" != "$REPO_REV" -o $? -ne 0 ] ; then
			echo "Unable to find branch ${REPO_REV} in git-repo repository (${REPO_URL})" >&2
			return 1
		fi
	fi

	if [ -z "$REPO_REV" ]; then
		if [ -e bin/.git-repo-rev ]; then
			REPO_REV=$(cat bin/.git-repo-rev)
			update_rev=false
		else # If we still don't know it, go find it...
			BASEBRANCHES[0]=${BASEBRANCH}
			# Skip master-wr, we don't use this branch any longer in git-repo...
			if [ "${BASEBRANCHES[0]}" == "master-wr" ]; then
				BASEBRANCHES[0]="$repo_branch_fallback"
			fi
			if [ "${BASEBRANCHES[0]}" != "$repo_branch_fallback" ]; then
				BASEBRANCHES[1]="$repo_branch_fallback"
			fi
			REPO_REV=$(setup_check_url_branch "${REPO_URL}" "${BASEBRANCHES[@]}")
			if [ -z "${REPO_REV}" ]; then
				echo "Unable to find a usable branch (${BASEBRANCHES[@]}) in git-repo repository (${REPO_URL})" >&2
				return 1
			fi
		fi
	fi

	# Ensure subsequent 'repo' calls use the correct URL
	if $update_url ; then
		echo ${REPO_URL} > bin/.git-repo
	fi
	export REPO_URL

	# Ensure subsequent 'repo' calls use the correct REV
	if $update_rev ; then
		echo ${REPO_REV} > bin/.git-repo-rev
	fi
	export REPO_REV

	return 0
}

wr_repo_clone() {
	# git-repo is limited to working on it's own branches only.
	# In otherwords, we can't checkout a tag in git-repo and work with it,
	# otherwise we get numerous errors that things fail due to them not being
	# based on branches.
	#
	# Due to the design of git-repo, it is safe to use the latest version
	# on a branch associated with the tag.  For instance, if the tag
	# vWRLINUX_CI_10.19.29.0 is a tag based on WRLINUX_CI branch, we can just
	# use the branch for cloning.
	#

	# Since we can't check what branch the tag is from w/o a clone, we clone...
	if [ ! -d bin/git-repo ]; then
		git clone "${REPO_URL}" bin/git-repo
		if [ $? -ne 0 ]; then
			echo "Unable to clone git-repo from ${REPO_URL}." >&2
			return 1
		fi
	else
		if [ "${REPO_URL}" != "$(git config -f bin/git-repo/.git/config remote.origin.url)" ]; then
			echo "Updating git-repo remote url"
			git config -f bin/git-repo/.git/config remote.origin.url "${REPO_URL}"
		fi

		# We always clear local changes to make sure we're synced up!
		(cd bin/git-repo && git remote update origin && git reset --hard @{upstream})
		if [ $? -ne 0 ]; then
			echo "WARNING: Unable to reset the git-repo respository." >&2
		fi
	fi

	# Translate REPO_REV, if a tag to a branch
	if [ "$REPO_REV" != "${REPO_REV##refs/tags/}" ]; then
		# Find the first branch containing that commit..
		REPO_BRANCH=$(cd bin/git-repo && git branch -r --contains ${REPO_REV}^{commit} 2>/dev/null | head -n 1)
		if [ -z ${REPO_BRANCH} ]; then
			echo "ERROR: Unable to find branch containing $REPO_REV in git-repo repository."
			exit 1
		fi
		# Strip spaces
		REPO_BRANCH=$(echo ${REPO_BRANCH})
		# Turn into a local branch
		REPO_BRANCH=${REPO_BRANCH##origin/}
		echo "Translated tag ${REPO_REV} to branch ${REPO_BRANCH}"

		REPO_REV=$REPO_BRANCH
	fi

	if [ "* ${REPO_REV}" != "$(cd bin/git-repo && git branch | grep '\*')" ]; then
		(cd bin/git-repo && git checkout ${REPO_REV})
		if [ $? -ne 0 ]; then
			echo "ERROR: Unable to checkout branch ${REPO_REV}" >&2
			return 1
		fi
	fi

	if [ -d .repo/repo/.git ]; then
		echo "Syncing git-repo to configured .repo/repo"
		repo_resync=false
		bin_repo_url=$(git config -f bin/git-repo/.git/config remote.origin.url)
		git_repo_url=$(git config -f .repo/repo/.git/config remote.origin.url)
		if [ "${bin_repo_url}" != "${git_repo_url}" ]; then
			git config -f .repo/repo/.git/config remote.origin.url "${bin_repo_url}"
			repo_resync=true
		fi
		bin_repo_branch=$(git config -f bin/git-repo/.git/config branch.${REPO_REV}.merge)
		git_repo_branch=$(git config -f .repo/repo/.git/config branch.default.merge)
		if [ "${bin_repo_branch}" != "${git_repo_branch}" ]; then
			git config -f .repo/repo/.git/config branch.default.merge "${bin_repo_branch}"
			repo_resync=true
			git_repo_branch=$(git config -f .repo/repo/.git/config branch.default.merge)
		fi
		if $repo_resync ; then
			(cd .repo/repo && git remote update origin) || exit 1
			(cd .repo/repo && git reset --hard @{upstream}) || exit 1
		fi
	fi


	export PATH=$(cd bin/git-repo && pwd):$PATH
}
