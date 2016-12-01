#!/usr/bin/env python3

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

import os
import subprocess

# Setup-specific modules
import logger_setup

logger = logger_setup.setup_logging()

def run_cmd(cmd, environment=None, cwd=None, log=1, expected_ret=0, err=b'GitError', err2=b'error', err3=b'fatal', stderr=None, stdout=None):
    err_msg = []

    logger.debug('Running cmd: "%s"' % repr(cmd))
    if cwd:
        logger.debug('From %s' % cwd)

    # log 0 - output goes to stdout/stderr, not logged
    # log 1 - send output to plain
    # log 2 - send output to debug
    if log == 1 or log == 2:
        if stderr is None:
            stderr = subprocess.STDOUT

        ret = subprocess.Popen(cmd, env=environment, cwd=cwd, stderr=stderr, stdout=subprocess.PIPE)
        while True:
            output = ret.stdout.readline()
            if not output and ret.poll() is not None:
                break
            if output:
                output = output.strip()
                if len(err_msg) > 0 or output.startswith(err) or output.startswith(err2) or output.startswith(err3):
                    err_msg.append("%s" % output.decode('utf-8'))
                if log == 1:
                    logger.plain("%s" % output.decode('utf-8'))
                elif log == 2:
                    logger.debug("%s" % output.decode('utf-8'))
    else:
        logger.debug('output not logged for this command (%s) without verbose flag (-v).' % (cmd))
        ret = subprocess.Popen(cmd, env=environment, cwd=cwd, close_fds=True, stderr=stderr, stdout=stdout)

    ret.wait()
    if ret.returncode != expected_ret:
        if stderr != subprocess.DEVNULL:
            if environment:
                for key in environment.keys():
                    logger.to_file('%20s = %s' % (key, repr(environment[key])))
            if log != 2:
                logger.critical('cmd "%s" returned %d' % (cmd, ret.returncode))
            else:
                logger.debug('cmd "%s" returned %d' % (cmd, ret.returncode))

        msg = ''
        if log:
            if cwd:
                msg += cwd + ': '
            msg += " ".join(cmd) + '\n'
            msg += '\n'.join(err_msg)
            msg += '\n'
        raise Exception(msg)
    logger.debug('Finished running cmd: "%s"' % repr(cmd))

def fetch_url(url=None, auth=False):
    assert url is not None

    from urllib.request import urlopen, URLError
    from urllib.parse import urlparse

    if auth:
        import urllib

        logger.debug("Configuring authentication for %s..." % url)

        up = urlparse(url)

        client = os.environ.get('GIT_ASKPASS', None)
        if not client:
            client = os.environ.get('SSH_ASKPASS', None)
        if not client:
            raise Exception('Unable to get authentication via ASKPASS.')

        cmd = [ client, "Username for '%s://%s': " % (up.scheme, up.netloc) ]
        logger.debug("cmd: %s " % (cmd))

        ret = subprocess.Popen(cmd, env=os.environ, close_fds=True, stdout=subprocess.PIPE)
        uname = ""
        while True:
            lin = ret.stdout.readline()
            if not lin and ret.poll() is not None:
                break
            uname += lin.decode('utf-8')
        ret.wait()
        if ret.returncode != 0:
            raise Exception('Unable to get username for %s from %s.\n%s' % (up.netloc, client, cmd))
        uname = uname.rstrip('\n')

        cmd = [ client, "Password for '%s://%s@%s': " % (up.scheme, uname, up.netloc) ]
        logger.debug("cmd: %s " % (cmd))
        ret = subprocess.Popen(cmd, close_fds=True, stdout=subprocess.PIPE)
        passwd = ""
        while True:
            lin = ret.stdout.readline()
            if not lin and ret.poll() is not None:
                break
            passwd += lin.decode('utf-8')
        ret.wait()
        if ret.returncode != 0:
            raise Exception('Unable to get password for %s from %s.\n%s' % (up.netloc, client, cmd))
        passwd = passwd.rstrip('\n')

        logger.debug("%s: u:'%s' p:'%s'" % ( url, uname, passwd ))

        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, "%s://%s" % (up.scheme, up.netloc), uname, passwd)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)

    logger.debug("Fetching %s..." % url)

    try:
        res = urlopen(url)
    except URLError as e:
        if hasattr(e, 'code') and e.code == 401:
            res = fetch_url(url, auth=True)
        else:
            raise

    logger.debug("done.")

    return res
