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

setup_add_func anspass_late_setup

setup_shutdown_func anspass_shutdown

. ${BASEDIR}/data/environment.d/setup_anspass

# anspass_setup defined in setup_anspass
anspass_late_setup() {
	# If we've already started anspass, skip this
	if [ -n "${ANSPASS_PATH}" -a -n "${ANSPASS_TOKEN}" ]; then
		return 0
	fi

	# We want to use askpass (if enabled), no reason to invoke
	# anspass yet.... unless the user passed in a user/pass
	# meaning they want an offline install, no Q's asked.
	if [ -n "${WINDSHARE_USER}" ]; then
		anspass_setup
		return $?
	fi

	return 0
}

# anspass_stop defined in setup_anspass
anspass_shutdown() {
	anspass_stop
}
