# Copyright (C) 2017 Wind River Systems, Inc.
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

# For compatibility with the commercial version, we need to allow for the
# accept-eula argument, even though it's a no-op

# We don't 'keep' this command & argument as the option is not longer used.
setup_add_arg --kernel KTYPE

setup_add_func ktype_check

ktype_check() {
	if [ -n "${KTYPE+x}" ]; then
		echo
		echo "WARNING: argument --kernel is no longer supported and will be ignored." >&2
		echo "         To adjust the LINUX_KERNEL_TYPE, edit the build conf/local.conf file." >&2
		echo
	fi
}
