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

ADDFUNCS+=" askpass_setup ;"

SHUTDOWNFUNCS+=" askpass_shutdown ;"

askpass_setup() {
	# If anspass is already enabled, use it instead!
	if [ -n "${ANSPASS_TOKEN}" ]; then
		return 0
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

	# TODO: Implement a command line method to specify username and password
	#if [ -n "${WINDSHARE_USER}" ]; then
	#	echo "${WINDSHARE_USER}" | ${BASEDIR}/data/environment.d/setup_askpass --set "Username for 'https://windshare.windriver.com': "
	#	echo "${WINDSHARE_PASS}" | ${BASEDIR}/data/environment.d/setup_askpass --set "Password for 'https://${WINDSHARE_USER}@windshare.windriver.com': "
	#fi

	export GIT_ASKPASS=${BASEDIR}/data/environment.d/setup_askpass
	export SSH_ASKPASS=${BASEDIR}/data/environment.d/setup_askpass
	return 0
}

askpass_shutdown() {
	if [ -n "${WRL_ASKPASS_SOCKET}" ]; then
		${BASEDIR}/data/environment.d/setup_askpass --quit
	fi
}
