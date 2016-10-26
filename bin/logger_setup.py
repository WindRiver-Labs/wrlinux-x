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
#
"""
logger_setup is the infrastructure for setup.py to log both to the screen and
to a file.  Up on initialisation, the logger will only log to the screen and
have two new log levels:
        plain = 15
        to_file = 1

plain logs will not be prefixed with the logging type when outputting to the
output passed to the setup_logging function (which defaults to sys.stdout).
"""
import logging
import sys
import time

FILE_LOG_FORMAT = '%(asctime)s %(levelname)8s [%(filename)s:%(lineno)s' \
                + ' - %(funcName)20s(): %(message)s'

# INFO = 20
PLAIN_LOG_LEVEL = 15
# DEBUG = 10
TO_FILE_LOG_LEVEL = 1
# NOTSET = 0

logger = None

def plain(self, message, *args, **kws):
    """Function to be added to the logger for plain log level support"""

    if self.isEnabledFor(PLAIN_LOG_LEVEL):
        self._log(PLAIN_LOG_LEVEL, message, args, **kws)

def to_file(self, message, *args, **kws):
    """Function to be added to the logger for to_file log level support"""
    if self.isEnabledFor(TO_FILE_LOG_LEVEL):
        self._log(TO_FILE_LOG_LEVEL, message, args, **kws)


def setup_logging(level=PLAIN_LOG_LEVEL, output=sys.stdout):
    """create the setup.py singleton logger."""
    global logger
    if logger:
        return logger

    logger = logging.getLogger('setup.py')

    formatter = ScreenFormatter(plain_log_level=PLAIN_LOG_LEVEL)
    stream_h = logging.StreamHandler(output)
    stream_h.setFormatter(formatter)

    # Logging timezone is UTC
    stream_h.converter = time.gmtime


    logger.setLevel(level)
    logger.addHandler(stream_h)

    logging.addLevelName(PLAIN_LOG_LEVEL, "PLAIN")
    logging.Logger.plain = plain

    logging.addLevelName(TO_FILE_LOG_LEVEL, 'TO_FILE')
    logging.Logger.to_file = to_file

    return logger


def setup_logging_file(log_file, log_format=FILE_LOG_FORMAT):
    """Add a logging.FileHandler to the logger"""
    global logger
    logger.debug("Logging to %s" % log_file)
    formatter = logging.Formatter(fmt=log_format)
    file_h = logging.FileHandler(log_file)
    # Logging timezone is UTC
    file_h.converter = time.gmtime
    file_h.setFormatter(formatter)
    file_h.setLevel(TO_FILE_LOG_LEVEL)
    logger.addHandler(file_h)




class ScreenFormatter(logging.Formatter):
    """ScreenFormatter exists to allow printing plain messages with a different
    format than other log levels.
    """

    plain_format = "%(msg)s"

    def __init__(self, fmt="%(levelname)s: %(msg)s", plain_log_level=15):
        self.plain_log_level = plain_log_level
        logging.Formatter.__init__(self, fmt)


    def format(self, record):

        format_orig = self._fmt

        if record.levelno == self.plain_log_level:
            self._fmt = self.plain_format
            self._style._fmt = self._fmt

        result = logging.Formatter.format(self, record)

        self._fmt = format_orig
        self._style._fmt = self._fmt
        return result


