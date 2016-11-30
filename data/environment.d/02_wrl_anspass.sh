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

ADDFUNCS+=" anspass_pre_setup ;"

. ${BASEDIR}/data/environment.d/setup_anspass

anspass_pre_setup() {
	# Do we have anspassd available yet?
	if which anspassd >/dev/null 2>&1 ; then
		anspass_setup
	fi
}
