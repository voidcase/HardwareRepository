"""
Contains the classes.

* Shapes
* Shape
* Point
* Line
* Grid

Shapes (replaces ShapeHistory) keeps track of objects dervied from Shape.
"""
import copy

from functools import reduce

import queue_model_objects_v1 as queue_model_objects

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareRepository import dispatcher


class Shapes(HardwareObject):
    """Keeps track of Shapes."""

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.shapes = {}

    def get_shapes(self):
        """
        Get all Shapes.

        :returns: All the shapes
        :rtype: Shape
        """
        return self.shapes.values()

    def get_points(self):
        """
        Get all Points currently handled.

        :returns: All points currently handled
        :rtype: Point
        """
        current_points = []

        for shape in self.get_shapes():
            if isinstance(shape, Point):
                current_points.append(shape)

        return current_points

    def get_lines(self):
        """
        Get all Lines currently handled.

        :returns: All lines currently handled
        :rtype: Line
        """
        lines = []

        for shape in self.get_shapes():
            if isinstance(shape, Line):
                lines.append(shape)

        return lines

    def get_grids(self):
        """
        Get all Grids currently handled.

        :returns: All Grids currently handled
        :rtype: Grid
        """
        grid = []

        for shape in self.get_shapes():
            if isinstance(shape, Grid):
                grid.append(shape)

        return grid

    def get_shape(self, sid):
        """
        Get Shape with id <sid>.

        :param str sid: id of Shape to retrieve
        :returns: Shape assocaited with sid
        :rtype: sid
        """
        return self.shapes.get(sid, None)

    def add_shape(self, shape):
        """
        Add the shape <shape> to the dictionary of handled shapes.

        :param shape: Shape to add.
        :type shape: Shape object.
        """
        self.shapes[shape.id] = shape

    def add_shape_from_mpos(self, mpos_list, screen_coord, t):
        """
        Adds a shape of type <t>, with motor positions from mpos_list and
        screen position screen_coord.

        :param list mpos_list: List of motor positions
        :param tuple screen_coord: Screen cordinate for shape
        :param str t: Type str for shape, P (Point), L (Line), G (Grid)
        :returns: Shape of type <t>
        :rtype: <t>
        """
        cls_dict = {"P": Point, "L": Line, "G": Grid, "2DP": TwoDPoint}
        _cls = cls_dict[t]
        shape = None

        if _cls:
            shape = _cls(mpos_list, screen_coord)
            self.add_shape(shape)

        return shape

    def add_shape_from_refs(self, refs, t):
        """
        Adds a shape of type <t>, taking motor positions and screen positions
        from reference points in refs.

        :param list refs: List of id's of the refrence Points
        :param str t: Type str for shape, P (Point), L (Line), G (Grid)
        :returns: Shape of type <t>
        :rtype: <t>
        """
        mpos = [self.get_shape(refid).mpos() for refid in refs]
        spos_list = [self.get_shape(refid).screen_coord for refid in refs]
        spos = reduce((lambda x, y: tuple(x) + tuple(y)), spos_list, ())
        shape = self.add_shape_from_mpos(mpos, spos, t)
        shape.refs = refs

        return shape

    def delete_shape(self, sid):
        """
        Removes the shape <shape> from the list of handled shapes.

        :param shape: The shape to remove
        :type shape: Shape object.
        """
        return self.shapes.pop(sid, None)

    def clear_all(self):
        """
        Clear the shapes, remove all contents.
        """
        self.shapes = {}
        Grid.SHAPE_COUNT = 0
        Line.SHAPE_COUNT = 0
        Point.SHAPE_COUNT =0

    def get_selected_shapes(self):
        """
        Get all selected shapes.

        :returns: List fot selected Shapes
        :rtype: List of Shapes
        """
        return [s for s in self.shapes.values() if s.is_selected()]

    def de_select_all(self):
        """De select all shapes."""

        for shape in self.shapes.values():
            shape.de_select()

    def select_shape(self, sid):
        """
        Select the shape <shape> (programmatically).

        :param shape: The shape to select.
        :type shape: Shape
        """
        shape = self.shapes.get(sid, None)

        if shape:
            shape.select()

    def de_select_shape(self, sid):
        """
        De-select the shape <shape> (programmatically).

        :param shape: The shape to de-select.
        :type shape: Shape
        """
        shape = self.shapes.get(sid, None)

        if shape:
            shape.de_select()

    def is_selected(self, sid):
        """
        Check if Shape with <sid> is selected.

        :returns: True if Shape with <sid> is selected False otherwise
        :rtype: Shape
        """
        shape = self.shapes.get(sid, None)
        return shape and shape.is_selected()

    # Signature maintained for backward compatability with ShapeHistory.
    # Not yet implemented
    def get_snapshot(self, *args, **kwargs):
        """
        Get a snapshot of the video stream and overlay the objects in
        qub_objects.

        :returns: The snapshot
        :rtype: str
        """
        pass

    def select_shape_with_cpos(self, cpos):
        return

    # For backwards compatability with old ShapeHisotry object
    # returns first of selected grids
    def get_grid(self):
        """
        Get the first of the selected grids, (the one that was selected first in
        a sequence of select operations)
        
        :returns: The first selected grid as a dictionary
        :rtype: dict
        """
        grid = None

        for shape in self.get_shapes():
            if isinstance(shape, Grid):
                grid = shape.as_dict()
                break;

        return grid


    def set_grid_data(self, sid, result_data):
        shape = self.get_shape(sid)

        if shape:
            shape.set_result(result_data)
        else:
            msg = "Cant set result for %s, no shape with id %s" % (sid, sid)
            raise AttributeError(msg)

    def get_grid_data(self, key):
        shape = self.get_shape(key)
        return shape.get_result()


class Shape(object):
    """
    Base class for shapes.
    """
    SHAPE_COUNT = 0

    def __init__(self, mpos_list=[], screen_coord=(-1, -1)):
        object.__init__(self)
        Shape.SHAPE_COUNT += 1
        self.t = "S"
        self.id = ""
        self.cp_list = []
        self.name = ""
        self.state = "SAVED"
        self.label = ""
        self.screen_coord = screen_coord
        self.selected = False
        self.refs = []

        self.add_cp_from_mp(mpos_list)

    def get_centred_positions(self):
        """
        :returns: The centred position(s) associated with the shape.
        :rtype: List of CentredPosition objects.
        """
        return self.cp_list

    def get_centred_position(self):
        return self.get_centred_positions()[0]

    def select(self):
        self.selected = True

    def de_select(self):
        self.selected = False

    def is_selected(self):
        return self.selected

    def update_position(self, transform):
        spos_list = [transform(cp.as_dict()) for cp in self.cp_list]
        spos_list = tuple([pos for l in spos_list for pos in l])
        self.screen_coord = spos_list

    def add_cp_from_mp(self, mpos_list):
        for mp in mpos_list:
            self.cp_list.append(queue_model_objects.CentredPosition(mp))

    def set_id(self, id_num):
        self.id = self.t + "%s" % id_num
        self.name = self.label + "-%s" % id_num

    def move_to_mpos(self, mpos_list, screen_coord=[]):
        self.cp_list = []
        self.add_cp_from_mp(mpos_list)

        if screen_coord:
            self.screen_coord = screen_coord

    def update_from_dict(self, shape_dict):
        # We dont allow id updates
        shape_dict.pop("id", None)

        for key, value in shape_dict.iteritems():
            if hasattr(self, key):
                setattr(self, key, value)

    def as_dict(self):
        cpos_list = []

        for cpos in self.cp_list:
            cpos_list.append(cpos.as_dict())

        d = copy.deepcopy(vars(self))

        # replace cpos_list with a list of motor positions
        d.pop("cp_list")
        d["motor_positions"] = str(cpos_list)

        return d


class Point(Shape):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Shape.__init__(self, mpos_list, screen_coord)
        Point.SHAPE_COUNT += 1
        self.t = "P"
        self.label = "Point"
        self.set_id(Point.SHAPE_COUNT)

    def mpos(self):
        return self.cp_list[0].as_dict()

    def set_id(self, id_num):
        Shape.set_id(self, id_num)
        self.cp_list[0].index = self.id

    def as_dict(self):
        d = Shape.as_dict(self)
        # replace cpos_list with the motor positions
        d["motor_positions"] = self.cp_list[0].as_dict()
        return d


class TwoDPoint(Point):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Point.__init__(self, mpos_list, screen_coord)
        self.t = "2DP"
        self.label = "2D-Point"
        self.set_id(Point.SHAPE_COUNT)


class Line(Shape):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Shape.__init__(self, mpos_list, screen_coord)
        Line.SHAPE_COUNT += 1
        self.t = "L"
        self.label = "Line"
        self.set_id(Line.SHAPE_COUNT)

    def get_centred_positions(self):
        return [self.start_cpos, self.end_cpos]

    def get_points_index(self):
        if all(self.cp_list):
            return (self.cp_list[0].get_index(), self.cp_list[1].get_index())


class Grid(Shape):
    SHAPE_COUNT = 0

    def __init__(self, mpos_list, screen_coord):
        Shape.__init__(self, mpos_list, screen_coord)
        Grid.SHAPE_COUNT += 1
        self.t = "G"
        self.set_id(Grid.SHAPE_COUNT)

        self.width = -1
        self.height = -1
        self.cell_count_fun = "zig-zag"
        self.cell_h_space = -1
        self.cell_height = -1
        self.cell_v_space = -1
        self.cell_width = -1
        self.label = "Grid"
        self.num_cols = -1
        self.num_rows = -1
        self.selected = False
        self.result = []
        self.pixels_per_mm = [1, 1]
        self.beam_pos = [1, 1]
        self.beam_width = 0
        self.beam_height = 0

        self.set_id(Grid.SHAPE_COUNT)
    
    def getRGBfromI(self, RGBint):
        blue =  RGBint & 255
        green = (RGBint >> 8) & 255
        red =   (RGBint >> 16) & 255
        return red, green, blue
    
    def get_centred_position(self):
        return self.cp_list[1]

    def get_grid_range(self):
        return (float(self.cell_width * (self.num_cols - 1)), \
                float(self.cell_height * (self.num_rows - 1)))

    def get_num_lines(self):
        if self.cell_count_fun == "zig-zag":
            return self.num_rows
        elif self.cell_count_fun == "inverse-zig-zag":
            return self.num_cols
        else:
            return self.num_rows

    def set_id(self, id_num):
        Shape.set_id(self, id_num)
        self.cp_list[0].index = self.id

    def set_result(self, result_data):
        self.result = result_data

    def set_cell_result(self, cell_number, value):
        r, g, b = self.getRGBfromI(value)
        cell_count = self.num_cols*self.num_rows

        if self.get_result() is None:
            res = {}
            for i in range(1, self.num_rows*self.num_cols + 1):
                res[i] = [i, [0, 0, 0, 0]]
            self.set_result(res)

        if self.cell_count_fun == "zig-zag":
            current_row = divmod(cell_number-1, self.num_cols)[0] + 1
            row_counts = range((current_row-1)*self.num_cols+1, current_row*self.num_cols+1) 

            if current_row % 2 == 0: 
                # inverse order in this row
                row_counts.reverse()
            current_col = row_counts.index(cell_number) + 1
            index = ((current_row-1)*self.num_cols+current_col)
            self.result[index] =  [index, [r, g, b, 0]]
        elif self.cell_count_fun == "top-down-zig-zag":
            pass
        elif self.cell_count_fun == "top-down":
            pass
        elif self.cell_count_fun == "inverse-zig-zag":
            current_col = self.num_cols - divmod(cell_number-1, self.num_rows)[0]
            col_counts = range((self.num_cols - current_col)*self.num_rows+1, cell_count - (current_col-1)*self.num_rows + 1)
            if self.num_cols % 2 == 0:
                if current_col % 2 == 0:
                    col_counts.reverse()
            else:
               if current_col % 2 != 0:
                    col_counts.reverse() 
            current_row = col_counts.index(cell_number) + 1
            index = (current_row-1)*self.num_cols +current_col
            self.result[index] =  [index, [r, g, b, 0]]
        else:
            self.result[cell_number] =  [cell_number, [r, g, b, 0]]

    def get_result(self):
        return self.result

    def as_dict(self):
        d = Shape.as_dict(self)
        # replace cpos_list with the motor positions
        d["motor_positions"] = self.cp_list[0].as_dict()

        # MXCuBE - 2 WF compatability
        d["x1"] = -float((self.beam_pos[0] - d["screen_coord"][0]) / self.pixels_per_mm[0])
        d["y1"] = -float((self.beam_pos[1] - d["screen_coord"][1]) / self.pixels_per_mm[1])
        d["steps_x"] = d["num_cols"]
        d["steps_y"] = d["num_rows"]
        d["dx_mm"] = d["width"] / self.pixels_per_mm[0]
        d["dy_mm"] = d["height"] / self.pixels_per_mm[1]
        d["beam_width"] = d["beam_width"]
        d["beam_height"] = d["beam_height"]
        d["angle"] = 0

        return d    
