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

# Check if we have access to anspassd, if so try to setup anspass.

# Quick walk through args to look for --no-anspass 
#  We do it here because we need to decide right now if the anspass
#  needs to be started/stopped

args="$@"
if [ "${args/--no-anspass//}" != "${args}" ] ; then
	export NO_ANSPASS=1
fi

if [ "$NO_ANSPASS" = "" ] ; then
setup_add_func anspass_setup

setup_shutdown_func anspass_early_shutdown

. ${BASEDIR}/data/environment.d/setup_anspass
fi

# anspass_setup defined in setup_anspass

# This isn't really a shutdown, but a transfer.  Before we stop 'askpass', we
# need to transfer any credential into anspass.  By this point anspass
# should be ready for a transfer.
#
# If anspass isn't running yet, we have to start it, so we can transfer the
# credentials.  But it should be shutdown right after.
#
# anspass_start defined in setup_anspass
anspass_early_shutdown() {
	# Before shutting down, try to transfer askpass items to anspass
	if [ -n "${WRL_ASKPASS_SOCKET}" ]; then
		if [ -z "$(${BASEDIR}/data/environment.d/setup_askpass --dump)" ]; then
			return 0
		fi
		# If anspass is not running, we start it so we can transfer
		# credentials for storage
		if [ -z "${ANSPASS_PATH}" -o -z "${ANSPASS_TOKEN}" ]; then
			anspass_start
		fi
		echo "Storing credentials into anspass."
		${BASEDIR}/data/environment.d/setup_askpass --dump | anspass_transfer
		anspass_stop
	fi
	return 0
}
