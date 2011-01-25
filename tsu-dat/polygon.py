#!/usr/bin/env python

"""Determine if a point is inside a given polygon or not.

NOTE: Points precisely on the edge of the polygon may be inside
      *or* outside the polygon.  Does this matter for Tsu-DAT?
"""


def point_in_poly(x, y, poly):
    """Determine if a point is inside a polygon.

    x     X coordinate of point
    y     Y coordinate of point
    poly  list of [(x,y), ...] points, assumed closed

    Return True if point is inside polygon.

    Note that a point precisely on an edge may be considered in or out.
    """

    n = len(poly)
    inside = False
    (p1x, p1y) = poly[0]

    # loop over i = (1, 2, ..., n) so last poly index is poly[0] (start point)
    for i in range(1, n+1):
        (p2x, p2y) = poly[i % n]

        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside

        p1x, p1y = p2x, p2y

    return inside

