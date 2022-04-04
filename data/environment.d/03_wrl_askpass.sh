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

# This needs to be run BEFORE we run any password checks...

setup_add_arg --user WINDSHARE_USER
setup_add_arg --password WINDSHARE_PASS

setup_add_func askpass_setup

setup_shutdown_func askpass_shutdown

askpass_setup() {
	# These values may also be used by anspass
	WINDSHARE_SCHEME=$(echo ${BASEURL} | sed 's,\([^:/]*\).*,\1,')
	if [ ${WINDSHARE_SCHEME} ]; then
		WINDSHARE_HOST=$(echo ${BASEURL} | sed 's,\([^:/]*\)://\([^/]*\).*,\2,')
	fi

	# If anspass is already enabled, use it instead!
	if [ -n "${ANSPASS_TOKEN}" ]; then
		return 0
	fi

	if [ "$WINDSHARE_SCHEME" = "http" ] || [ "$WINDSHARE_SCHEME" = "https" ]; then
		if [ -n "$GIT_ASKPASS" ]; then
			echo "INFO: Detected GIT_ASKPASS configuration. Disabling built-in askpass functionality."
			return 0
		fi
	fi

	export WRL_ASKPASS_SOCKET=${PWD}/bin/.setup_askpass

	# Cleanup any old instances
	${BASEDIR}/data/environment.d/setup_askpass --quit >/dev/null 2>&1
	rm -f ${WRL_ASKPASS_SOCKET}

	mkdir -p $(dirname ${WRL_ASKPASS_SOCKET})
	${BASEDIR}/data/environment.d/setup_askpass --server &
	askpass_pid=$!
	askpass_jid=%%

	while [ ! -e ${WRL_ASKPASS_SOCKET} ]; do
		if ! jobs $askpass_jid >/dev/null 2>&1 ; then
			echo "Unable to start the askpass server." >&2
			return 1
		fi
		# We have to give it time to start...
		sleep 1
	done

	# We need to tell it what tty to use for questions...
	echo $(tty) | ${BASEDIR}/data/environment.d/setup_askpass --set "tty" > /dev/null 2> /dev/null

	# If user/pass passed in (can't do this for a file path)
	if [ -n "${WINDSHARE_HOST}" ]; then
		if [ -n "${WINDSHARE_USER}" ]; then
			echo "${WINDSHARE_USER}" | ${BASEDIR}/data/environment.d/setup_askpass --set "Username for '${WINDSHARE_SCHEME}://${WINDSHARE_HOST}': " > /dev/null
			echo "${WINDSHARE_PASS}" | ${BASEDIR}/data/environment.d/setup_askpass --set "Password for '${WINDSHARE_SCHEME}://${WINDSHARE_USER}@${WINDSHARE_HOST}': " "${WINDSHARE_PASS}" > /dev/null
		fi

		if [ ${WINDSHARE_SCHEME} = "ssh" -a -n "${WINDSHARE_PASS}" ]; then
			echo "${WINDSHARE_PASS}" | ${BASEDIR}/data/environment.d/setup_askpass --set "${WINDSHARE_HOST}'s password: " > /dev/null
		fi
	fi

	export GIT_SSH=${BASEDIR}/data/environment.d/setup_ssh
	export GIT_ASKPASS=${BASEDIR}/data/environment.d/setup_askpass
	export SSH_ASKPASS=${BASEDIR}/data/environment.d/setup_askpass
	return 0
}

askpass_shutdown() {
	if [ -n "${WRL_ASKPASS_SOCKET}" ]; then
		${BASEDIR}/data/environment.d/setup_askpass --quit
		rm -f ${WRL_ASKPASS_SOCKET}
		unset WRL_ASKPASS_SOCKET
	fi
}
