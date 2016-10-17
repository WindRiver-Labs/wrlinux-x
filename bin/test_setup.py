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

import unittest
import logging
import sys
import os

from setup import Setup
from setup_argparse import Setup_Argparse

class test_setup(unittest.TestCase):
    """Test cases for setup"""

    def __init__(self, *args, **kwargs):
        super(test_setup, self).__init__(*args, **kwargs)
        self.test_dir = 'test/directory'
        self.test_xml = 'xml/broken.xml'
        self.test_jobs = '42'

        self.stderr_orig = sys.stderr
        self.stdout_orig = sys.stdout


    def setUp(self):
        # Set up Object
        self.setup = Setup()
        # Silence output
        null = open(os.devnull,'wb')
        sys.stdout = sys.stderr = null
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Restore output
        logging.disable(logging.NOTSET)
        sys.stderr = self.stderr_orig
        sys.stdout = self.stdout_orig
        # remove Object
        del self.setup

    # Make sure the init of the setup program sets what should be set.
    def test_init(self):
        self.set_rootdir()

        fn = self.rootdir + self.setup.BINTOOLS_SSL_CERT
        dn = self.rootdir + self.setup.BINTOOLS_SSL_DIR
        self.assertTrue(self.setup.env["GIT_SSL_CAINFO"] == fn)
        self.assertTrue(self.setup.env["CURL_CA_BUNDLE"] == fn)
        self.assertTrue(self.setup.env["SSL_CERT_FILE"]  == fn)
        self.assertTrue(self.setup.env["SSL_CERT_DIR"]   == dn)
        self.assertEqual(self.setup.env["HOME"], self.rootdir)
        self.assertEqual(self.setup.env["PWD"], self.rootdir)

        self.assertEqual(self.setup.jobs, self.setup.default_jobs)

        self.assertEqual(self.setup.quiet, '--quiet')

        self.assertEqual(self.setup.xml, self.setup.default_xml)


    def test_set_debug(self):
        self.setup.set_debug()
        self.assertEqual(self.setup.get_log_level(), logging.DEBUG)
        self.assertTrue(self.setup.env["REPO_CURL_VERBOSE"] == '1')

    def test_evaluate_args(self):
        # Test argparse for -v, -m, and -j
        parser = Setup_Argparse(self.setup)
        parser.evaluate_args(['-v', '-m', self.test_xml, '-j' , self.test_jobs])
        # Ensure verbose worked
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.DEBUG)
        self.assertTrue(self.setup.env["REPO_CURL_VERBOSE"] == '1')
        self.assertTrue(self.setup.quiet == '')
        # Ensure the xml is different.
        self.assertTrue(self.setup.xml == self.test_xml)
        # Ensure the job count is different.
        self.assertTrue(self.setup.jobs == self. test_jobs)

    def test_evaluate_args_long(self):
        # Test argparse for --verbiose, --xml, and --jobs
        parser = Setup_Argparse(self.setup)
        parser.evaluate_args(['--verbose', '--xml', self.test_xml, '--jobs' , self.test_jobs])
        # Ensure verbose worked
        self.assertEqual(self.setup.get_log_level(), logging.DEBUG)
        self.assertTrue(self.setup.env["REPO_CURL_VERBOSE"] == '1')
        self.assertTrue(self.setup.quiet == '')
        # Ensure the xml is different.
        self.assertTrue(self.setup.xml == self.test_xml)
        # Ensure the job count is different.
        self.assertTrue(self.setup.jobs == self. test_jobs)

    def test_setup_env(self):
        self.set_incorrect_rootdir()
        self.setup.rootdir = self.rootdir
        self.setup.setup_env()

        # set_ssl_cert test
        fn = self.rootdir + self.setup.BINTOOLS_SSL_CERT
        dn = self.rootdir + self.setup.BINTOOLS_SSL_DIR
        self.assertTrue(self.setup.env["GIT_SSL_CAINFO"] == fn)
        self.assertTrue(self.setup.env["CURL_CA_BUNDLE"] == fn)
        self.assertTrue(self.setup.env["SSL_CERT_FILE"]  == fn)
        self.assertTrue(self.setup.env["SSL_CERT_DIR"]   == dn)

        # set_repo_git_env
        self.assertEqual(self.setup.env["HOME"], self.rootdir)

        # set_cwd
        self.assertEqual(self.setup.env["PWD"], self.rootdir)

        # __init__
        self.assertEqual(self.setup.jobs, self.setup.default_jobs) 
        self.assertEqual(self.setup.quiet, '--quiet')
        self.assertEqual(self.setup.xml, self.setup.default_xml)

    def test_set_cwd(self):
        self.setup.rootdir = self.test_dir
        self.setup.set_cwd()
        self.assertEqual(self.setup.env["PWD"], self.test_dir)

    def test_set_repo_git_env(self):
        self.setup.rootdir = self.test_dir
        self.setup.set_repo_git_env()
        self.assertEqual(self.setup.env["HOME"], self.test_dir)

    def test_set_ssl_cert(self):
        self.setup.rootdir = self.test_dir
        fn = self.setup.rootdir + self.setup.BINTOOLS_SSL_CERT
        dn = self.setup.rootdir + self.setup.BINTOOLS_SSL_DIR
        self.setup.set_ssl_cert()
        self.assertTrue(self.setup.env["GIT_SSL_CAINFO"] == fn)
        self.assertTrue(self.setup.env["CURL_CA_BUNDLE"] == fn)
        self.assertTrue(self.setup.env["SSL_CERT_FILE"]  == fn)
        self.assertTrue(self.setup.env["SSL_CERT_DIR"]   == dn)

    def set_rootdir(self):
        self.rootdir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')

    def set_incorrect_rootdir(self):
        # Incorrect path, but okay for testing.
        self.rootdir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    unittest.main()
