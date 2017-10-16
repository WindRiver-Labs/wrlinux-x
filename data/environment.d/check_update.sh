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

# Check if this is an existing product, if the default.xml has beeen changed
# warning the user they may need to update any build directories

setup_add_func check_update_start
setup_shutdown_func check_update_stop

check_update_start() {
	if [ -e config/bblayers.conf.sample ]; then
		SHASUM_BBLAYERS=$(shasum config/bblayers.conf.sample | cut -d ' ' -f 1)
	fi

	if [ -e config/local.conf.sample ]; then
		SHASUM_LOCALCONF=$(shasum config/local.conf.sample | cut -d ' ' -f 1)
	fi
}

check_update_stop() {
	if [ -e config/bblayers.conf.sample -a -n "${SHASUM_BBLAYERS}" ]; then
		NEW_SHASUM=$(shasum config/bblayers.conf.sample | cut -d ' ' -f 1)
		if [ "${NEW_SHASUM}" != "${SHASUM_BBLAYERS}" ]; then
			cat << EOF

Note: The project layers have been updated. You should inspect the
conf/bblayers.conf file in all build directories and syncronize them to match
the updated conf/bblayers.conf.sample file, as necessary.

EOF
		fi
	fi

	if [ -e config/local.conf.sample -a -n "${SHASUM_LOCALCONF}" ]; then
		NEW_SHASUM=$(shasum config/local.conf.sample | cut -d ' ' -f 1)
		if [ "${NEW_SHASUM}" != "${SHASUM_LOCALCONF}" ]; then
			cat << EOF

Note: The project local.conf.sample has been updated.  You should inspect the
conf/local.conf file in all build directories and syncronize them to match,
as necessary.

EOF
		fi
	fi
}
