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

# Regenerate the wrlinux-specific Toaster fixture file based on the 
# current 'layers_wrs_com.json' and 'default.xml'

setup_shutdown_func update_toaster_fixture_stop

update_toaster_fixture_stop() {
    # generate the wrlinux-specific Toaster fixture file
    $BASEDIR/bin/toaster_fixture.py
}

