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

    formatter = ScreenFormatter("%(levelname)s: %(message)s")
    stream_h = logging.StreamHandler(output)
    stream_h.setFormatter(formatter)

    # Logging timezone is UTC
    stream_h.converter = time.gmtime

    logger.setLevel(level)
    logger.addHandler(stream_h)

    logging.addLevelName(PLAIN_LOG_LEVEL, "PLAIN")
    logging.Logger.plain = plain

    return logger

class FileFormatter(logging.Formatter):
    def format(self, record):
        # FileHandler doesn't need color
        record.levelname = record.levelname_orig
        return logging.Formatter.format(self, record)

def setup_logging_file(log_file):
    """Add a logging.FileHandler to the logger"""
    global logger
    logger.debug("Logging to %s" % log_file)
    formatter = FileFormatter(FILE_LOG_FORMAT)
    file_h = logging.FileHandler(log_file)
    # Logging timezone is UTC
    file_h.converter = time.gmtime
    file_h.setFormatter(formatter)
    file_h.setLevel(TO_FILE_LOG_LEVEL)
    logger.addHandler(file_h)
    logging.addLevelName(TO_FILE_LOG_LEVEL, 'TO_FILE')
    logging.Logger.to_file = to_file



class ScreenFormatter(logging.Formatter):
    """ScreenFormatter exists to allow printing plain messages with a different
    format than other log levels.
    """

    RED, GREEN, YELLOW, BLUE = [1, 2, 3, 4]

    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"

    COLORS = {
        'INFO': GREEN,
        'DEBUG': BLUE,
        'WARNING': YELLOW,
        'ERROR': RED,
        'CRITICAL': RED
    }

    def format(self, record):
        levelname = record.levelname
        # Save it for FileHandler
        record.levelname_orig = levelname
        if levelname == "PLAIN":
            msg = record.getMessage()
        else:
            if sys.stdout.isatty():
                fore_color = 30 + self.COLORS[levelname]
                levelname_color = self.COLOR_SEQ % fore_color + levelname + self.RESET_SEQ
                record.levelname = levelname_color
                msg = logging.Formatter.format(self, record)
            msg = logging.Formatter.format(self, record)
        return msg

# Add a class to emulate stdout/stderr
class LoggerOut:
    def __init__(self, logger):
        self.logger = logger

    def write(self, message):
        # We skip any lines that are simply a '\n'.
        # The logger always ends in the equivalent of a \n, and many programs
        # seem to like to insert blank lines using '\n' which makes the
        # logging confusing.
        if message != '\n':
            self.logger(message)

    def flush(self):
        # We print all messages immediately, so flush is a no-op.
        pass
