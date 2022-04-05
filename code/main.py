

from ast import pattern
import io
import json
from optparse import Option
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from pprint import pprint 

table_offset = 3

file_tag = """
<?xml version="1.0" encoding="UTF-8" standalone="no"?>

<svg
   width="{w}{unit}"
   height="{h}{unit}"
   viewBox="0 0 {w} {h}"
   version="1.1"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
   {body}
</svg>
"""

class Thickness(object):
    def __init__(
        self,
        min: float,
        max: float,
        nom: float,
    ) -> None:
        self.min = min
        self.max = max
        self.nom = nom


class NodeSpec(object):
    def __init__(
        self,
        height: float,
        width: float,
    ) -> None:
        self.height = height
        self.width = width

class Material(object):
    def __init__(
        self,
        unit: str,
        thickness: Dict[str,float],
        kerf: float,
        min_part: float,
        min_feature: float,
        min_engraving: float,
        node: Dict[str, float],
        corner_radius: float,
        note: str,
    ) -> None:
        self.unit = unit
        self.thickness = Thickness(**thickness)
        self.kerf = kerf
        self.min_part = min_part
        self.min_feature = min_feature
        self.min_engraving = min_engraving
        self.node = NodeSpec(**node)
        self.corner_radius = corner_radius
        self.note = note


class MapSize(object):
    def __init__(
        self,
        w: float,
        l: float
    ) -> None:
        self.w = w
        self.l = l

class MapCenter(object):
    def __init__(
        self,
        l: str,
        r: str,
        t: str,
        b: str,
        w_door: str,
        w_corner: int,
        dividers: int,
    ) -> None:
        self.l = l
        self.r = r
        self.t = t
        self.b = b
        self.w_door = w_door
        self.dividers = dividers
        self.w_corner = w_corner

class MapBorder(object):
    def __init__(
        self,
        w_door: str,
        w_tower: int,
        l_tower: int,
        w_lamps: int,
        l_lamps: int,
    ) -> None:
        self.w_door = w_door
        self.w_tower = w_tower
        self.l_tower = l_tower
        self.w_lamps = w_lamps
        self.l_lamps = l_lamps

class MapWall(object):
    def __init__(
        self,
        start: str,
        end: str,
        row: str=None,
        col: str=None,
    ) -> None:
        self.start = start
        self.end = end
        self.row = row
        self.col = col
        self.group: Option[int] = None 
        self.intersect: List[MapWall] = []
        self.color: str = "black"

    def add_intersect(self, other) -> None:
        self.intersect.append(other)
    
    def is_row(self) -> bool:
        return self.row is not None
class Map(object):
    def __init__(
        self,
        hall_ratio: float,
        size: Dict[str,float],
        border: Dict[str,Any],
        center: Dict[str,Any],
        walls: Dict[str, List[Dict[str,str]]],
    ) -> None:
        self.hall_ratio = hall_ratio
        self.size = MapSize(**size)
        self.border = MapBorder(**border)
        self.center = MapCenter(**center)
        self.rows = [MapWall(**w) for w in walls["e-w"]]
        self.cols = [MapWall(**w) for w in walls["n-s"]]

class Provider(object):
    def __init__(
        self,
        cut_color: str,
        line_color: str,
        area_color: str,
        line_w: float,
    ) -> None:
        self.cut_color = cut_color
        self.line_color = line_color
        self.area_color = area_color
        self.line_w = line_w

class SVGMaze(object):
    def __init__(
        self,
        map: Map,
        material: Material,
        provider: Provider
    ) -> None:
        self.map = map
        self.material = material
        self.provider = provider
        self.center = self._center()
        self.border = self._borders()

    pos_re = re.compile("([\\d]+)(h|a)")
    def _add(self, pos: str, diff: int) -> str:
        """
        Add `diff` spaces to the `pos` value, does not change a/h.
        """
        pos_num, pos_type = self.pos_re.match(pos).groups((1, 2))
        return "{}{}".format(int(pos_num) + diff, pos_type)

    def _str_to_pos(self, pos) -> Tuple[int, str]:
        """
        Converts a position
        """
        num, unit = self.pos_re.match(pos).groups((1, 2))
        return (int(num), unit)

    def _pos_to_space(self, num: int, unit: str) -> int:
        if unit == "h":
            return (num * 2) - 1
        return (num * 2)

    def _space_to_pos(self, space: int) -> Tuple[int, str]:
        if space % 2 == 0:
            return (space // 2, "a")
        return ((space+1) // 2, "h")

    def _pos_to_str(self, num: int, unit: str) -> str:
        return "{}{}".format(num, unit)

    def _str_to_space(self, pos: str) -> int:
        n, t = self._str_to_pos(pos)
        return self._pos_to_space(n, t)

    def _space_to_str(self, space: int) -> str:
        n, t = self._space_to_pos(space)
        return self._pos_to_str(n, t)

    w_re = re.compile("([\\d]+)a([\\d]+)h")
    def str_width(self, val: str) -> Tuple[int, int]:
        a, h = self.w_re.match(val).groups(1, 2)
        return (int(a), int(h))

    def pos_num(self, place:str) -> float:
        pos_type = place[-1]
        pos_num = float(place[:-1])
        if pos_type == "h":
            return pos_num*2-1
        return pos_num*2

    def edge(self, place:str, outside:bool, is_hedge: bool):
        pos_num = int(place[:-1])
        on_hedge = place[-1] == "h"
        ratio = self.map.hall_ratio

        # start extreme right/bottom
        val = pos_num * (1 + ratio)
        # 
        if on_hedge:
            val -= ratio

        # adjust to inside hedge
        if not outside:
            val -= 1 if on_hedge else ratio

        # adjust measuring hedge when it lies on an aisle location.
        if is_hedge and not on_hedge:
            val += ((ratio-1)/2) * (-1 if outside else 1)

        return val*self.material.thickness.nom

    def _center_aisle(self):
        w = self.map.size.w
        t_end = "{}a".format(int(w/2)-1)
        b_start = "{}a".format(int(w/2)+1)
        if w % 2 == 1:
            t_end = "{}h".format(int(w-1)/2)
            b_start = "{}h".format(int(w+3)/2)
        return t_end, b_start


    def _borders(self) -> List[MapWall]:
        w = self.map.size.w
        l = self.map.size.l
        t_end, b_start = self._center_aisle()
        return [
            MapWall("1h", "{}h".format(l), row="1h"),
            MapWall("1h", "{}h".format(l), row= "{}h".format(w)),
            MapWall("1h", "{}h".format(w), col="1h"),
            MapWall("1h", t_end, col="{}h".format(l)),
            MapWall(b_start, "{}h".format(w), col="{}h".format(l)),
        ]

    def _center(self) -> List[MapWall]:
        t_end, b_start = self._center_aisle()
        c = self.map.center
        middles = []
        l, l_unit = self._str_to_pos(c.l)
        r, r_unit = self._str_to_pos(c.r)
        r_sp = self._pos_to_space(r - c.w_corner - 1, r_unit)
        l_sp = self._pos_to_space(l + c.w_corner + 1, l_unit)
        middle_w = r_sp - l_sp + 2 - c.dividers
        seg_w = middle_w // c.dividers
        seg_rem = middle_w % c.dividers

        for i in range(c.dividers // 2):
            w = seg_w
            if seg_rem > 0:
                seg_rem -= 1
                w += 1
            num, unit = self._space_to_pos(l_sp)
            s = "{}{}".format(num, unit)
            num, unit = self._space_to_pos(l_sp + w-1)
            e = "{}{}".format(num, unit)
            middles = middles + [
                MapWall(s, e, row=c.t),
                MapWall(s, e, row=c.b),
            ]
            l_sp += w + 1
            w = seg_w
            if seg_rem > 0:
                seg_rem -= 1
                w += 1
            num, unit = self._space_to_pos(r_sp)
            e = "{}{}".format(num, unit)
            num, unit = self._space_to_pos(r_sp - w+1)
            s = "{}{}".format(num, unit)
            middles = middles + [
                MapWall(s, e, row=c.t),
                MapWall(s, e, row=c.b),
            ]
            r_sp -= (w + 1)
        
        if c.dividers % 2 == 1:
            num, unit = self._space_to_pos(l_sp)
            s = "{}{}".format(num, unit)
            num, unit = self._space_to_pos(r_sp)
            e = "{}{}".format(num, unit)
            middles = middles + [
                MapWall(s, e, row=c.t),
                MapWall(s, e, row=c.b),
            ]

        return [
            MapWall(c.t, t_end, col=c.l),
            MapWall(b_start, c.b, col=c.l),
            MapWall(c.t, t_end, col=c.r),
            MapWall(b_start, c.b, col=c.r),
            MapWall(c.l, self._add(c.l, c.w_corner), row=c.t),
            MapWall(c.l, self._add(c.l, c.w_corner), row=c.b),
            MapWall(self._add(c.r, -1 * c.w_corner), c.r, row=c.t),
            MapWall(self._add(c.r, -1 * c.w_corner), c.r, row=c.b),
        ] + middles

    def rect(self, wall: MapWall):
        args = {}
        if wall.row is not None:
            args["h"] = self.material.thickness.nom
            args["x"] = self.edge(wall.start, False, True)
            args["y"] = self.edge(wall.row, False, True)
            x_end = self.edge(wall.end, True, True)
            args["w"] = x_end - args["x"]
        else:
            args["w"] = self.material.thickness.nom
            args["x"] = self.edge(wall.col, False, True)
            args["y"] = self.edge(wall.start, False, True)
            y_end = self.edge(wall.end, True, True)
            args["h"] = y_end - args["y"]
        
        args["color"] = wall.color
        args["stroke"] = 0.1

        return """
        <rect x="{x}" y="{y}" width="{w}" height="{h}"
        fill="{color}" stroke="{color}" stroke-width="{stroke}"/>
        """.format(**args)

    def shift(self, body:str, x_shift: int=0, y_shift: int=0):
        return """<g transform="translate({x} {y})">
        {body}
        </g>
        """.format(
            body=body,
            x = x_shift * self.material.thickness.nom,
            y = y_shift * self.material.thickness.nom,
        )

    def _intersect(self, first: MapWall, second: MapWall) -> Optional[Tuple[str, str]]:
        if first.is_row() == second.is_row():
            return None

        row = first
        col = second
        if col.is_row():
            row = second
            col = first
        r = self._str_to_space(row.row)
        r_s = self._str_to_space(row.start)
        r_e = self._str_to_space(row.end)
        c = self._str_to_space(col.col)
        c_s = self._str_to_space(col.start)
        c_e = self._str_to_space(col.end)

        if r < c_s or r > c_e or c < r_s or c > r_e:
            return None
        
        return (self._space_to_str(r), self._space_to_str(c))


    def _merge_group(self, groups: Dict[int, List[MapWall]], a: MapWall, b: MapWall):
        if b.group is None:
            b.group = a.group
            groups[a.group].append(b)
            return
       
        dead_group = b.group
        for w in groups[dead_group]:
            w.group = a.group
            groups[a.group].append(w)
        del groups[dead_group]

    def _group_walls(self):
        groups: Dict[int, List[MapWall]] = {}
        cur_group = 1
        for i in range(len(self.border)):
            a = self.border[i]
            if not a.group:
                a.group = cur_group
                groups[cur_group] = [a]
                cur_group += 1
            for b in self.border[i+1:] + self.map.rows + self.map.cols:
                if self._intersect(a, b):
                    a.add_intersect(b)
                    b.add_intersect(a)
                    self._merge_group(groups, a, b)
        
        for i in range(len(self.center)):
            a = self.center[i]           
            if not a.group:
                a.group = cur_group
                groups[cur_group] = [a]
                cur_group += 1
            for b in self.center[i+1:] + self.map.rows + self.map.cols:
                if self._intersect(a, b):
                    a.add_intersect(b)
                    b.add_intersect(a)
                    self._merge_group(groups, a, b)

        for a in self.map.rows:
            if not a.group:
                a.group = cur_group
                groups[cur_group] = [a]
                cur_group += 1
            for b in self.map.cols:
                if self._intersect(a, b):
                    a.add_intersect(b)
                    b.add_intersect(a)
                    self._merge_group(groups, a, b)

        for a in self.map.cols:
            if not a.group:
                a.group = cur_group
                groups[cur_group] = [a]
                cur_group += 1

        colors = [
            "red",
            "orange",
            "yellow",
            "green",
            "blue",
            "indigo",
            "violet"
        ]

        for k in groups:
            for w in groups[k]:
                w.color = colors[k % len(colors)]

    def write_file(self):
        width = self.material.thickness.nom * ((2 * table_offset) + self.map.size.w + ((self.map.size.w - 1) * self.map.hall_ratio))
        length = self.material.thickness.nom * ((2 * table_offset) + self.map.size.l + ((self.map.size.l - 1) * self.map.hall_ratio))

        self._group_walls()

        pattern = "".join(
            [self.rect(b) for b in self.border]
            + [self.rect(r) for r in self.map.rows]
            + [self.rect(c) for c in self.map.cols]
            + [self.rect(c) for c in self.center]
        )

        body = self.shift(pattern, 3, 3)

        print(file_tag.format(
            unit=self.material.unit,
            w=length,
            h=width,
            body=body,
        ))

        

map = Map(**json.load(io.FileIO("./data/patterns/savage.json")))
material = Material(**json.load(io.FileIO("./data/ponoko/mat/look.json")))
provider = Provider(**json.load(io.FileIO("./data/ponoko/provider.json")))

maze = SVGMaze(map, material, provider)
maze.write_file()
