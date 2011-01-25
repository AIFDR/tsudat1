#!/usr/bin/env python

"""Test functions in util.py."""


import os
import unittest
import tempfile
import shutil

import util


class Test_Util(unittest.TestCase):

    def test_readPointsDataFile(self):
        # create temporary data file
        tmp_dir = tempfile.mkdtemp(prefix='Tsu-DAT_', dir='/var/tmp/')
        tmp_file = os.path.join(tmp_dir, 'temp.dat')
        fd = open(tmp_file, 'w')
        fd.write('100.0 20.0 1\n')
        fd.write('110.0 25.0 2\n')
        fd.close()

        # read temp file
        data = util.readPointsDataFile(tmp_file)

        # check returned data
        self.failUnless(data[0].lon == 100.0)
        self.failUnless(data[0].lat == 20.0)
        self.failUnless(data[0].id == 1)

        self.failUnless(data[1].lon == 110.0)
        self.failUnless(data[1].lat == 25.0)
        self.failUnless(data[1].id == 2)

        # clean up
        shutil.rmtree(tmp_dir)

#-------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()


