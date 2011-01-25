#!/usr/bin/env python

"""
A simple logger.

TODO: Use python logging, maybe.
"""

BSD_2Clause_Licence = """
Copyright 2010 Ross Wilson (r-w@manontroppo.org). All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

  1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER ``AS IS'' AND ANY EXPRESS
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are
those of the authors and should not be interpreted as representing official
policies, either expressed or implied, of the copyright holder.
"""


import os
import datetime
import traceback



################################################################################
# A simple logger.
# 
# Simple usage:
#     import log
#     log = log.Log('my_log.txt', Log.DEBUG)
#     log('A line in the log at the default level (DEBUG)')
#     log('A log line at WARN level', Log.WARN)
#     log.debug('log line issued at DEBUG level')
# 
# Based on the 'borg' recipe from [http://code.activestate.com/recipes/66531/].
# 
# Log levels styled on the Python 'logging' module.
################################################################################

class Log(object):

    __shared_state = {}                # this __dict__ shared by ALL instances

    # the predefined logging levels (a la python logging)
    CRITICAL = 50
    ERROR = 40
    WARN = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0

    _level_num_to_name = {NOTSET: 'NOTSET',
                          DEBUG: 'DEBUG',
                          INFO: 'INFO',
                          WARN: 'WARN',
                          ERROR: 'ERROR',
                          CRITICAL: 'CRITICAL'}

    # maximum length of filename (enforced)
    MaxNameLength = 12

    def __init__(self, logfile=None, level=NOTSET, append=True):
        """Initialise the logging object.
        
        logfile the path to the log file
        level   logging level - don't log below this level
        append  True if log file is appended to, otherwise overwritten
        """

        # make sure we have same state as all other log objects
        self.__dict__ = self.__shared_state

        # don't allow logfile to change after initially set
        if not hasattr(self, 'logfile'):
            if logfile is None:
                logfile = '%s.log' % __name__
            self.level = level
            self.logfile = logfile
            if append:
                self.logfd = open(logfile, 'a')
            else:
                self.logfd = open(logfile, 'w')

            self.critical('='*55)
            self.critical('Log started on %s, log level=%s'
                 % (datetime.datetime.now().ctime(),
                    Log._level_num_to_name[level]))
            self.critical('-'*55)

    def __call__(self, msg, *args):
        """Call on the logging object.

        msg     message string to log
        args    extra args tuple - first is assumed to be log level
                (if not given, assume self.level)
        """

        # get level to log at
        level = self.level
        if args:
            level = args[0]

        # are we going to log?
        if level < self.level:
            return

        # get time
        to = datetime.datetime.now()
        hr = to.hour
        min = to.minute
        sec = to.second
        msec = to.microsecond

        # caller information - look back for first module != <this module name>
        frames = traceback.extract_stack()
        frames.reverse()
        try:
            (_, mod_name) = __name__.rsplit('.', 1)
        except ValueError:
            mod_name = __name__
        for (fpath, lnum, mname, _) in frames:
            (fname, _) = os.path.basename(fpath).rsplit('.', 1)
            if fname != mod_name:
                break

        # get string for log level
        loglevel = Log._level_num_to_name[level]

        fname = fname[:Log.MaxNameLength]
        self.logfd.write('%02d:%02d:%02d.%06d|%8s|%*s:%-4d|%s\n'
                         % (hr, min, sec, msec, loglevel, Log.MaxNameLength,
                            fname, lnum, msg))

    def critical(self, msg):
        """Log a message at CRITICAL level."""

        self(msg, Log.CRITICAL)

    def error(self, msg):
        """Log a message at ERROR level."""

        self(msg, Log.ERROR)

    def warn(self, msg):
        """Log a message at WARN level."""

        self(msg, Log.WARN)

    def info(self, msg):
        """Log a message at INFO level."""

        self(msg, Log.INFO)

    def debug(self, msg):
        """Log a message at DEBUG level."""

        self(msg, Log.DEBUG)

    def __del__(self):
        self.logfd.close()

