#!/usr/bin/env python

"""
A 'slippy map' widget for wxPython.

So why is this widget called 'pySlip'?

Well, in the OpenStreetMap world[1], a 'slippy map' is a browser map view served
by a tile server that can be panned and zoomed in the same way as popularised by
Google maps.  Such a map feels 'slippery', I guess.

Rather than 'slippy' I went for the slightly more formal 'pySlip' since the
thing is written in Python and therefore must have the obligatory 'py' prefix.

Even though this was originally written for a geographical application, the
underlying system only assumes a cartesian 2D coordinate system.  So pySlip
could be used to present a game map, 2D CAD view, or whatever.  The major
difficulty for most uses is to generate the map tiles.

[1] http://wiki.openstreetmap.org/index.php/Slippy_Map
"""


__license__ = """
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

__all__ = ['pySlip']


import os
import sys
import copy
import glob
try:
    import cPickle as pickle
except ImportError:
    import pickle
import Image
import wx
import traceback

import log
log = log.Log('pyslip.log')


################################################################################
# The wxPython pySlip widget
################################################################################

class pySlip(wx.Panel):
    """A widget to display a tiled map, a la Google maps."""

################################################################################

    ######
    # An internal class for map tiles
    ######

    class Tiles(object):
        """An object to handle a pyslip tiles directory.

        Uses 'elephant' caching - it never forgets!
        TODO: Add more sophisticated limit + 'drop LRU' caching.
        """

        # the name of the tile info file (under the main tile dir)
        TileInfoFilename = 'tile.info'

        # expected form of individual tile level directories (2 decimal digits)
        TileFilenameTemplate = '[0-9][0-9]'

        # name of picture file to use if tile missing (under the main tile dir)
        MissingTileFilename = 'missing_tile.png'

        def __init__(self, tile_dir):
            """Initialise a Tiles instance.

            tile_dir  root directory of tiles
            """

            # open top-level info file
            self.tile_dir = tile_dir
            info_file = os.path.join(tile_dir, self.TileInfoFilename)
            try:
                fd = open(info_file, 'rb')
                (self.extent, self.tile_size,
                     self.sea_colour, self.land_colour) = pickle.load(fd)
                fd.close()
            except IOError:
                msg = "'%s' doesn't appear to be a tile directory" % tile_dir
                raise RuntimeError(msg)

            (self.tile_size_x, self.tile_size_y) = self.tile_size

            # get list of tile levels
            tile_mask = os.path.join(tile_dir, self.TileFilenameTemplate)
            self.levels = [int(os.path.basename(l))
                               for l in glob.glob(os.path.join(tile_mask))]

            # setup the tile caches
            self.cache = {}
            for l in self.levels:
                self.cache[l] = {}

            # set min and max tile levels
            self.min_level = min(self.levels)
            self.max_level = max(self.levels)

        def use_level(self, n):
            """Prepare to serve tiles from the required level.

            n    The required level

            Returns a tuple (map_width, map_height) if succesful, else None.
            The width/height values are pixels.
            """

            # try to get cache for this level, no cache means no level
            try:
                self.tile_cache = self.cache[n]
            except KeyError:
                return None

            # get tile info
            info = self.get_info(n)
            if info is None:
                return None

            (self.num_tiles_x, self.num_tiles_y, self.ppd_x, self.ppd_y) = info

            # cache partial path to level dir
            self.tile_level_dir = os.path.join(self.tile_dir, '%02d' % n)

            return (self.tile_size_x*self.num_tiles_x,
                    self.tile_size_y*self.num_tiles_y,
                    self.ppd_x, self.ppd_y)

        def get_info(self, level):
            """Get tile info for a particular level.

            level  the level to get tile info for

            Returns (num_tiles_x, num_tiles_y, ppd_x, ppd_y).
            """

            # see if we can open the tile info file.
            info_file = os.path.join(self.tile_dir, '%02d' % level,
                                     self.TileInfoFilename)
            try:
                fd = open(info_file, 'rb')
            except IOError:
                return None

            # OK, looks like we actually do have this level!
            info = pickle.load(fd)
            fd.close()

            return info

        def get_tile(self, x, y):
            """Get bitmap for tile at tile coords (x, y).

            x    X coord of tile required tile (tile coordinates)
            y    Y coord of tile required tile (tile coordinates)

            Returns bitmap object containing the tile image.

            Tile coordinates are measured from map top-left.

            If tile is in cache, read from there, else read from file & put
            into cache.
            """

            try:
                # if tile in cache, return it from there
                return self.tile_cache[(x,y)]
            except KeyError:
                # else not in cache: get image, cache and return it
                # exceptions are normally slow,
                # but we are reading a file if we get exception, so ...
                img_name = os.path.join(self.tile_level_dir,
                                        'tile_%d_%d.png' % (x, y))

# Optimization
# removed since we *know* tiles are there, we generated them!
# don't need to do filesystem operation.
# maybe put back if tiles come from internet?
#                if not os.path.exists(img_name):
#                    # if tile not there, use 'missing tile' file
#                    img_name = os.path.join(self.tile_dir, MissingTileFilename)

                img = wx.Image(img_name, wx.BITMAP_TYPE_ANY)
                pic = img.ConvertToBitmap()
                self.tile_cache[(x,y)] = pic
                return pic

################################################################################

    ######
    # An internal class for layers
    ######

    class Layer(object):
        """A Layer object.

        Contains everything required to draw:
            . map-relative points
            . view-relative points
            . map-relative polygons
            . view-relative polygons
            . map-relative images
            . view-relative images
        """

        def __init__(self, id=0, painter=None, data=None, map_relative=True,
                     colour='#000000', size=3, visible=False, filled=False,
                     name="<no name given>", attributes=None):
            """Initialise the Layer object.

            data        the layer data
            painter     render function
            colour      colour of all points
            size        size (radius/width)of drawn objects (in pixels)
            visible     layer visibility
            filled      if True, fill polygons
            name        the name of the layer (for debug)
            attributes  a dictionary of layer-specific attributes
            """

            self.painter = painter
            self.data = data
            self.map_relative = map_relative
            self.colour = colour
            self.size = size
            self.visible = visible
            self.filled = filled
            self.delta = None           # minimum distance for selection
            self.name = name
            self.attributes = attributes
            self.id = id

            # callbacks for selection
            self.callback_point_select = None
            self.right_callback_point_select = None
            self.callback_box_select = None

        def __str__(self):
            return ('<pyslip Layer: id=%d, name=%s, map_relative=%s, '
                    'visible=%s, size=%s, colour=%s'
                    % (self.id, self.name, str(self.map_relative),
                       str(self.visible), str(self.size), str(self.colour)))

################################################################################

    # exec dictionary to convert placement strings to 'ix' and 'iy' values
    # given dc_width, dc_height, bmap_width and bmap_height
    image_place = {'c':  ('ix=dc_width/2-bmap_width/2+x;'
                          'iy=dc_height/2-bmap_width/2+y'),
                   'ne': ('ix=dc_width-bmap_width-x;'
                          'iy=y'),
                   'se': ('ix=dc_width-bmap_width-x;'
                          'iy=dc_height-bmap_height-y'),
                   'sw': ('ix=x;'
                          'iy=dc_height-bmap_height-y'),
                   'nw': ('ix=x;'
                          'iy=y'),
                   'cn': ('ix=dc_width/2-bmap_width/2+x;'
                          'iy=y'),
                   'ce': ('ix=dc_width-bmap_width-x;'
                          'iy=dc_height/2-bmap_height/2-y'),
                   'cs': ('ix=dc_width/2-bmap_width/2+x;'
                          'iy=dc_height-bmap_height-y'),
                   'cw': ('ix=x;'
                          'iy=dc_height/2-bmap_height/2-y')
                  }

    # panel background colour
    BackgroundColour = wx.WHITE


    def __init__(self, parent, tile_dir=None, start_level=None,
                 min_level=None, max_level=None, **kwargs):
        """Initialise a pySlip instance.

        parent       reference to parent object
        tile_dir     the root tile directory
        start_level  initial tile level to start at
        min_level    the minimum tile level to use
        max_level    the maximum tile level to use
        **kwargs     keyword args for Panel
        """

        # create and initialise the base panel
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY, **kwargs)
        self.SetBackgroundColour(pySlip.BackgroundColour)

        # get tile info
        self.tiles = pySlip.Tiles(tile_dir)
        self.max_level = max_level
        if max_level is None:
            self.max_level = self.tiles.max_level
        self.min_level = min_level
        if min_level is None:
            self.min_level = self.tiles.min_level
        self.level = start_level
        if start_level is None:
            self.level = self.min_level

        self.tile_size_x = self.tiles.tile_size_x
        self.tile_size_y = self.tiles.tile_size_y

        # set some internal state
        self.view_width = None          # view size in pixels
        self.view_height = None         # set on onResize()

        self.ppd_x = 0                  # pixel_per_degree for current tileset
        self.ppd_y = 0

        self.view_offset_x = 0          # pixel offset at left & top of view
        self.view_offset_y = 0

        self.view_llon = self.view_rlon = None  # view limits
        self.view_tlat = self.view_blat = None

        self.was_dragging = False               # True if dragging map
        self.move_dx = 0                        # drag delta values
        self.move_dy = 0
        self.last_drag_x = None                 # previous drag position
        self.last_drag_y = None

        self.ignore_next_up = False             # flag to ignore next UP event

        self.is_box_select = False              # True if box selection
        self.sbox_1_x = self.sbox_1_y = None    # box size

        # layer stuff
        self.next_layer_id = 1      # source of unique layer IDs
        self.layer_z_order = []     # layer Z order, contains layer IDs
        self.layer_mapping = {}     # maps layer ID to (...layer data...)

        # callback to report mouse position in view
        self.mouse_position_callback = None

        # callback on right mouse click (right button up event)
        self.rightclick_callback = None

        # callback on level change
        self.change_level_callback = None

        # bind events
        self.Bind(wx.EVT_SIZE, self.onResize)       # widget events
        self.Bind(wx.EVT_PAINT, self.onPaint)

        self.Bind(wx.EVT_MOTION, self.onMove)       # mouse events
        self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.onLeftDClick)
        self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.onMiddleDown)
        self.Bind(wx.EVT_MIDDLE_UP, self.onMiddleUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheel)

        # OK, use the tile level the user wants
        self.use_level(self.level)

        # force a resize, which sets up the rest of the state
        self.onResize()

    ######
    # Handle various callback-related things
    ######

    def setMousePositionCallback(self, callback):
        """Set callback function on mouse move.

        callback  the function to call on mouse move, pass
                  current mouse position as (lon, lat) (floats).
        """

        self.mouse_position_callback = callback

    def handleMousePositionCallback(self, xy):
        """Handle a mouse position callback."""

        if self.mouse_position_callback:
            (x, y) = xy
            posn = self.convertView2Geo(x, y)
            self.mouse_position_callback(posn)

    def setLevelChangeCallback(self, callback):
        """Set callback routine on level change.

        callback  function to call on level change
        """

        self.change_level_callback = callback

    def handleLevelChangeCallback(self, level):
        """Handle a level change callback."""

        if self.change_level_callback:
            self.change_level_callback(level)

    def setLayerPointSelectCallback(self, id, delta, callback):
        """Register a layer callback for point selection.

        id       the layer id
        delta    maximum distance allowed for selection
        callback the function to call on possible point selection

        The callback function is called on left mouse up:
            callback(id, posn)
        where id    is the ID of the layer containing the point
                    (None if previously selected point is deselected)
              posn  is the geo coordinates of the selection click (lon, lat)
                    (*not* the coordinates of the point to be selected!)
        """

        l = self.layer_mapping[id]
        l.callback_point_select = callback
        l.delta = delta

    def setLayerPointRightSelectCallback(self, id, delta, callback):
        """Register a layer callback for point right-selection.

        id       the layer id
        delta    maximum distance allowed for selection
        callback the function to call on possible point selection

        The callback function is called on right mouse up:
            callback(id, posn)
        where id    is the ID of the layer containing the point
                    (None if previously selected point is deselected)
              posn  is the geo coordinates of the selection click (lon, lat)
                    (*not* the coordinates of the point to be selected!)
        """

        l = self.layer_mapping[id]
        l.right_callback_point_select = callback
        l.delta = delta

    def setBoxSelectCallback(self, id, callback):
        """Register a layer callback for box selection.

        id       the layer id
        callback the function to call on possible box selection

        The callback function is called on left mouse up:
            callback(id, points)
        where id      is the ID of the layer that is interested
              points  is a list of point tuples (lon, lat)
        The function returns (points, colour, radius) if point is to be
        selected, where points is a list of points to select (may be None),
        colour is colour of selected points and radius is their size.
        """

        self.layer_mapping[id].callback_box_select = callback

    ######
    # Play with layers Z order
    ######

    def pushLayerToBack(self, id):
        """Make layer specified be drawn at back of Z order.

        id   ID of the layer to push back
        """

        #log.debug('pushLayerToBack: pushing layer %s to the back' % str(id))

        self.layer_z_order.remove(id)
        self.layer_z_order.insert(0, id)

    def popLayerToFront(self, id):
        """Make layer specified be drawn at front of Z order.

        id   ID of the layer to pop to front
        """

        #log.debug('popLayerToFront: popping layer %s to the front' % str(id))

        self.layer_z_order.remove(id)
        self.layer_z_order.append(id)

    def placeLayerAfterLayer(self, id, top_id):
        """Place a layer so it will be drawn underneath a particular layer.

        id      ID of layer to place underneath 'top_id'
        top_id  ID of layer to be drawn *after* 'id'
        """

        self.layer_z_order.remove(id)
        i = self.layer_z_order.index(top_id)
        self.layer_z_order.insert(i, id)

    ######
    # Layers and points
    ######

    def addPointLayer(self, point_data, map_relative=True,
                      colour='#ff0000', size=3, name='<point_layer>'):
        """Add a layer of points to the map, allow different colours.

        point_data    list of (lon,lat,colour[,extra]) data
        map_relative  points drawn relative to map if True, else view relative
        colour        colour of all points if colour not in 'point_data'
        size          radius of points in pixels
        """

        id = self.addLayer(self.drawPointsLayer, point_data, map_relative,
                           colour, size, name=name)
        #log.debug('addPointLayer: new layer, id=%d' % id)
        return id


    def addMonoPointLayer(self, point_data, map_relative=True,
                          colour='#ff0000', size=3, name='<mono_point_layer>'):
        """Add a layer of points to the map, all same colour.

        point_data    list of (lon,lat[,extra]) data
        map_relative  points drawn relative to map if True, else view relative
        colour        colour of all points (unselected)
        size          radius of points in pixels
        name          name of this layer
        """

        id = self.addLayer(self.drawMonoPointsLayer, point_data, map_relative,
                           colour, size, name=name)
        #log.debug('addMonoPointLayer: new layer, id=%d' % id)
        return id

    def addMonoPolygonLayer(self, poly_data, map_relative=True,
                            colour='#ff0000', size=1, closed=False,
                            filled=False, name='<mono_polygon_layer>'):
        """Add a layer of monochrome polygon data to the map.

        poly_data     list of sequence of (lon,lat) coordinates
        map_relative  points drawn relative to map if True, else view relative
        colour        colour of all lines (unselected)
        size          width of polygons in pixels
        closed        True if polygon is to be closed
        filled        if True, fills polygon with given colour
        name          name of this layer
        """

        # copy data as we may change it
        data = copy.copy(poly_data)
        if closed or filled:
            data.append(data[0])

        id = self.addLayer(self.drawMonoPolygonLayer, data, map_relative,
                           colour, size, filled=filled, name=name)
        #log.debug('addMonoPolygonLayer: new layer, id=%d' % id)
        return id

    def addImageLayer(self, image_data, map_relative=True,
                      name='<image_layer>'):
        """Add a layer of images to the map.

        image_data    list of (lon,lat,filename) coordinates (map_relative)
                      or list of (x,y,filename,place) (view relative) where
                      x & y are margins in pixels
        map_relative  points drawn relative to map if True, else view relative
        name          name of this layer
        """

        # load all files, convert to bitmaps
        i_data = []
        if map_relative:
            for (x, y, fname) in image_data:
                img = wx.Image(fname, wx.BITMAP_TYPE_ANY)
                bmap = img.ConvertToBitmap()
                i_data.append((x, y, bmap))
        else:
            for (x, y, fname, place) in image_data:
                img = wx.Image(fname, wx.BITMAP_TYPE_ANY)
                bmap = img.ConvertToBitmap()
                i_data.append((x, y, bmap, place))

        id = self.addLayer(self.drawImageLayer, i_data, map_relative,
                           name=name)
        #log.debug('addImageLayer: new layer, id=%d' % id)
        return id

    def addTextLayer(self, data, map_relative, name='<text_layer>',
                     attributes=None):
        """Add a text layer to the map.

        data          list of sequence of (lon,lat, text, [dict]) coordinates
        map_relative  points drawn relative to map if True, else view relative
        name          name of this layer
        attributes    a dictionary of changeable text attributes
                      (placement, font, fontsize, colour, etc)
        """

        id = self.addLayer(self.drawTextLayer, data, map_relative, colour=None,
                           size=None, name=name, attributes=attributes)
        #log.debug('addTextLayer: new layer, id=%d' % id)
        return id


    def addLayer(self, render, data, map_rel, colour=None, size=None,
                 visible=True, filled=False, name='<unnamed_layer>',
                 attributes=None):
        """Add a generic layer to the system.

        id          the unique layer ID
        render      the function used to render the layer
        data        actual layer data (depends on layer type)
        map_rel     True if points are map_relative, else view_relative
        colour      display colour of the points (unselected)
        size        display radius of points (unselected)
        visible     True if layer is to be draw, else False
        filled      if True, fill polygons
        name        name for this layer
        attributes  a dictionary of type-specific attributes
        """

        # get layer ID
        id = self.next_layer_id
        self.next_layer_id += 1

        # copy data so user changes don't update display!
        my_data = copy.copy(data)

        l = self.Layer(id=id, painter=render, data=my_data,
                       map_relative=map_rel, colour=colour, size=size,
                       visible=visible, filled=filled, name=name,
                       attributes=attributes)

        self.layer_mapping[id] = l
        self.layer_z_order.append(id)

        # force display of new layer
        self.Refresh()

        return id

    def showLayer(self, id):
        """Show a layer.

        id   the layer id
        """

        #log.debug('showLayer: showing layer %s' % str(id))

        self.layer_mapping[id].visible = True

        self.Refresh()

    def hideLayer(self, id):
        """Hide a layer.

        id   the layer id
        """

        #log.debug('hideLayer: hiding layer %s' % str(id))

        self.layer_mapping[id].visible = False
        self.Refresh()

    def deleteLayer(self, id):
        """Delete a layer.

        id   the layer id
        """

        # just in case we got None
        if id is None:
            return

        # see if what we are about to remove might be visible
        layer = self.layer_mapping[id]
        visible = layer.visible

        del layer
        self.layer_z_order.remove(id)

        # if layer was visible, refresh display
        if visible:
            self.Refresh()

    ######
    # Layer drawing routines
    ######

    def drawPointsLayer(self, dc, points, map_rel, colour, size, filled,
                        attributes):
        """Draw an individually coloured points Layer on the view.

        dc          the device context to draw on
        points      a sequence of point tuples: (x, y, colour, extra)
        map_rel     points relative to map if True, else relative to view
        colour      UNUSED
        size        radius of each point
        filled      UNUSED
        attributes  layer attributes dictionary
        """

        if points is None:
            return

        if map_rel:
            for p in points:
                lon = p[0]
                lat = p[1]
                colour = p[2]

                dc.SetPen(wx.Pen(colour))
                dc.SetBrush(wx.Brush(colour))

                posn = self.convertGeo2ViewMasked(lon, lat)
                if posn:
                    (x, y) = posn
                    dc.DrawCircle(x, y, size)
        else:
            for p in points:
                lon = p[0]
                lat = p[1]
                colour = p[2]

                dc.SetPen(wx.Pen(colour))
                dc.SetBrush(wx.Brush(colour))

                dc.DrawCircle(x, y, size)

    def drawMonoPointsLayer(self, dc, points, map_rel, colour, size, filled,
                            attributes):
        """Draw a monochrome points Layer on the view.

        dc          the device context to draw on
        points      a sequence of point tuples: (x, y, extra)
        map_rel     points relative to map if True, else relative to view
        colour      colour to draw each point in
        size        radius of each point
        filled      UNUSED
        attributes  layer attributes dictionary
        """

        if points is None:
            return

        dc.SetPen(wx.Pen(colour))
        dc.SetBrush(wx.Brush(colour))

        if map_rel:
            for p in points:
                lon = p[0]
                lat = p[1]
                posn = self.convertGeo2ViewMasked(lon, lat)
                if posn:
                    (x, y) = posn
                    dc.DrawCircle(x, y, size)
        else:
            for p in points:
                x = p[0]
                y = p[1]
                dc.DrawCircle(x, y, size)

    def drawMonoPolygonLayer(self, dc, polys, map_rel, colour, size, filled,
                             attributes):
        """Draw a monochrome polygon Layer on the view.

        dc          the device context to draw on
        polys       a sequence of polygon tuple sequences
                    [((x, y), (x',y'), ...), ...]
        map_rel     points relative to map if True, else relative to view
        colour      colour to draw a point in
        size        width of polygon line
        filled      True if polygon is filled
        attributes  layer attributes dictionary
        """

        if polys is None:
            return

        dc.SetPen(wx.Pen(colour, width=size))
        if filled:
            dc.SetBrush(wx.Brush(colour))
        else:
            dc.SetBrush(wx.TRANSPARENT_BRUSH)

        if map_rel:
            for p in polys:
                p_lonlat = []
                for (lon, lat) in p:
                    posn = self.convertGeo2View(lon, lat)
                    p_lonlat.append(posn)
                dc.DrawPolygon(p_lonlat)
        else:
            for p in polys:
                pp = [wx.Point(point[0], point[1]) for point in p]
                dc.DrawPolygon(pp)

    def drawImageLayer(self, dc, images, map_rel, colour, size, filled,
                       attributes):
        """Draw an image Layer on the view.

        dc          the device context to draw on
        images      a sequence of image tuple sequences [(x, y, bitmap), ...]
        map_rel     points relative to map if True, else relative to view
        colour      UNUSED
        size        UNUSED
        filled      UNUSED
        attributes  layer attributes dictionary
        """

        if images is None:
            return

        if map_rel:
            for i in images:
                try:
                    (lon, lat, bmap) = i
                except ValueError:
                    raise RuntimeError('Map-relative image data must be: '
                                       '[(lon, lat, filename), ...]')
                (x, y) = self.convertGeo2View(lon, lat)
                dc.DrawBitmap(bmap, x, y, False)
        else:
            for i in images:
                try:
                    (x, y, bmap, place) = i
                except ValueError:
                    raise RuntimeError('View-relative image data must be: '
                                       '[(x, y, filename, placement), ...]')
                (bmap_width, bmap_height) = bmap.GetSize()
                (dc_width, dc_height) = dc.GetSize()
                exec(self.image_place[place.lower()])    # defines ix & iy
                dc.DrawBitmap(bmap, ix, iy, False)

    # placement dictionary - assumes x, y and offset exist
    # perturbs x and y to coorect values for the placement
    text_placement = {'lt': 'x=x+offset;y=y+offset',
                      'tl': 'x=x+offset;y=y+offset',
                      'ct': 'x=x-w/2;y=y+offset',
                      'tc': 'x=x-w/2;y=y+offset',
                      'rt': 'x=x-w-offset;y=y+offset',
                      'tr': 'x=x-w-offset;y=y+offset',
                      'lm': 'x=x+offset;y=y-h/2',
                      'ml': 'x=x+offset;y=y-h/2',
                      'cm': 'x=x-w/2;y=y-h/2',
                      'mc': 'x=x-w/2;y=y-h/2',
                      'rm': 'x=x-w-offset;y=y-h/2',
                      'mr': 'x=x-w-offset;y=y-h/2',
                      'lb': 'x=x+offset;y=y-h-offset',
                      'bl': 'x=x+offset;y=y-h-offset',
                      'cb': 'x=x-w/2;y=y-h-offset',
                      'bc': 'x=x-w/2;y=y-h-offset',
                      'rb': 'x=x-w-offset;y=y-h-offset',
                      'br': 'x=x-w-offset;y=y-h-offset'}

    text_offset = { }

    def drawTextLayer(self, dc, text, map_rel, colour, size, filled, attributes):
        """Draw an image Layer on the view.

        dc          the device context to draw on
        text        a sequence of text tuple sequences [(x, y, text, [dict]), ...]
        map_rel     points relative to map if True, else relative to view
        colour      UNUSED
        size        UNUSED
        filled      UNUSED
        attributes  layer attributes dictionary

        Attributes values that are recognised here:
            placement  string indicating placement of text relative to point
            offset     number of pixels offset from the point
            angle      angle to rotate the string
        """

        if text is None:
            return

        # handle attributes here
        placement = attributes.get('placement', 'cm')
        offset = attributes.get('offset', 4)
        angle =  attributes.get('angle', 0)
        colour = attributes.get('colour', wx.BLACK)

        dc.SetPen(wx.Pen(colour))
        dc.SetBrush(wx.Brush(colour))

        # draw text on map/view
        if map_rel:
            for i in text:
                try:
                    (lon, lat, t) = i
                    d = None
                except ValueError:
                    raise RuntimeError('Map-relative text data must be: '
                                       '[(lon, lat, text), ...]')
                (x, y) = self.convertGeo2View(lon, lat)
                (w, h, _, _) = dc.GetFullTextExtent(t)

                dc.DrawCircle(x, y, 2)
                exec self.text_placement[placement.lower()]
                dc.DrawText(t, x, y)
        else:
            for i in text:
                try:
                    (x, y, t) = i
                    d = None
                except ValueError:
                    raise RuntimeError('View-relative text data must be: '
                                       '[(x, y, text), ...]')
                dc.DrawCircle(x, y, 2)
                dc.DrawText(t, x, y)

    def drawSelectedPoint(self, dc, lon, lat, colour, size):
        """Draw a selected point.

        dc      the device context to draw on
        lon+lat the point to draw on (geo coords)
        colour  point draw colour
        size  point radius
        """

        dc.SetPen(wx.Pen(colour))
        dc.SetBrush(wx.Brush(colour))

        posn = self.convertGeo2ViewMasked(lon, lat)
        if posn:
            # 'posn' is within the view
            (x, y) = posn
            dc.DrawCircle(x, y, size)

    ######
    # Positioning methods
    ######

    def gotoPosition(self, posn):
        """Set view to centre on a position.

        posn  a tuple (lon,lat) to centre view on

        If any level switching is required, it is assumed already done.
        """

        (lon, lat) = posn

        x = (lon - self.map_llon) * self.ppd_x
        y = (self.map_tlat - lat) * self.ppd_y
        self.view_offset_x = x - self.view_width/2
        self.view_offset_y = y - self.view_height/2

        self.drawTilesLayers()
        self.onResize(None)


    def gotoLevelAndPosition(self, level, posn):
        """Goto a map level and set view to centre on a position.

        level  the map level to use
        posn   a tuple (lon,lat) to centre view on

        Does nothing if we can't use desired level.
        """

        if self.use_level(level):
            self.gotoPosition(posn)

    def zoomToArea(self, posn, size):
        """Set view to level and position to view an area.

        posn  a tuple (lon,lat) to centre view on
        size  a tuple (width,height) of area in degrees

        Centre an area and zoom to view such that the area will fill
        approximately 50% of width or height, whichever is greater.

        Use the ppd_x and ppd_y values in level 'tiles.info' files.
        """

        # unpack area width.height (degrees)
        (awidth, aheight) = size

        # step through levels (smallest first) and check view size (degrees)
        for l in self.tiles.levels:
            level = l
            (_, _, ppd_x, ppd_y) = self.tiles.get_info(l)
            view_deg_width = self.view_width / ppd_x
            view_deg_height = self.view_height / ppd_y

            # if area >= 50% of view, bomb out
            if awidth >= view_deg_width/2 or aheight >= view_deg_height/2:
                break

        self.gotoLevelAndPosition(level, posn)

    ######
    # Convert between geo and view coordinates
    ######

    def convertGeo2View(self, lon, lat):
        """Convert a geo (lon+lat) position to view pixel coords.

        lon   longitude of point
        lat   latitude of point

        Return screen pixels coordinates of the point (x,y).
        """

        x_pix = (lon - self.view_llon) * self.ppd_x
        y_pix = (self.view_tlat - lat) * self.ppd_y

        return (x_pix, y_pix)

    def convertGeo2ViewMasked(self, lon, lat):
        """Convert a geo (lon+lat) position to view pixel coords.

        lon   longitude of point
        lat   latitude of point

        Return screen pixels coordinates of the point (x,y) or None
        if point is off-view.
        """

        if (self.view_llon <= lon <= self.view_rlon and
                self.view_blat <= lat <= self.view_tlat):
            return self.convertGeo2View(lon, lat)

        return None

    def convertView2Geo(self, x, y):
        """Convert an x,y view position to geo lon+lat.

        x    view X coordinate (pixels)
        y    view Y coordinate (pixels)

        Return a tuple (lon, lat) - geo coordinates of the point.
        """

        # x_pix is from left map edge, y_pix from top map edge
        x_pix = x + self.view_offset_x
        y_pix = y + self.view_offset_y

        lon = self.map_llon + x_pix/self.ppd_x
        lat = self.map_tlat - y_pix/self.ppd_y

        return (lon, lat)

    def isPositionOnMap(self, posn):
        """Decide if position is within map extent.

        posn  tuple (lon, lat)
        """

        (x, y) = posn
        return (self.map_llon <= x <= self.map_rlon
                and self.map_blat <= y <= self.map_tlat)

    ######
    # GUI stuff
    ######

    def onMove(self, event):
        """Handle a mouse move (map drag or rectangle select).

        event  The mouse move event

        If SHIFT key is down, do rectangle select.
        Otherwise pan the map if we are dragging.
        """

        # get current mouse position
        (x, y) = event.GetPositionTuple()

        self.handleMousePositionCallback((x, y))

        if event.Dragging() and event.LeftIsDown():
            # are we doing box select?
            if self.is_box_select:
                # set select box point 2 at mouse position
                (self.sbox_w, self.sbox_h) = (x - self.sbox_1_x,
                                              y - self.sbox_1_y)
            elif not self.last_drag_x is None:
                # no, just a map drag
                self.was_dragging = True
                dx = self.last_drag_x - x
                dy = self.last_drag_y - y

                # move the map in the view
                self.view_offset_x += dx
                self.view_offset_y += dy

                # limit drag at edges of map
                if self.map_width > self.view_width:
                    # if map > view, don't allow edge to show background
                    if self.view_offset_x < 0:
                        self.view_offset_x = 0
                    elif self.view_offset_x > self.max_x_offset:
                        self.view_offset_x = self.max_x_offset
                else:
                    # else map < view, centre X
                    self.view_offset_x = (self.map_width - self.view_width)/2

                if self.map_height > self.view_height:
                    # if map > view, don't allow edge to show background
                    if self.view_offset_y < 0:
                        self.view_offset_y = 0
                    elif self.view_offset_y > self.max_y_offset:
                        self.view_offset_y = self.max_y_offset
                else:
                    # else map < view, centre Y
                    self.view_offset_y = (self.map_height - self.view_height)/2

                # adjust remembered X,Y
                self.last_drag_x = x
                self.last_drag_y = y

                self.recalc_view_lonlat_limits()

            # redraw client area
            self.drawTilesLayers()

    def onPaint(self, event):
        """Handle a system PAINT event.

        event   event that caused a repaint, may be None

        Tile the canvas.  Resize, zoom and drag code have set up state.
        Then draw layers.
        """

        dc = wx.PaintDC(self)
        self.drawTilesLayers(dc)

    def drawTilesLayers(self, dc=None, clear=False):
        """Do actual map tile and layers drawing.

        dc     device context to draw on
        clear  clear background if True
        """

        # if no given DC, get client DC
        if dc is None:
            dc = wx.ClientDC(self)

        # if map smaller than view, clear background as it will show
        if clear:
            dc.Clear()

        # figure out how to draw tiles
        if self.view_offset_x < 0:
            # centre in X
            start_x_tile = 0
            stop_x_tile = self.tiles.num_tiles_x
            x_pix = -self.view_offset_x
        else:
            x_offset = self.view_offset_x + self.move_dx
            start_x_tile = int(x_offset / self.tile_size_x)
            stop_x_tile = int((x_offset+self.view_width+self.tile_size_x-1)
                              / self.tile_size_x)
            x_pix = start_x_tile*self.tile_size_y - x_offset

        if self.view_offset_y < 0:
            # centre in Y
            start_y_tile = 0
            stop_y_tile = self.tiles.num_tiles_y
            y_pix_start = -self.view_offset_y
        else:
            y_offset = self.view_offset_y + self.move_dy
            start_y_tile = int(y_offset / self.tile_size_y)
            stop_y_tile = int((y_offset+self.view_height+self.tile_size_y-1)
                              / self.tile_size_y)
            y_pix_start = start_y_tile*self.tile_size_y - y_offset

        # start pasting tiles onto view
        for x in range(start_x_tile, stop_x_tile):
            y_pix = y_pix_start
            for y in range(start_y_tile, stop_y_tile):
                dc.DrawBitmap(self.tiles.get_tile(x, y), x_pix, y_pix, False)
                y_pix += self.tile_size_y
            x_pix += self.tile_size_x

        # draw layers
        for id in self.layer_z_order:
            l = self.layer_mapping[id]
            if l.visible:
                l.painter(dc, l.data, map_rel=l.map_relative,
                          colour=l.colour, size=l.size, filled=l.filled,
                          attributes=l.attributes)

        # draw selection rectangle, if any
        if self.sbox_1_x:
            penclr = wx.Colour(0, 0, 255, 255)
            dc.SetPen(wx.Pen(penclr, width=1))
            brushclr = wx.Colour(0, 0, 0, 0)
            dc.SetBrush(wx.Brush(brushclr, style=wx.TRANSPARENT))
            dc.DrawRectangle(self.sbox_1_x, self.sbox_1_y,
                             self.sbox_w, self.sbox_h)

    def onResize(self, event=None):
        """Handle a window resize.

        event  that caused the resize, may be None (not used)

        Handle all possible states of view and map:
           . new view entirely within map
           . map smaller than view (just centre map)

        Set up view state and then force a repaint.
        """

        # get new size of the view
        (self.view_width, self.view_height) = self.GetClientSizeTuple()

        # if map > view in X axis
        if self.map_width > self.view_width:
            self.max_x_offset = self.map_width - self.view_width
            # do nothing unless background is showing
            # if map left edge right of view edge
            if self.view_offset_x < 0:
                # move view to hide background at left
                self.view_offset_x = 0
            elif self.view_offset_x + self.view_width > self.map_width:
                # move view to hide background at right
                self.view_offset_x = self.map_width - self.view_width
        else:
            # else view >= map - centre map in X direction
            self.max_x_offset = self.map_width - self.view_width
            self.view_offset_x = self.max_x_offset / 2

        # if map > view in Y axis
        if self.map_height > self.view_height:
            self.max_y_offset = self.map_height - self.view_height
            # do nothing unless background is showing
            # if map top edge below view edge
            if self.view_offset_y < 0:
                # move view to hide background at top
                self.view_offset_y = 0
            elif self.view_offset_y + self.view_height > self.map_height:
                # move view to hide background at bottom
                self.view_offset_y = self.map_height - self.view_height
        else:
            # else view >= map - centre map in Y direction
            self.max_y_offset = self.map_height - self.view_height
            self.view_offset_y = self.max_y_offset / 2

        # set the left/right/top/bottom lon/lat extents
        self.recalc_view_lonlat_limits()

        # redraw tiles & layers
        self.drawTilesLayers(clear=True)

    def recalc_view_lonlat_limits(self):
        """Recalculate the view lon/lat extent values.

        Assumes only the .view_offset_? and .ppd_? values have been set.
        """

        self.view_llon = self.map_llon + self.view_offset_x / self.ppd_x
        self.view_rlon = self.view_llon + self.view_width / self.ppd_x

        self.view_tlat = self.map_tlat - self.view_offset_y / self.ppd_y
        self.view_blat = self.view_tlat - self.view_height / self.ppd_y


    def getNearestPointInLayer(self, data, delta, locn):
        """Determine if clicked location selects a point in layer data.

        data   list of point data (lon, lat)
        delta  squared maximum threshold for selecting
        locn   click location

        Return None (no selection) or (lon, lat) of selected point.

        The points in 'data' might or might not have added colour data.
        """

# TODO: speed this up - kdtree?

        (cx, cy) = locn
        res = None
        dist = None
        for p in data:
            x = p[0]
            y = p[1]
            d = (x-cx)*(x-cx) + (y-cy)*(y-cy)
            if dist:
                if d < dist:
                    dist = d
                    res = (x, y)
            else:
                dist = d
                res = (x, y)

        if dist <= delta:
            return res
        return None

    def onLeftDown(self, event):
        """Left mouse button down. Prepare for possible drag."""

        self.is_box_select = False      # assume not box selection

        click_posn = event.GetPositionTuple()

        if event.ShiftDown():
            self.is_box_select = True
            self.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))
            (self.sbox_w, self.sbox_h) = (0, 0)
            (self.sbox_1_x, self.sbox_1_y) = click_posn
        else:
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            (self.last_drag_x, self.last_drag_y) = click_posn
        event.Skip()

    def onLeftUp(self, event):
        """Left mouse button up.

        Complications arise when we iterate through layers and call a user
        callback function.  We must iterate through a *copy* of layers that
        exist when the user clicked.  We must also expect that layers will
        disappear and be created from the side effects of the callback.
        """

        self.last_drag_x = self.last_drag_y = None

        if self.ignore_next_up:
            self.ignore_next_up = False
            return

        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

        # we need a repaint to remove any selection box, but NOT YET!
        delayed_paint = self.sbox_1_x

        # if any layers interested, inform of possible select
        if not self.was_dragging:
            if self.is_box_select:
                self.is_box_select = False

                # box selection
                (lon_1, lat_1) = self.convertView2Geo(self.sbox_1_x,
                                                      self.sbox_1_y)
                (lon_2, lat_2) = self.convertView2Geo(self.sbox_1_x+self.sbox_w,
                                                      self.sbox_1_y+self.sbox_h)

                # check each layer for a box select callback
                copy_layers = copy.copy(self.layer_z_order)
                handled_layers = []
                for id in copy_layers:
                    # if layer still exists and not already handled
                    if id in self.layer_mapping and id not in handled_layers:
                        l = self.layer_mapping[id]
                        if l.visible and l.callback_box_select:
                            # get all points selected (if any)
                            points = self.getBoxSelectPoints(l.data,
                                                             (lon_1,lat_1),
                                                             (lon_2,lat_2))
                            if points:
                                # pass points to callback
                                handled_layers.append(id)
                                if l.callback_box_select(id, points):
                                    delayed_paint = True
            else:
                # possible point selection
                (cx, cy) = event.GetPositionTuple()
                clickpt = self.convertView2Geo(cx, cy)
                # check each layer for a point select callback
                copy_layers = copy.copy(self.layer_z_order)
                handled_layers = []
                for id in copy_layers:
                    # if layer still exists and not already handled
                    if id in self.layer_mapping and id not in handled_layers:
                        l = self.layer_mapping[id]
                        if l.visible and l.callback_point_select:
                            pt = self.getNearestPointInLayer(l.data,
                                                             l.delta, clickpt)
                            if pt:
                                handled_layers.append(id)
                                if l.callback_point_select(id, pt):
                                    delayed_paint = True

        # turn off drag
        self.was_dragging = False

        # turn off box selection mechanism
        self.is_box_select = False
        self.sbox_1_x = self.sbox_1_y = None

        # force PAINT event to remove selection box (if required)
        if delayed_paint:
            self.Refresh()

    def getBoxSelectPoints(self, data, p1, p2):
        """Get list of points inside box p1-p2.

        data   list of (x, y, r, g, b) of all points in layer
        p1     one corner point of selection box
        p2     opposite corner point of selection box

        We have to figure out wich corner is which.

        Return a list of (lon, lat) of points inside box.
        """

# TODO: speed this up?
        # get canonical box limits
        (p1x, p1y) = p1
        (p2x, p2y) = p2
        lx = min(p1x, p2x)      # left x coord
        rx = max(p1x, p2x)
        ty = max(p1y, p2y)      # top y coord
        by = min(p1y, p2y)

        # get a list of points inside the selection box
        result = []
        for (x, y, _, id) in data:
            if lx <= x <= rx and by <= y <= ty:
                result.append((x, y, id))

        return result

    def onLeftDClick(self, event):
        """Left mouse button double-click.

        Zoom in (if possible).
        Zoom out (if possible) if shift key is down.
        """

        # ignore next Left UP event
        self.ignore_next_up = True

        # should ignore double-click off the map, but within view
        # a possible workaround is to limit minimum view level

        # get view coords of mouse double click, want same centre afterwards
        (x, y) = event.GetPositionTuple()

        if event.ShiftDown():
            # zoom out if shift key also down
            if self.use_level(self.level-1):
                self.zoomOut(x, y)
        else:
            # zoom in
            if self.use_level(self.level+1):
                self.zoomIn(x, y)

        self.handleMousePositionCallback((x, y))

    def onMiddleDown(self, event):
        """Middle mouse button down."""

        pass

    def onMiddleUp(self, event):
        """Middle mouse button up."""

        pass

    def onMouseWheel(self, event):
        """Mouse wheel event."""

        # get centre of view in map coords, want same centre afterwards
        x = self.view_width/2
        y = self.view_height/2

        # determine which way to zoom, & *can* we zoom?
        if event.GetWheelRotation() > 0:
            if self.use_level(self.level+1):
                self.zoomIn(x, y)
        else:
            if self.use_level(self.level-1):
                self.zoomOut(x, y)

        self.handleMousePositionCallback(event.GetPositionTuple())

    def onRightDown(self, event):
        """Right mouse button down."""

        pass

    def onRightUp(self, event):
        """Right mouse button up.
       
        Check for callback on right click.
        """

        #self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

        # possible point selection
        (cx, cy) = event.GetPositionTuple()
        clickpt = self.convertView2Geo(cx, cy)

        # check each layer for a point right select callback
        copy_layers = copy.copy(self.layer_z_order)
        handled_layers = []
        for id in copy_layers:
            # if layer still exists and not already handled
            if id in self.layer_mapping and id not in handled_layers:
                l = self.layer_mapping[id]
                if l.visible and l.right_callback_point_select:
                    pt = self.getNearestPointInLayer(l.data, l.delta, clickpt)
                    if pt:
                        handled_layers.append(id)
                        if l.right_callback_point_select(id, pt):
                            delayed_paint = True

    def use_level(self, level):
        """Use a new tile level.

        level  the new tile level to use.

        Returns True if all went well.
        Maintain centre of map, if possible.
        """

        if self.min_level <= level <= self.max_level:
            map_extent = self.tiles.use_level(level)
            if map_extent:
                self.level = level
                (self.map_width, self.map_height,
                     self.ppd_x, self.ppd_y) = map_extent
                (self.map_llon, self.map_rlon,
                     self.map_blat, self.map_tlat) = self.tiles.extent

                # do level change callback
                self.handleLevelChangeCallback(level)

                return True

        return False

    def getMapCoordsFromView(self, posn):
        """Convert view pixel coordinates to map coordinates.

        posn   is a tuple (x, y) of view pixel coordinates

        Returns (x, y) map pixel coordinates.
        """

        # unpack the position
        (view_x, view_y) = posn

        # calculate map coords
        map_x = view_x + self.view_offset_x
        map_y = view_y + self.view_offset_y

        return (map_x, map_y)

    ######
    # The next two routines could be folded into one as they are the same.
    # However, if we ever implement a 'staged' zoom, we need both routines.
    ######

    def zoomIn(self, x, y):
        """Zoom map in to the next level.

        x, y  are pixel coords (view, not map) of new centre after zoom

        The tile stuff has already been set to the correct level.
        """

        # set view state
        (map_x, map_y) = self.getMapCoordsFromView((x,y))
        self.view_offset_x = map_x*2 - self.view_width/2
        self.view_offset_y = map_y*2 - self.view_height/2

        self.onResize(None)

    def zoomOut(self, x, y):
        """Zoom map out to the previous level.

        x, y  are pixel coords (view, not map) of new centre after zoom

        The tile stuff has already been set to the correct level.
        """

        # set view state
        (map_x, map_y) = self.getMapCoordsFromView((x,y))
        self.view_offset_x = map_x/2 - self.view_width/2
        self.view_offset_y = map_y/2 - self.view_height/2

        self.onResize(None)

######
# Miscellaneous.
######

    def logLayerInfo(self, msg=None):
        """Log details of current layers."""

        if msg:
            log(msg)

        log.debug('Layers:')
        for id in self.layer_z_order:
            layer = self.layer_mapping[id]
            log.debug('  %s' % str(layer))

    def log_state(self):
        """Debug routine - log view state variables."""

        log('-' * 50)
        log('.level=%d' % self.level)
        log('.view_llon=%.3f, .view_rlon=%.3f'
            % (self.view_llon, self.view_rlon))
        log('.view_tlat=%.3f, .view_blat=%.3f'
            % (self.view_tlat, self.view_blat))
        log('.ppd_x=%.2f, .ppd_y=%.2f' % (self.ppd_x, self.ppd_y))
        log('.view_offset_x=%d, .view_offset_y=%d'
            % (self.view_offset_x, self.view_offset_y))
        log('.view_width=%d, .view_height=%d'
            % (self.view_width, self.view_height))
        log('-' * 50)
        log('')

    def log_stack(self, msg):
        """Dump traceback-style info to the log."""

        log(('%s\n' % msg) + ''.join(traceback.format_list(traceback.extract_stack())))


################################################################################
# 'Smoke test' harness.
################################################################################

if __name__ == '__main__':
    import sys
    
    class TestFrame(wx.Frame):

        def __init__(self, *args, **kwargs):
            if sys.platform == 'win32':
                tdir = r'C:\Tsu-dat\tiles.PUBLISH'
            else:
                tdir = '/mnt/tsu-dat/Tsu-DAT_Data/tiles.PUBLISH'

            wx.Frame.__init__(self, *args, **kwargs)
            self.pyslip = pySlip(self, tile_dir=tdir)
            self.pyslip.Show()

    app = wx.App()
    frame = TestFrame(None, -1, title='pySlip test', size=(1024,768))
    frame.Show()
    app.MainLoop()
