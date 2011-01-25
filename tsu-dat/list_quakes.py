#!/usr/bin/env python

"""
This code implements the logic of David Burbidge's 'list_quakes' program.
Except the two output files are now in CSV format.
"""


import re


# pattern string used to split multimax data
SpacesPatternString = ' +'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(SpacesPatternString)

# a small value to perturb the user wave height limits
Epsilon = 1.0E-6


##
# @brief Function to do all the work - list the quakes selected.
def list_quakes(event_num, min_height, max_height, InvallFilename,
                TStarFilename, FaultXYFilename, QuakeProbFilename):
    ##
    # @brief Class to hold i_invall data
    class Inval(object):
        def __init__(self, lon, lat):
            self.lon = lon
            self.lat = lat

        def __str__(self):
            return '.lon=%g, .lat=%g' % (self.lon, self.lat)


    ##
    # @brief Class to hold T-**** data
    class TStar(object):
        def __init__(self, ipt, zquake, zprob, mag, slip, ng, ng_data):
            self.ipt = ipt
            self.zquake = zquake
            self.zprob = zprob
            self.mag = mag
            self.slip = slip
            self.ng_data = [int(i) for i in SpacesPattern.split(ng_data)]
            if len(self.ng_data) != ng:
                raise RuntimeError(1, "Error parsing T-***** data: %s" % msg)

        def __str__(self):
            return ('.ipt=%d, .zquake=%g, .zprob=%g, .mag=%g, '
                    '.slip=%g, .ng_data=%s' %
                    (self.ipt, self.zquake, self.zprob, self.mag,
                     self.slip, str(self.ng_data)))


    # read i_invall file
    try:
        fd = open(InvallFilename, "r")
        invall_lines = fd.readlines()
        fd.close()
    except IOError, msg:
        raise RuntimeError(1, "Error reading file '%s': %s" % 
                           (InvallFilename, msg))

    # trash the first three lines
    invall_lines = invall_lines[3:]

    # split i_invall data into fields
    invall_data = []
    for line in invall_lines:
        l = line.strip()
        (lon, lat, _) = SpacesPattern.split(l, maxsplit=2)
        invall_data.append(Inval(float(lon), float(lat)))

    del invall_lines

    # now read T-**** file, creating filename from event #
    try:
        fd = open(TStarFilename, "r")
        tstar_lines = fd.readlines()
        fd.close()
    except IOError, msg:
        raise RuntimeError(1, "Error reading file: %s" % msg)

    # trash the first line of T-**** data
    tstar_lines = tstar_lines[1:]

    # get the data from tstar_lines
    tstar_data = []
    min_wave = min_height - Epsilon
    max_wave = max_height + Epsilon
    for (ipt, line) in enumerate(tstar_lines):
        l = line.strip()
        (zquake, zprob, mag,
         slip, ng, ng_data) = SpacesPattern.split(l, maxsplit=5)
        zquake = float(zquake)
        zprob = float(zprob)
        mag = float(mag)
        slip = float(slip)
        ng = int(ng)
        ng_data = ng_data.strip()
        # only remember the data if zquake in wave height range and zprob > 0.0
        if zprob > 0.0 and (min_wave <= zquake <= max_wave):
#            tstar_data.append(TStar(ipt+1, zquake, zprob, mag,
#                                    slip, ng, ng_data))
            tstar_data.append(TStar(ipt, zquake, zprob, mag, slip, ng, ng_data))
    del tstar_lines

    # write out lines joining centroids
    try:
        outfd = open(FaultXYFilename, "w")
    except IOError, msg:
        raise RuntimeError(1, "Error opening output file: %s" % msg)

    outfd.write('Lon,Lat,Quake_ID,Subfault_ID\n')
    for t in tstar_data:
        for n in t.ng_data:
            outfd.write('%.4f,%.4f,%d,%d\n' %
                        (invall_data[n].lon, invall_data[n].lat, t.ipt, n))
    outfd.close()

    # write out quake probabilities
    try:
        outfd = open(QuakeProbFilename, "w")
    except IOError, msg:
        raise RuntimeError(1, "Error opening output file: %s" % msg)

    outfd.write('Quake_ID,Ann_Prob,z_max(m),Mag\n')
    for t in tstar_data:
        outfd.write('%d,%.5G,%.5f,%.2f\n' % (t.ipt, t.zprob, t.zquake, t.mag))
    outfd.close()

