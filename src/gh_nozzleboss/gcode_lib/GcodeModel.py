from gh_nozzleboss.helper_lib import segments_to_meshdata, obj_from_pydata
from gh_nozzleboss.gcode_lib.Layer import Layer
from gh_nozzleboss.gcode_lib.Segment import Segment
import math
import numpy as np


from .utils import bevel_path
import bpy, bmesh


class GcodeModel:

    def __init__(self, parser):
        # save parser for messages
        self.parser = parser
        # latest coordinates & extrusion relative to offset, feedrate
        self.relative = {
            "X": 0.0,
            "Y": 0.0,
            "Z": 0.0,
            "F": 0.0,
            "E": 0.0}
        # offsets for relative coordinates and position reset (G92)
        self.offset = {
            "X": 0.0,
            "Y": 0.0,
            "Z": 0.0,
            "E": 0.0}
        # if true, args for move (G1) are given relatively (default: absolute)
        self.isRelative = False
        self.color = [0, 0, 0, 0, 0, 0, 0, 0]  # RGBCMYKW
        self.toolnumber = 0

        # the segments
        self.segments = []
        self.layers = []
        # self.distance = None
        # self.extrudate = None
        # self.bbox = None

    def do_G1(self, args, type):
        # G0/G1: Rapid/Controlled move
        # clone previous coords
        coords = dict(self.relative)

        # update changed coords
        for axis in args.keys():
            # print(coords)
            if axis in coords:
                if self.isRelative:
                    coords[axis] += args[axis]
                else:
                    coords[axis] = args[axis]
            else:
                self.warn("Unknown axis '%s'" % axis)

        # build segment
        absolute = {
            "X": self.offset["X"] + coords["X"],
            "Y": self.offset["Y"] + coords["Y"],
            "Z": self.offset["Z"] + coords["Z"],
            "F": coords["F"]  # no feedrate offset

            # self.offset["E"] +    ofsett wont work for relative E
        }

        # if gcode line has no E = travel move
        # but still add E = 0 to segment (so coords dictionaries have same shape for subdividing linspace function)
        if "E" not in args:  # "E" in coords:
            absolute["E"] = 0
        else:
            absolute["E"] = args["E"]

        seg = Segment(
            type,
            absolute,
            self.color,
            self.toolnumber,
            # self.layerIdx,
            self.parser.lineNb,
            self.parser.line)

        if seg.coords['X'] != self.relative['X'] + self.offset["X"] or seg.coords['Y'] != self.relative['Y'] + \
                self.offset["Y"] or seg.coords['Z'] != self.relative['Z'] + self.offset["Z"]:
            self.addSegment(seg)

        # update model coords
        self.relative = coords

    def do_G92(self, args):
        # G92: Set Position
        # this changes the current coords, without moving, so do not generate a segment

        # no axes mentioned == all axes to 0
        if not len(args.keys()):
            args = {"X": 0.0, "Y": 0.0, "Z": 0.0}  # , "E":0.0
        # update specified axes
        for axis in args.keys():
            if axis in self.offset:
                # transfer value from relative to offset
                self.offset[axis] += self.relative[axis] - args[axis]
                self.relative[axis] = args[axis]
            else:
                self.warn("Unknown axis '%s'" % axis)

    def do_M163(self, args):
        # seg color [R,G,B,C,Y,M,K,W]
        col = list(
            self.color)  # list() creates new list, otherwise you just change reference and all segs have same color
        extr_idx = int(args['S'])  # e.g. M163 S0 P1
        weight = args['P']
        # change CMYKW
        col[extr_idx + 3] = weight  # +3 weil ersten 3 stellen RGB sind, need only CMYKW values for extrude
        self.color = col

        # take RGB values for seg from last comment (above first M163 statement)
        comment = eval(self.parser.comment)  # string comment to list
        # RGB = [GcodeParser.comment[1], GcodeParser.com
        RGB = comment[:3]
        self.color[:3] = RGB

    def setRelative(self, isRelative):
        self.isRelative = isRelative

    def addSegment(self, segment):
        self.segments.append(segment)

    def warn(self, msg):
        self.parser.warn(msg)

    def error(self, msg):
        self.parser.error(msg)

    def classifySegments(self):

        # start model at 0, act as prev_coords
        coords = {
            "X": 0.0,
            "Y": 0.0,
            "Z": 0.0,
            "F": 0.0,
            "E": 0.0}

        # first layer at Z=0
        currentLayerIdx = 0
        currentLayerZ = 0  # better to use self.first_layer_height
        layer = []  # add layer to model.layers

        for i, seg in enumerate(self.segments):
            # default style is travel (move, no extrusion)
            style = "travel"

            # some horizontal movement, and positive extruder movement: extrusion
            if (
                    ((seg.coords["X"] != coords["X"]) or (seg.coords["Y"] != coords["Y"]) or (
                            seg.coords["Z"] != coords["Z"])) and
                    (seg.coords["E"] > 0)):  # != coords["E"]
                style = "extrude"

            # segments to layer lists
            # look ahead and if next seg has E and differenz Z, add new layer for current segment
            if i == len(self.segments) - 1:
                layer.append(seg)
                currentLayerIdx += 1
                seg.style = style
                seg.layerIdx = currentLayerIdx
                self.layers.append(layer)  # add layer to list of Layers, used to later draw single layer objects
                break

            # positive extruder movement of next point in a different Z signals a layer change for this segment
            if self.segments[i].coords["Z"] != currentLayerZ and self.segments[i + 1].coords["E"] > 0:
                self.layers.append(
                    layer)  # layer abschließen, add layer to list of Layers, used to later draw single layer objects
                layer = []  # start new layer
                currentLayerZ = seg.coords["Z"]
                currentLayerIdx += 1
                # prev_seg.layerIdx = currentLayerIdx # lookback, previous point before texrsuion is part of new layer too, both create an edge

            # set style and layer in segment
            seg.style = style
            seg.layerIdx = currentLayerIdx
            layer.append(seg)
            coords = seg.coords

    def subdivide(self, subd_threshold):
        # divide edge if > subd_threshold

        subdivided_segs = []

        # start model at 0
        coords = {
            "X": 0.0,
            "Y": 0.0,
            "Z": 0.0,
            "F": 0.0,  # no interpolation
            "E": 0.0}

        for seg in self.segments:
            # calc XYZ distance
            d = (seg.coords["X"] - coords["X"]) ** 2
            d += (seg.coords["Y"] - coords["Y"]) ** 2
            d += (seg.coords["Z"] - coords["Z"]) ** 2
            seg.distance = math.sqrt(d)

            if seg.distance > subd_threshold:

                subdivs = math.ceil(
                    seg.distance / subd_threshold)  # ceil makes sure that linspace interval is at least 2
                # print("num of subd: ", math.ceil(subdivs))
                P1 = coords
                P2 = seg.coords

                # interpolated points
                interp_coords = np.linspace(list(P1.values()), list(P2.values()), num=subdivs, endpoint=True)

                for i in range(len(interp_coords)):  # inteprolated points array back to segment object

                    new_coords = {"X": interp_coords[i][0], "Y": interp_coords[i][1], "Z": interp_coords[i][2],
                                  "F": seg.coords[
                                      "F"]}  # E/subdivs is for relative extrusion, absolute extrusion need "E":interp_coords[i][4]
                    # print("interp_coords_new:", new_coords)
                    if seg.coords["E"] > 0:
                        new_coords["E"] = round(seg.coords["E"] / (subdivs - 1), 5)
                    else:
                        new_coords["E"] = 0

                    # make sure P1 hasn't been written before, compare with previous line
                    if new_coords['X'] != coords['X'] or new_coords['Y'] != coords['Y'] or new_coords['Z'] != coords[
                        'Z']:  # write segment only if movement changes, avoid double coordinates due to same start and endpoint of linspace

                        new_seg = Segment(seg.type, new_coords, seg.color, seg.toolnumber, seg.lineNb, seg.line)
                        new_seg.layerIdx = seg.layerIdx
                        new_seg.style = seg.style
                        subdivided_segs.append(new_seg)

            else:

                subdivided_segs.append(seg)

            coords = seg.coords  # P1 becomes P2

        self.segments = subdivided_segs

    # create blender curve and vertex_info in text file(coords, style, color...)
    def draw(self, split_layers=False):
        if split_layers:
            i = 0
            for layer in self.layers:
                verts, edges = segments_to_meshdata(layer)
                if len(verts) > 0:
                    obj_from_pydata(str(i), verts, edges, close=False, collection_name="Layers")
                    i += 1

        else:
            verts, edges = segments_to_meshdata(self.segments)
            obj = obj_from_pydata("Gcode", verts, edges, close=False, collection_name="Layers")

            # set active and bevel
            bpy.context.view_layer.objects.active = bpy.data.objects[obj.name]
            bevel_path(bpy.data.objects[obj.name])

            # create vcol maps and textblocks
            obj.data.vertex_colors.new(name='Speed')
            obj.data.vertex_colors.new(name='Flow')
            obj.data.vertex_colors.new(name='Tool')

            if not bpy.data.texts.get('T0'):
                bpy.data.texts.new('T0')
                bpy.data.texts['T0'].write('T0; switch to extruder T0 (any G-code macro can be passed here)\n')
            if not bpy.data.texts.get('T1'):
                bpy.data.texts.new('T1')
                bpy.data.texts['T1'].write('T1; switch to extruder T1 (any G-code macro can be passed here)\n')
            if not bpy.data.texts.get('Start'):
                bpy.data.texts.new('Start')
                bpy.data.texts['Start'].write(';nozzleboss\n')
                bpy.data.texts['Start'].write('G28 ;homing\n')
                bpy.data.texts['Start'].write('M104 S180 ;set hotend temp\n')
                bpy.data.texts['Start'].write('M190 S50 ;wait for bed temp\n')
                bpy.data.texts['Start'].write('M109 S200 ;wait for hotendtemp\n')
                bpy.data.texts['Start'].write('M83; relative extrusion mode (REQUIRED)\n')

            if not bpy.data.texts.get('End'):
                bpy.data.texts.new('End')
                bpy.data.texts['End'].write('G10 ;retract\n')
                bpy.data.texts['End'].write('M104 S0 ;deactivate hotend\n')
                bpy.data.texts['End'].write('M140 S0 ;deactivate bed\n')
                bpy.data.texts['End'].write('G28 ;homing\n')
                bpy.data.texts['End'].write('M84 ;turn off motors\n')



