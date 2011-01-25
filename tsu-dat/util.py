#!/usr/bin/env python

"""
Utility routines used by Tsu-DAT.
"""


import dataobj


################################################################################
# File I/O routines.
################################################################################

def readPointsFile(filename):
    """Read a file of points data into memory.

    filename  path to the points data

    Returns a list of [lon, lat, ...].

    Any fields after lon & lat are split on space and added to data list.
    """

    # read in points data
    try:
        fd = open(filename, 'r')
    except IOError:
        msg = "Can't find points file '%s'" % filename
        raise RuntimeError(msg)

    layer_data = []
    for (lnum, line) in enumerate(fd.readlines()):
        data = line.split()
        if len(data[0]) < 2:
            msg = 'File %s needs at least two fields on line %d' % lnum
            raise RuntimeError(msg)
        new_line = [float(data[0]), float(data[1])]
        new_line.extend(data[2:])
        layer_data.append(new_line)
    fd.close()

    return layer_data


def readPointsDataFile(filename):
    """Read a file of points data into memory.

    filename  path to the points data

    Returns a list of pySlip data objects.

    Fields in the file are "lon lat id".  These are the attributes for each data
    object.
    """

    # read in points data
    try:
        fd = open(filename, 'r')
    except IOError:
        msg = "Can't find points file '%s'" % filename
        raise RuntimeError(msg)

    layer_data = []
    for (lnum, line) in enumerate(fd.readlines()):
        data = line.strip().split()
        if len(data) != 3:
            msg = ('File %s should have three fields on line %d'
                   % (filename, lnum))
            raise RuntimeError(msg)
        obj = dataobj.DataObj(lon=float(data[0]), lat=float(data[1]),
                              id=int(data[2]))
        layer_data.append(obj)
    fd.close()

    return layer_data



