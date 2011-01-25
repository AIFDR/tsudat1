#!/usr/bin/env python

"""
A data object class.

Used: obj = DataObj(lon=100.2, lat=-25.3, id=1)
      print obj.lon

The idea is to create an object with attributes with the
names of the keyword args on the creation call.
"""


class DataObj(object):
    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            msg = 'DataObj() must be called with keyword args ONLY!'
            raise RuntimeError(msg)

        self.__dict__ = kwargs

