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

# Check if the buildtools are available, if so load it early...

BUILDTOOLS="${BUILDTOOLS:-bin/buildtools}"

ADDFUNCS+=" buildtools_pre_setup ;"

buildtools_pre_setup() {
	ENVIRON=$(find -L ${BUILDTOOLS} -name "environment-setup-${SDKARCH}-*-linux" 2>/dev/null | head -n1)
	if [ -z "${ENVIRON}" ]; then
		# Nothing there yet...
		return
	fi
	. "${ENVIRON}"
	if [ $? -ne 0 ]; then
		# Something went wrong.. ignore it
		return
	fi
}
