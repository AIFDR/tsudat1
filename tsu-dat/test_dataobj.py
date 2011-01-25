#!/usr/bin/env python

"""Test functions in util.py."""


import os
import unittest
import tempfile
import shutil

import dataobj


class Test_DataObj(unittest.TestCase):

    def test_simple(self):
        # test 1 - just one attribute
        do = dataobj.DataObj(test=1)
        self.failUnless(hasattr(do, 'test'))
        self.failUnless(do.test == 1)

        # test 2 - lotsa attributes
        do = dataobj.DataObj(alpha=1, beta=1.0, gamma='abc', delta=(1,2),
                             epsilon=[2,3], zeta={1:'one'})
        self.failUnless(hasattr(do, 'alpha'))
        self.failUnless(hasattr(do, 'beta'))
        self.failUnless(hasattr(do, 'gamma'))
        self.failUnless(hasattr(do, 'delta'))
        self.failUnless(hasattr(do, 'epsilon'))
        self.failUnless(hasattr(do, 'zeta'))
        self.failUnless(do.alpha == 1)
        self.failUnless(do.beta == 1.0)
        self.failUnless(do.gamma == 'abc',
                        "do.gamma(%s) != 'abc'" % str(do.gamma))
        self.failUnless(do.delta == (1,2),
                        'do.delta(%s) != (1, 2)' % str(do.delta))
        self.failUnless(do.epsilon == [2,3],
                        'do.epsilon(%s) != [2,3]' % str(do.epsilon))
        self.failUnless(do.zeta == {1: 'one'},
                        "do.zeta(%s) != {1:'one'}" % str(do.zeta))

        # now check that we fail when we should
        self.failUnlessRaises(RuntimeError, dataobj.DataObj, 2, test=1)


#-------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()


