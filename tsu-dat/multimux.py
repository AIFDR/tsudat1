#!/usr/bin/env python

"""
Do what David Burbidge's 'get_multimux' program does.
"""

import os
import re
import shutil

import config as cfg
import log
log = log.Log()


# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(' +')


def multimux(event_id, save_dir):
    """Do what David Burbidge's 'get_multimux' program does.

    event_id  ID of the event
    save_dir  path to save directory base
    """

    # get path to output file
    event_dir = os.path.join(save_dir, 'boundaries', str(event_id))
    if os.path.isdir(event_dir):
        shutil.rmtree(event_dir)
    os.makedirs(event_dir)
    fault_file = os.path.join(event_dir, cfg.EventFile)

    # get the fault name data
    filename = os.path.join(cfg.MultimuxDirectory, cfg.FaultNameFilename)
    try:
        fd = open(filename, "r")
        fault_names = [fn.strip() for fn in fd.readlines()]
        fd.close()
    except IOError, msg:
        raise RuntimeError(1, "Error reading file: %s" % msg)

    # open the output file
    try:
        outfd = open(fault_file, "w")
    except IOError, msg:
        raise RuntimeError(1, "Error opening output file: %s" % msg)

    # handle each fault
    nquake = 0
    for fn in fault_names:
        # create the filename for the multimux data file
        mmx_filename = 'i_multimux-%s' % fn
        mmx_filename = os.path.join(cfg.MultimuxDirectory, mmx_filename)

        # Read all data in file, checking as we go
        try:
            infd = open(mmx_filename, "r")
        except IOError, msg:
            raise RuntimeError(1, "Error opening file: %s" % msg)

        # check fault name in file is as expected
        mux_faultname = infd.readline().strip()
        if mux_faultname != fn:
            raise RuntimeError(1, "Error reading file")

        # read data
        while True:
            # get number of subfaults, EOF means finished
            try:
                nsubfault = infd.readline()
            except IOError:
                raise RuntimeError(1, "Error reading file")

            if not nsubfault:
                break
            nsubfault = int(nsubfault)

            nquake += 1
            if nquake == event_id:
                outfd.write(' %d\n' % nsubfault)
                for i in range(nsubfault):
                    line = infd.readline()
                    (subfaultname, slip, prob, mag, _) = \
                                   SpacesPattern.split(line, maxsplit=4)
                    subfaultname = subfaultname.strip()
                    slip = float(slip)
                    outfd.write(" %s %g\n" % (subfaultname, slip))
            else:
                for i in range(nsubfault):
                    try:
                        infd.readline()
                    except IOError:
                        raise RuntimeError(1,
                                           "Something wrong at bottom of file %s" %
                                           mux_faultname)

        infd.close()
    outfd.close()

