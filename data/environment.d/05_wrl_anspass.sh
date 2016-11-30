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

# This needs to run after anspass is installed by the buildtools-tarball

ADDFUNCS+=" anspass_post_setup ;"

SHUTDOWNFUNCS+=" askpass_shutdown ;"

. ${BASEDIR}/data/environment.d/setup_anspass

anspass_post_setup() {
	# Do we have anspassd available yet?
	if which anspassd >/dev/null 2>&1 ; then
		anspass_setup
	fi
}

anspass_shutdown() {
	# Did we start it?  if so we need to shut it down!
	if [ -n "${wrl_anspass_started}" ]; then
		anspass-ctrl --quit
	fi
}

