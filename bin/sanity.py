#!/usr/bin/env python3

# Copyright (C) 2019 Wind River Systems, Inc.
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

# Please keep these sorted.
"""
sanity.py module to help setup program to do sanity checks.
"""

import os
import sys
import logger_setup
logger = logger_setup.setup_logging()

# Fixed list of tools needed.
fixed_hosttools = """
 [ ar as awk basename bash bzip2 cat chgrp chmod chown chrpath
 cmp comm cp cpio cpp cut date dd diff diffstat dirname du echo
 egrep env expand expr false fgrep file find flock g++ gawk gcc
 getconf getopt git grep gunzip gzip head hostname iconv id install
 ld ldd ln ls make makeinfo md5sum mkdir mknod mktemp mv nm objcopy
 objdump od patch perl pod2man pr printf pwd python2 python2.7
 python3 ranlib readelf readlink realpath rm rmdir rpcgen sed
 seq sh sha256sum sleep sort split stat strings strip tail tar tee
 test touch tr true uname uniq wc wget which xargs
"""

def which(path, item, direction = 0, executable=False):
    """
    Locate `item` in the list of paths `path` (colon separated string like $PATH).
    If `direction` is non-zero then the list is reversed.
    If `executable` is True then the candidate has to be an executable file,
    otherwise the candidate simply has to exist.
    """

    if executable:
        is_candidate = lambda p: os.path.isfile(p) and os.access(p, os.X_OK)
    else:
        is_candidate = lambda p: os.path.exists(p)

    paths = (path or "").split(':')
    if direction != 0:
        paths.reverse()

    for p in paths:
        next = os.path.join(p, item)
        if is_candidate(next):
            if not os.path.isabs(next):
                next = os.path.abspath(next)
            return next

    return ""

def check_hosttools():
    """
    Check tools on host. Error out if some tool is missing. 
    """
    host_tools = []
    notfound = []

    try:
        import settings
        host_tools = settings.REQUIRED_HOST_TOOLS.split()
    except Exception as e:
        logger.warn("Failed to get host tools from setting.py: %s" % e)
        logger.warn("Use a fixed list of host tools for checking.")
        host_tools = []
    
    if not host_tools:
        # Fall back to a fixed list of host tools
        host_tools = fixed_hosttools.split()

    path = os.environ['PATH']
    for tool in host_tools:
        srctool = which(path, tool, executable=True)
        # gcc/g++ may link to ccache on some hosts, e.g.,
        # /usr/local/bin/ccache/gcc -> /usr/bin/ccache, then which(gcc)
        # would return /usr/local/bin/ccache/gcc, but what we need is
        # /usr/bin/gcc, this code can check and fix that.
        if "ccache" in srctool:
            srctool = bb.utils.which(path, tool, executable=True, direction=1)
        if not srctool:
            notfound.append(tool)
    if notfound:
        logger.error("Required host tools not available: %s" % notfound)
        sys.exit(1)
    else:
        logger.info("All required host tools are available.")

# allow running sanity checks individually
if __name__ == '__main__':
    check_hosttools()
