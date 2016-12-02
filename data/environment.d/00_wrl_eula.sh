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

# Verify EULA acceptance

# We don't 'keep' this command & argument as acceptance is stored
setup_add_arg --accept-eula ACCEPT_EULA

setup_add_func eula_setup

eula_askuser() {
	accept=${ACCEPT_EULA}
	while [ "${accept}" != "yes" ] ; do
		echo
		echo "The End User License Agreement is available at:"
		echo "	${BASEDIR}/EULA"
		echo
		read -p "I have read the EULA and accept it - yes/no/read " accept
		case ${accept} in
			[yY][eE][sS])
				accept="yes"
				;;
			[nN][oO])
				echo "You must agree to the EULA to continue." >&2
				exit 1
				;;
			[rR] | [rR][eE][aA][dD])
				# Prefer 'less' if we have it, otherwise fall back to more
				if which less >/dev/null 2>&1 ; then
					cat ${BASEDIR}/EULA | less -P"Type 'q' when done."
				else
					cat ${BASEDIR}/EULA | more
				fi
				;;
			*)
				echo "Only yes, no and read are accepted." >&2
				;;
		esac
	done

	echo

	mkdir -p config
	# Log the EULA acceptance if there is any question in the future...
	{
		echo "#End User License Agreement Accepted"
		echo "EULA_DATE=\"$(date)\""
		echo "EULA_USER=\"$(whoami)@$(hostname)\""
		echo "EULA_VERSION=\"$(tail -n 1 ${BASEDIR}/EULA)\""
		echo "EULA_SHA=\"$(shasum ${BASEDIR}/EULA | cut -d ' ' -f 1)\""
		echo
	} >> config/eula_accepted
}

eula_setup() {
	if [ -e config/eula_accepted ]; then
		. ./config/eula_accepted
	fi
	NEW_SHA=$(shasum ${BASEDIR}/EULA | cut -d ' ' -f 1)
	if [ -n "${EULA_SHA}" -a "${NEW_SHA}" != "${EULA_SHA}" ]; then
		echo "The End User User License has changed since you last agreed to it."
		EULA_SHA=""
	fi
	if [ -z "${EULA_SHA}" -o -z "${EULA_VERSION}" -o -z "${EULA_DATE}" ]; then
		eula_askuser
	else
		echo "End User License Agreement '${EULA_VERSION}' agreed to by ${EULA_USER} on ${EULA_DATE}."
	fi
}
