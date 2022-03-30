

import io
import json
from typing import Any, Dict, List 

table_offset = 3

file_tag = """
<svg version="1.1"
     width="{w}" height="{h}"
     xmlns="http://www.w3.org/2000/svg">

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
        dividers: int,
    ) -> None:
        self.l = l,
        self.r = r,
        self.t = t,
        self.b = b
        self.w_door = w_door
        self.dividers = dividers

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
        self.group: int = None 

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

    def _borders(self) -> List[MapWall]:
        w = self.map.size.w
        l = self.map.size.l
        return [
            MapWall("1h", "{}h".format(l), row="1h"),
            MapWall("1h", "{}h".format(l), row= "{}h".format(w)),
            MapWall("1h", "{}h".format(w), col="1h"),
            MapWall("1h", "{}h".format(int(w/2-1)), col="{}h".format(l)),
            MapWall("{}h".format(int(w/2+1)), "{}h".format(w), col="{}h".format(l)),
        ]

    def _center() -> List[MapWall]:
        return []

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
        
        args["color"] = "black"
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

    def _group_walls(self):
        groups: List[List[MapWall]] = [[]]
        cur_group = 0
        self.map.rows[0].group = 0

    def write_file(self):
        width = self.material.thickness.nom * ((2 * table_offset) + self.map.size.w + ((self.map.size.w - 1) * self.map.hall_ratio))
        length = self.material.thickness.nom * ((2 * table_offset) + self.map.size.l + ((self.map.size.l - 1) * self.map.hall_ratio))

        border = self._borders()

        pattern = "".join(
            [self.rect(b) for b in border] +
            [self.rect(r) for r in self.map.rows] +
            [self.rect(c) for c in self.map.cols]
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
